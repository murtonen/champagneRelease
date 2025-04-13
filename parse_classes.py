import re
import json
from pathlib import Path


def parse_html_classes(html_content):
    """
    Parses the HTML content to extract Master Class schedule information.
    Returns a list of dictionaries, each representing a master class.
    """
    master_classes = []
    day_sections_regex = re.compile(
        r'<div class="fusion-menu-anchor" id="mc(torstai|perjantai|lauantai)"></div>.*?<h3><strong>(.*?)</strong></h3>.*?<div class="fusion-text.*?">(.*?)</div>',
        re.DOTALL | re.IGNORECASE,
    )
    class_detail_regex = re.compile(
        r'(\d{2}:\d{2})\s*–\s*(.*?):\s*<a href="(.*?)">(.*?)</a>',
        re.IGNORECASE | re.DOTALL,
    )

    day_sections = day_sections_regex.findall(html_content)
    if not day_sections:
        print("Could not find day sections in classes.html.")
        return []

    for day_tag, day_name_full, day_html in day_sections:
        day_name = day_name_full.strip()
        print(f"Processing Day section: {day_name} (Tag: {day_tag})")
        paragraphs = re.findall(r"<p>(.*?)</p>", day_html, re.DOTALL | re.IGNORECASE)
        if not paragraphs:
            print(f"  No paragraphs found for {day_name}")
            continue

        for p_content in paragraphs:
            lines = re.split(r"\s*<br\s*/?>\s*", p_content.strip())
            for line in lines:
                line = line.strip()
                if not line:
                    continue

                match = class_detail_regex.search(line)
                if match:
                    time, presenter, link, title = match.groups()
                    presenter_cleaned = re.sub("<.*?>", "", presenter).strip()
                    title_cleaned = re.sub("<.*?>", "", title).strip()
                    master_classes.append(
                        {
                            "day": day_name,
                            "time": time.strip(),
                            "presenter": presenter_cleaned,
                            "title": title_cleaned,
                            "link": link.strip(),
                        }
                    )
                else:
                    # Handle lines without the standard link structure (previously 'simple_text_match')
                    # Check if it's just a 'SOLD OUT' notification or similar we should ignore
                    if (
                        "SOLD OUT" in line.upper()
                        or line.startswith("//")
                        or not re.search(r"\d{2}:\d{2}", line)
                    ):
                        # print(f"  Skipping non-standard/sold-out line: {line[:80]}...")
                        pass  # Skip these lines silently for cleaner output
                    else:
                        # Attempt to parse lines like "18:00 – Jukka Sinivirta: Champagne Balcony presents"
                        simple_match = re.search(
                            r"(\d{2}:\d{2})\s*–\s*(.*?):\s*(.*)", line
                        )
                        if simple_match:
                            time, presenter, title = simple_match.groups()
                            master_classes.append(
                                {
                                    "day": day_name,
                                    "time": time.strip(),
                                    "presenter": re.sub("<.*?>", "", presenter).strip(),
                                    "title": re.sub("<.*?>", "", title).strip(),
                                    "link": None,  # No link in this format
                                }
                            )
                        else:
                            print(
                                f"  Could not parse line in {day_name} section: {line[:100]}..."
                            )

    print(
        f"Finished parsing initial class list. Found {len(master_classes)} potential classes."
    )
    return master_classes


def extract_wines_from_class_html(html_content):
    """
    Extracts the list of wines from the HTML content of a single Master Class page.
    Searches for lists following specific headings.
    """
    wines = []
    wine_list_regex = re.compile(
        r"(?:<p><strong>Maisteltavat samppanjat:</strong></p>|<p><strong>Champagnes:</strong></p>).*?<ul>(.*?)</ul>",
        re.DOTALL | re.IGNORECASE,
    )
    list_item_regex = re.compile(r"<li.*?>(.*?)</li>", re.DOTALL | re.IGNORECASE)

    match = wine_list_regex.search(html_content)
    if match:
        ul_content = match.group(1)
        list_items = list_item_regex.findall(ul_content)
        for item in list_items:
            cleaned_wine = re.sub("<.*?>", "", item).strip()
            # Additional cleaning for potential HTML entities like &amp;
            cleaned_wine = cleaned_wine.replace("&amp;", "&").replace("&#8211;", "–")
            if cleaned_wine:
                wines.append(cleaned_wine)
    # else: # Don't print error here, handled in the calling function
    # print("Could not find the wine list section in the HTML.")

    return wines


# --- Main Execution Logic ---


