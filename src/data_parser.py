import pdfplumber
import re
from datetime import datetime, timedelta
import sys  # Added for stderr printing

# Regex to find date headers like "THURSDAY 24.4." and capture the date part
DATE_HEADER_PATTERN = re.compile(
    r"(?:TORSTAI|THURSDAY|PERJANTAI|FRIDAY|LAUANTAI|SATURDAY)\s+(\d{1,2}\.\d{1,2}\.)",
    re.IGNORECASE,
)
# Regex to capture schedule lines: Time Name Stand
SCHEDULE_LINE_PATTERN = re.compile(r"^(\d{1,2}:\d{2})\s+(.+?)\s+(\d+)$")
# Assumed year based on filename
YEAR = "2025"
# --- DEBUG FLAG ---
DEBUG = False  # Set to False to turn off debug prints


def parse_rare_schedule(pdf_path="Material/Rare_schedule_2025.pdf"):
    """
    Parses the Rare Schedule PDF to extract opening dates, times, champagne names, and stand numbers.

    Returns:
        list: A list of dictionaries, each containing 'date' (str, YYYY-MM-DD),
              'time' (str, HH:MM), 'name' (str), and 'stand' (str).
              Returns an empty list if parsing fails or PDF not found.
    """
    schedule = []
    current_date_str = None  # Store as DD.MM. initially
    page_num = 0

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_num += 1
                if DEBUG:
                    print(f"\n--- Processing Page {page_num} ---", file=sys.stderr)
                text = page.extract_text(
                    x_tolerance=2, y_tolerance=2
                )  # Adjust tolerance slightly if needed
                if not text:
                    if DEBUG:
                        print(f"Page {page_num}: No text extracted.", file=sys.stderr)
                    continue

                lines = text.split("\n")
                line_num = 0
                for line in lines:
                    line_num += 1
                    line = line.strip()
                    if not line:
                        continue

                    if DEBUG:
                        print(
                            f"Page {page_num}, Line {line_num}: Raw='{line}'",
                            file=sys.stderr,
                        )

                    # Check for Date Header
                    date_match = DATE_HEADER_PATTERN.search(line)
                    if date_match:
                        day_month = date_match.group(1).replace(
                            ".", ""
                        )  # Get "244" from "24.4."
                        if DEBUG:
                            print(
                                f"  DEBUG: Date header FOUND: '{line}', extracted day_month: '{day_month}'",
                                file=sys.stderr,
                            )
                        # Reformat to DD.MM
                        if len(day_month) == 3:  # e.g., 244 -> 24.04
                            current_date_str = f"{day_month[0:2]}.0{day_month[2]}"
                        elif len(day_month) == 4:  # e.g., 1011 -> 10.11
                            current_date_str = f"{day_month[0:2]}.{day_month[2:4]}"
                        else:
                            # Handle unexpected format if necessary
                            print(
                                f"Warning: Skipping unrecognized date format in header: {line}"
                            )
                            current_date_str = None
                        if DEBUG and current_date_str:
                            print(
                                f"  DEBUG: Set current_date_str to: '{current_date_str}'",
                                file=sys.stderr,
                            )

                    # Check for Schedule Line if we have a current date
                    if current_date_str:
                        schedule_match = SCHEDULE_LINE_PATTERN.match(line)
                        if schedule_match:
                            if DEBUG:
                                print(
                                    f"  DEBUG: Schedule line FOUND: '{line}'",
                                    file=sys.stderr,
                                )
                            time = schedule_match.group(1)
                            name = schedule_match.group(2).strip()
                            stand = schedule_match.group(3)

                            # Construct full date YYYY-MM-DD
                            # Assuming the year is 2025 based on filename context
                            day, month = current_date_str.split(".")
                            full_date = f"{YEAR}-{month}-{day}"  # ISO format YYYY-MM-DD

                            # Clean up potential extra spaces in name
                            name = re.sub(r"\s+", " ", name).strip()
                            if DEBUG:
                                print(
                                    f"  DEBUG: Extracted -> Date: {full_date}, Time: {time}, Name: '{name}', Stand: {stand}",
                                    file=sys.stderr,
                                )

                            schedule.append(
                                {
                                    "date": full_date,
                                    "time": time,
                                    "name": name,
                                    "stand": stand,
                                }
                            )

    except FileNotFoundError:
        print(f"Error: PDF file not found at {pdf_path}")
        return []
    except Exception as e:
        print(f"An error occurred during PDF parsing: {e}")
        # Consider logging the full traceback here for debugging
        # import traceback
        # print(traceback.format_exc())
        return []

    return schedule


