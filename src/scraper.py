import requests
import re
import json
import sys
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import os

# --- Configuration ---
MAIN_LIST_URL = "https://grandchampagnehelsinki.fi/master-class-luennot-lista/"
OUTPUT_DIR = "Material"
OUTPUT_FILENAME = "master_classes.json"
# Ensure the Material directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)
OUTPUT_PATH = os.path.join(OUTPUT_DIR, OUTPUT_FILENAME)

# Mapping Finnish month abbreviations to numbers (adjust if needed)
MONTH_MAP_FI = {
    "huhtikuuta": "04",
    # Add other months if event spans more
}


# Define helper functions for parsing dates and times
def parse_session_datetime(day_str, time_str):
    """Parses 'Torstai 24. huhtikuuta' and '16:00' into date and time strings."""
    # Simplify day string processing
    day_match = re.search(r"(\d+)\.", day_str)
    month_match = re.search(r"(huhtikuuta)", day_str, re.IGNORECASE)

    if not day_match or not month_match:
        print(f"Warning: Could not parse day/month from '{day_str}'")
        return None, None

    day = day_match.group(1).zfill(2)
    month_name_fi = month_match.group(1).lower()
    month = MONTH_MAP_FI.get(month_name_fi)

    if not month:
        print(f"Warning: Unknown Finnish month '{month_name_fi}'")
        return None, None

    # Assuming year 2025 for the event
    year = "2025"
    date_str = f"{year}-{month}-{day}"  # YYYY-MM-DD format
    time_str_clean = time_str.strip()  # HH:MM format

    # Validate time format
    if not re.match(r"^\d{1,2}:\d{2}$", time_str_clean):
        print(f"Warning: Invalid time format '{time_str_clean}'")
        return date_str, None

    return date_str, time_str_clean


# Define a function to scrape a single detail page
def scrape_detail_page(url):
    print(f"  Scraping detail page: {url}")
    try:
        response = requests.get(url, timeout=15)  # Increased timeout slightly
        response.raise_for_status()
        # Explicitly decode as UTF-8, sometimes requests guesses wrong
        response.encoding = "utf-8"
        soup = BeautifulSoup(response.text, "html.parser")

        # Find the main content area more reliably
        content_area = soup.find("div", class_="post-content")
        if not content_area:
            print(f"  Warning: Could not find 'post-content' div on {url}")
            return [], None  # Return empty wines, None title

        # --- Extract Title --- #
        # Often the title is in an <h2> within the content or a main <h1>
        title_tag = content_area.find("h2")
        if not title_tag:
            title_tag = soup.find("h1", class_="entry-title")  # Check page title
        title = title_tag.get_text(strip=True) if title_tag else "Unknown Class Title"
        # Simplify title if needed (e.g., remove "Champagne X – " prefix)
        title = re.sub(r"^Champagne [^-]+ –\s*", "", title).strip()

        # --- Extract Wines --- #
        wine_list_header = content_area.find(
            lambda tag: tag.name in ["h2", "h3", "strong", "p"]
            and (
                "Maisteltavat samppanjat:" in tag.get_text()
                or "Champagnes:" in tag.get_text()
            )
        )

        wines = []
        if wine_list_header:
            element = wine_list_header.find_next_sibling()
            processed_text = set()  # Avoid adding duplicates from nested tags

            while element:
                # Stop if we hit another header or known unrelated section
                if element.name in ["h2", "h3"] or (
                    element.name == "p"
                    and element.find("a", href=lambda href: href and "mailto:" in href)
                ):
                    break

                if element.name == "ul":
                    for li in element.find_all("li"):
                        wine_name = li.get_text(strip=True)
                        if wine_name and wine_name not in processed_text:
                            wines.append(wine_name)
                            processed_text.add(wine_name)
                elif element.name == "p":
                    # Handle text possibly split by <br>
                    raw_html = element.decode_contents()
                    potential_wines = [
                        BeautifulSoup(part, "html.parser").get_text(strip=True)
                        for part in raw_html.split("<br/>")
                    ]
                    for wine_name in potential_wines:
                        # Heuristics: not too short, not just uppercase (like headers), not irrelevant phrases
                        if (
                            wine_name
                            and len(wine_name) > 5
                            and not wine_name.isupper()
                            and "Please note" not in wine_name
                            and "Buy a ticket" not in wine_name
                            and wine_name not in processed_text
                        ):
                            wines.append(wine_name)
                            processed_text.add(wine_name)

                element = element.find_next_sibling()
        else:
            print(f"  Warning: Could not find wine list header for '{title}' on {url}")

        if not wines:
            print(f"  Warning: Could not extract wine list for '{title}' from {url}")

        return wines, title

    except requests.exceptions.RequestException as e:
        print(f"  Error fetching detail page {url}: {e}")
        return [], "Error Fetching Title"
    except Exception as e:
        print(f"  Error parsing detail page {url}: {e}")
        return [], "Error Parsing Title"