def run_initial_class_parsing():
    """Parses classes.html to get the initial list of classes and saves to JSON.
    Overwrites existing master_classes.json.
    """
    html_file_path = Path("classes.html")
    output_json_path = Path("master_classes.json")
    print(f"--- Running Initial Class Parsing from {html_file_path} ---")

    if not html_file_path.is_file():
        print(f"Error: {html_file_path} not found.")
        return False

    try:
        with open(html_file_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        parsed_data = parse_html_classes(html_content)

        if parsed_data:
            # Initialize with empty wines list
            for master_class in parsed_data:
                master_class["wines"] = []

            with open(output_json_path, "w", encoding="utf-8") as f:
                json.dump(parsed_data, f, ensure_ascii=False, indent=4)
            print(
                f"Successfully parsed {len(parsed_data)} classes from {html_file_path}."
            )
            print(f"Initial data saved to {output_json_path}")
            return True
        else:
            print(f"No master class data was extracted from {html_file_path}.")
            return False
    except Exception as e:
        print(f"An error occurred during initial parsing: {e}")
        return False


def populate_wines_from_html_files():
    """Reads master_classes.json, finds corresponding master_class_N.html files,
    extracts wines, and updates the JSON.
    If an HTML file is missing, it prints a curl command to download it.
    """
    json_path = Path("master_classes.json")
    print(f"\n--- Populating Wines from HTML files into {json_path} ---")

    if not json_path.is_file():
        print(f"Error: {json_path} not found. Run initial parsing first?")
        return

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            master_classes_data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error reading {json_path}: {e}")
        return
    except Exception as e:
        print(f"An unexpected error occurred reading {json_path}: {e}")
        return

    updated_count = 0
    missing_files_commands = []  # Store commands for missing files

    for idx, master_class in enumerate(master_classes_data):
        class_index = idx + 1  # 1-based index for filename
        html_filename = f"master_class_{class_index}.html"
        html_file_path = Path(html_filename)

        class_title = master_class.get("title", f"Class {class_index}")
        class_link = master_class.get("link")

        if html_file_path.is_file():
            # Only update if the wines list is currently empty or missing
            if not master_class.get("wines"):
                print(f"  Processing {html_filename} for '{class_title}'...", end="")
                try:
                    with open(html_file_path, "r", encoding="utf-8") as f:
                        html_content = f.read()
                    extracted_wines = extract_wines_from_class_html(html_content)
                    if extracted_wines:
                        master_class["wines"] = extracted_wines
                        updated_count += 1
                        print(f" Found {len(extracted_wines)} wines.")
                    else:
                        master_class["wines"] = (
                            []
                        )  # Ensure key exists even if no wines found
                        print(" No wine list found in file.")
                except Exception as e:
                    print(f" Error processing {html_filename}: {e}")
                    master_class["wines"] = []  # Ensure key exists on error
            # else: # Optional: Add message if already populated
            # print(f"  Skipping {html_filename} for '{class_title}', already has wines.")
        else:
            # Ensure 'wines' key exists if file is missing
            if "wines" not in master_class:
                master_class["wines"] = []
            # If file is missing AND there's a link, generate download command
            if class_link:
                print(f"  Missing file: {html_filename} for '{class_title}'")
                # Construct curl command for PowerShell
                # Using -L for redirects, -o for output, --ssl-no-revoke for compatibility, -k for insecure as fallback
                # Escaping quotes for PowerShell command line might be needed depending on how it's run
                curl_command = f'curl.exe -L -k --ssl-no-revoke -o "{html_filename}" "{class_link}"'
                missing_files_commands.append(curl_command)
            # else: # No link, can't download
            # print(f"  Missing file: {html_filename} for '{class_title}' (No link available)")

    # Save the updated data back to JSON (reflects processed files)
    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(master_classes_data, f, ensure_ascii=False, indent=4)
        print(f"\nFinished processing. Updated {updated_count} classes with wines.")
        print(f"Updated data saved to {json_path}")
    except Exception as e:
        print(f"An error occurred saving updated data to {json_path}: {e}")

    # Print commands for missing files at the end
    if missing_files_commands:
        print(
            "\n----------------------------------------------------------------------"
        )
        print(
            f"NOTE: The following {len(missing_files_commands)} HTML files are missing."
        )
        print("Run these commands in your PowerShell terminal to download them:")
        print("----------------------------------------------------------------------")
        for cmd in missing_files_commands:
            print(cmd)
        print("----------------------------------------------------------------------")
        print("After running the commands, run 'python parse_classes.py' again.")
        print("----------------------------------------------------------------------")


# --- Script Entry Point ---
if __name__ == "__main__":
    # Step 1: Ensure the initial class list JSON exists.
    # run_initial_class_parsing() # Keep commented unless refreshing the base list

    # Step 2: Populate wines from available HTML files / generate download commands.
    populate_wines_from_html_files()