# --- Placeholder functions moved before __main__ block ---


# Placeholder for wine list parsing (to be added later)
def parse_wine_list(pdf_path="Material/Wine_list_2025.pdf"):
    """
    Parses the Wine List PDF to extract champagne names and prices, and identify house names.

    Returns:
        tuple: A tuple containing:
            - dict: Wine details mapping full champagne names to their details.
            - list: A list of unique house names identified.
    """
    wine_details = {}
    house_names = set()
    STAND_HEADER_PATTERN = re.compile(r"^(.*?)\s+STAND\s+(\d+)$", re.IGNORECASE)
    PRICE_LINE_PATTERN = re.compile(
        r"^(\d+)€\s+(.+?)\s*(?:[A-Z/]+\s*)?(?:(\d+[,.]\d+)\s*€)?$"
    )
    GRAPE_INFO_PATTERN = re.compile(r"^[A-Z/\s]+$")
    IGNORE_HEADERS = {"RARE CHAMPAGNE", "FRANCIACORTA", "ENGLISH SPARKLING WINE"}
    PRICE_START_PATTERN = re.compile(r"^\d+€")  # Check if line starts with price

    current_stand_name = None
    current_stand_number = None
    current_house_name = None

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                # Use slightly wider tolerance, might help with column alignment issues
                text = page.extract_text(x_tolerance=2, y_tolerance=3)
                if not text:
                    continue

                lines = text.split("\n")
                for line_num, line in enumerate(lines, 1):
                    line = line.strip()
                    if not line:
                        continue

                    # 1. Check for Stand Header first
                    stand_match = STAND_HEADER_PATTERN.match(line)
                    if stand_match:
                        current_stand_name = stand_match.group(1).strip()
                        current_stand_number = stand_match.group(2).strip()
                        current_house_name = None  # Reset house for new stand
                        # print(f"DEBUG (Page {page_num}): Found Stand {current_stand_number}: {current_stand_name}")
                        continue

                    # Skip lines until a stand is found
                    if not current_stand_number:
                        continue

                    # 2. Check for Pricing Line
                    price_match = PRICE_LINE_PATTERN.match(line)
                    if price_match:
                        if not current_house_name:
                            print(
                                f"Warning: Found price line but no current house name set (Page {page_num}, Line {line_num}): {line}"
                            )
                            continue  # Skip this price line

                        glass_price = price_match.group(1)
                        specific_name = price_match.group(2).strip()
                        # Group 3 is bottle price, might be None if not matched
                        bottle_price_match = price_match.group(3)
                        bottle_price = (
                            bottle_price_match.replace(",", ".")
                            if bottle_price_match
                            else None
                        )

                        # Combine House + Specific Name
                        full_name = f"{current_house_name} {specific_name}"
                        full_name = re.sub(r"\s+", " ", full_name).strip()

                        # Store details
                        if full_name not in wine_details:
                            wine_details[full_name] = {
                                "glass_price": glass_price,
                                "bottle_price": bottle_price,  # Can be None
                                "stand_number": current_stand_number,
                                "stand_name": current_stand_name,
                            }
                        # print(f"DEBUG (Page {page_num}): Added price for '{full_name}' (Bottle: {bottle_price})")
                        continue  # Processed price line

                    # 3. If not Stand or Price, check if it's a House Name
                    # Must NOT start with price, NOT be just grapes, NOT be an ignored header,
                    # NOT be purely numeric, and MUST contain at least one letter.
                    is_potential_house = (
                        not PRICE_START_PATTERN.match(line)
                        and not GRAPE_INFO_PATTERN.match(line)
                        and line.upper() not in IGNORE_HEADERS
                        and not line.isdigit()  # Added check: not just digits
                        and any(
                            c.isalpha() for c in line
                        )  # Added check: contains letters
                    )

                    if is_potential_house:
                        # This line is identified as a house name.
                        # It implicitly becomes the *current* house, replacing the previous one for this stand.
                        current_house_name = line.strip()
                        house_names.add(current_house_name)
                        # print(f"DEBUG (Page {page_num}): Set House to '{current_house_name}'")
                        continue  # Processed house name

                    # Otherwise, the line is considered junk or unexpected format, ignore it.
                    # print(f"DEBUG (Page {page_num}): Ignored line: '{line}'")

    except FileNotFoundError:
        print(f"Error: Wine list PDF file not found at {pdf_path}")
        return {}, []
    except Exception as e:
        print(f"An error occurred during wine list PDF parsing: {e}")
        # import traceback
        # print(traceback.format_exc())
        return {}, []

    return wine_details, sorted(list(house_names))