# Main scraping function
def scrape_and_save_master_classes(output_path):
    print(f"Starting scrape of {MAIN_LIST_URL}...")
    master_classes_dict = {}  # Use dict to handle duplicates by URL/Title

    try:
        response = requests.get(MAIN_LIST_URL, timeout=15)
        response.raise_for_status()
        response.encoding = "utf-8"
        soup = BeautifulSoup(response.text, "html.parser")

        # Find the main content area where the list is
        list_content = soup.find("div", class_="post-content")
        if not list_content:
            print(
                "Error: Could not find main content area ('post-content') on list page."
            )
            return

        day_headers = list_content.find_all("h3")
        current_day_str = None

        for header in day_headers:
            day_text = header.get_text(strip=True)
            if (
                "Torstai" in day_text
                or "Perjantai" in day_text
                or "Lauantai" in day_text
            ):
                current_day_str = day_text.replace("**", "").replace("\\.", ".").strip()
                print(f"\nProcessing Day: {current_day_str}")

            element = header.find_next_sibling()
            while element and element.name != "h3":
                # --- DEBUG --- #
                print(f"DEBUG Loop: Processing element: <{element.name}>")
                try:
                    # Print limited text content to avoid flooding logs
                    el_text = element.get_text(strip=True)[:100]
                    print(f"DEBUG Loop: Element text (start): '{el_text}'...")
                except:
                    print("DEBUG Loop: Could not get text for element")
                # ------------- #

                if element.name == "p":
                    class_text_raw = element.get_text()  # Get text for regex matching
                    # --- DEBUG --- #
                    print(f"DEBUG P-Tag: Raw text for regex: '{class_text_raw}'")
                    # ------------- #
                    time_match = re.match(
                        r"\s*(\d{1,2}:\d{2})\s*–\s*(.*)", class_text_raw
                    )
                    # --- DEBUG --- #
                    if time_match:
                        print(
                            f"DEBUG P-Tag: Regex matched! Time='{time_match.group(1)}', Info='{time_match.group(2)[:50]}...'"
                        )
                    else:
                        print("DEBUG P-Tag: Regex did NOT match.")
                    # ------------- #

                    if time_match and current_day_str:
                        time_str = time_match.group(1)
                        class_info_part = time_match.group(2).strip()
                        detail_link_tag = element.find("a", href=True)
                        detail_url = (
                            detail_link_tag["href"] if detail_link_tag else None
                        )

                        # Use URL as the primary key if possible, otherwise use the text as fallback key
                        key = detail_url if detail_url else class_info_part
                        if not key:  # Skip if no key can be determined
                            element = element.find_next_sibling()
                            continue

                        date_str, clean_time_str = parse_session_datetime(
                            current_day_str, time_str
                        )
                        if not date_str or not clean_time_str:
                            element = element.find_next_sibling()
                            continue

                        session_info = {"date": date_str, "time": clean_time_str}

                        if key not in master_classes_dict:
                            print(f"  Found new class entry: {class_info_part[:60]}...")
                            wines = []
                            title = (
                                class_info_part.split(":")[1].split("–")[0].strip()
                                if ":" in class_info_part
                                else class_info_part
                            )  # Default title
                            if detail_url:
                                wines, fetched_title = scrape_detail_page(detail_url)
                                if fetched_title:
                                    title = fetched_title  # Use title from detail page if found
                            else:
                                print(f"  Warning: No detail URL found for {title}")

                            master_classes_dict[key] = {
                                "name": title,
                                "sessions": [session_info],
                                "duration_minutes": 50,
                                "wines": wines,
                            }
                        else:
                            # Existing entry, just add the session if it's not already there
                            if session_info not in master_classes_dict[key]["sessions"]:
                                master_classes_dict[key]["sessions"].append(
                                    session_info
                                )
                                print(
                                    f"    Added session {date_str} {clean_time_str} to existing: {master_classes_dict[key]['name']}"
                                )

                element = element.find_next_sibling()

    except requests.exceptions.RequestException as e:
        print(f"Error fetching main list page {MAIN_LIST_URL}: {e}")
        return
    except Exception as e:
        import traceback

        print(f"Error parsing main list page: {e}")
        print(traceback.format_exc())  # Print full traceback for parsing errors
        return

    # Convert dict back to list
    master_classes_list = list(master_classes_dict.values())

    # Save the data
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(master_classes_list, f, indent=2, ensure_ascii=False)
        print(
            f"\nSuccessfully scraped data for {len(master_classes_list)} unique Master Classes."
        )
        print(f"Data saved to: {output_path}")
    except IOError as e:
        print(f"Error writing data to file {output_path}: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during file writing: {e}")


# --- Main Execution Guard ---
if __name__ == "__main__":
    scrape_and_save_master_classes(OUTPUT_PATH)