# Placeholder for tasting list parsing
def parse_tastings(txt_path="Material/tastings.txt"):
    """
    Parses the user's tasting schedule and tasted champagnes from tastings.txt.
    Assumes format:
        Day DD.MM.YYYY klo HH.MM:
        Champagne Name 1
        Champagne Name 2
        ...
        <Blank Line>
        Day DD.MM.YYYY klo HH.MM:
        ...

    Returns:
        tuple: (list_of_tasting_slots, set_of_tasted_champagnes)
               tasting_slots: [{'start': datetime, 'end': datetime, 'names': [str, ...]}, ...]
               tasted_champagnes: {str, ...} - A set of unique champagne names from all tastings.
    """
    tasting_slots = []
    tasted_champagnes_set = set()

    # Regex to find the header line like "Perjantai 25.4.2025 klo 18.00:"
    HEADER_PATTERN = re.compile(
        r"^\w+\s+(\d{1,2}\.\d{1,2}\.\d{4})\s+klo\s+(\d{1,2}\.\d{2}):?$", re.IGNORECASE
    )

    try:
        with open(txt_path, "r", encoding="utf-8") as f:
            current_tasting = None
            for line in f:
                line = line.strip()

                header_match = HEADER_PATTERN.match(line)
                if header_match:
                    date_str = header_match.group(1)  # DD.MM.YYYY
                    time_str = header_match.group(2).replace(".", ":")  # HH:MM

                    try:
                        # Combine date and time, parse to datetime
                        dt_str = f"{date_str} {time_str}"
                        start_time = datetime.strptime(dt_str, "%d.%m.%Y %H:%M")

                        # Assume 1 hour duration for the tasting slot
                        end_time = start_time + timedelta(hours=1)

                        # Start a new tasting entry
                        current_tasting = {
                            "start": start_time,
                            "end": end_time,
                            "names": [],
                        }
                        tasting_slots.append(current_tasting)

                    except ValueError as e:
                        print(
                            f"Warning: Could not parse date/time in tasting file line: '{line}'. Error: {e}"
                        )
                        current_tasting = None  # Skip wines until next valid header
                    continue  # Move to next line after processing header

                # If line is not empty and we have a current tasting block
                if line and current_tasting is not None:
                    champagne_name = re.sub(r"\s+", " ", line).strip()
                    if champagne_name:
                        current_tasting["names"].append(champagne_name)
                        tasted_champagnes_set.add(champagne_name)
                elif not line:
                    # Blank line signifies end of current tasting block's wines
                    current_tasting = None  # Reset until next header

    except FileNotFoundError:
        print(f"Warning: Tastings file not found at {txt_path}. Returning empty data.")
        return [], set()
    except Exception as e:
        print(f"An error occurred during tastings file parsing: {e}")
        return [], set()

    return tasting_slots, tasted_champagnes_set


# Placeholder for preferences parsing
def parse_preferences(txt_path="Material/preferences.txt"):
    """
    Parses the user's preferences from preferences.txt using basic pattern matching.
    Assumes format: Key: Value

    Returns:
        dict: A dictionary containing parsed preferences.
              Keys might include: 'sizes', 'older_than_year', 'houses'.
    """
    preferences = {"sizes": set(), "older_than_year": None, "houses": set()}

    # Regex patterns
    SIZE_PATTERN = re.compile(
        r"(magnum|jeroboam|methuselah|nabuchodonosor)", re.IGNORECASE
    )
    OLDER_THAN_PATTERN = re.compile(r"(?:older than|before)\s+(\d{4})", re.IGNORECASE)
    HOUSES_PATTERN = re.compile(r"^Houses?:\s*(.*)$", re.IGNORECASE)

    try:
        with open(txt_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                # Check for sizes
                size_matches = SIZE_PATTERN.findall(line)
                if size_matches:
                    for size in size_matches:
                        preferences["sizes"].add(size.lower())

                # Check for older than year
                older_match = OLDER_THAN_PATTERN.search(line)
                if older_match:
                    year = int(older_match.group(1))
                    # Keep the strictest requirement (lowest year)
                    if (
                        preferences["older_than_year"] is None
                        or year < preferences["older_than_year"]
                    ):
                        preferences["older_than_year"] = year

                # Check for Houses: list
                houses_match = HOUSES_PATTERN.match(line)
                if houses_match:
                    house_list_str = houses_match.group(1)
                    # Split by comma, strip whitespace, remove trailing punctuation
                    houses = [
                        re.sub(r"[.,;:!]$", "", h.strip())
                        for h in house_list_str.split(",")
                        if h.strip()
                    ]
                    preferences["houses"].update(houses)

    except FileNotFoundError:
        print(
            f"Warning: Preferences file not found at {txt_path}. Returning empty preferences."
        )
        # Return default structure even if file not found
    except Exception as e:
        print(f"An error occurred during preferences file parsing: {e}")
        # Return default structure on other errors

    # Convert sets to lists for easier JSON serialization later if needed
    preferences["sizes"] = list(preferences["sizes"])
    preferences["houses"] = list(preferences["houses"])

    return preferences


# --- Main execution block ---
if __name__ == "__main__":
    # Example usage when running this script directly
    # --- Parse Rare Schedule ---
    parsed_schedule = parse_rare_schedule()
    print("--- Parsed Rare Schedule (stdout) ---")  # Updated header
    if parsed_schedule:
        print(f"Successfully parsed {len(parsed_schedule)} schedule entries.")
        entries_to_show = 3  # Show fewer for brevity
        if len(parsed_schedule) > 2 * entries_to_show:
            for item in parsed_schedule[:entries_to_show]:
                print(
                    f"  Date: {item['date']}, Time: {item['time']}, Name: {item['name']}, Stand: {item['stand']}"
                )
            print("  ...")
            for item in parsed_schedule[-entries_to_show:]:
                print(
                    f"  Date: {item['date']}, Time: {item['time']}, Name: {item['name']}, Stand: {item['stand']}"
                )
        else:
            for item in parsed_schedule:
                print(
                    f"  Date: {item['date']}, Time: {item['time']}, Name: {item['name']}, Stand: {item['stand']}"
                )
    else:
        print("Could not parse schedule or file is empty/invalid.")

    # --- Parse Wine List ---
    print("\n--- Parsed Wine List Prices (stdout) ---")
    parsed_prices, house_names = parse_wine_list()
    if parsed_prices:
        print(f"Successfully parsed {len(parsed_prices)} price entries.")
        items_shown = 0
        max_items_to_show = 10  # Show sample prices
        for name, details in parsed_prices.items():
            if items_shown >= max_items_to_show:
                print("  ...")
                break
            print(
                f"  Name: '{name}', Glass Price: {details['glass_price']}, Bottle Price: {details['bottle_price']}, Stand: {details['stand_name']}"
            )
            items_shown += 1
        print("\n--- Parsed House Names (stdout) ---")
        print(f"Successfully identified {len(house_names)} unique house names.")
        for house in house_names[:max_items_to_show]:
            print(f"  - {house}")
        if len(house_names) > max_items_to_show:
            print("  ...")
    else:
        print("Could not parse prices or file is empty/invalid.")

    # --- Parse Tastings ---
    print("\n--- Parsed Tastings (stdout) ---")
    parsed_tasting_slots, parsed_tasted_champagnes = parse_tastings()
    if parsed_tasting_slots:
        print(f"Successfully parsed {len(parsed_tasting_slots)} tasting slots.")
        for slot in parsed_tasting_slots[:3]:  # Show first few slots
            print(f"  Slot Start: {slot['start']}, End: {slot['end']}")
            for name in slot["names"][:2]:  # Show first few names in slot
                print(f"    - {name}")
            if len(slot["names"]) > 2:
                print("      ...")
        if len(parsed_tasting_slots) > 3:
            print("  ...")
        print(f"Total unique champagnes in tastings: {len(parsed_tasted_champagnes)}")
        # Example of printing tasted champagnes
        # print("Tasted Champagnes Set:")
        # for name in sorted(list(parsed_tasted_champagnes))[:5]:
        #     print(f"  - {name}")
        # if len(parsed_tasted_champagnes) > 5: print("  ...")

    else:
        print("Could not parse tastings or file is empty/invalid.")

    # --- Parse Preferences ---
    print("\n--- Parsed Preferences (stdout) ---")
    parsed_prefs = parse_preferences()
    if parsed_prefs:
        print(f"Successfully parsed preferences:")
        print(f"  Sizes: {parsed_prefs.get('sizes')}")
        print(f"  Older Than Year: {parsed_prefs.get('older_than_year')}")
        print(f"  Houses: {parsed_prefs.get('houses')}")
    else:
        # This case might not be reachable if it always returns a dict
        print("Could not parse preferences or file is empty/invalid.")
