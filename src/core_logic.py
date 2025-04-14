from datetime import datetime, timedelta
import re
import sys
import os

# Import the fuzzy matching library
from thefuzz import process, fuzz

# Import the parsing functions
from .data_parser import (
    parse_rare_schedule,
    parse_wine_list,
    parse_preferences,
)


def load_all_data(material_dir):
    """Loads all data from files within the specified directory."""
    print("Loading all data...")
    try:
        # Construct full paths using the provided directory
        rare_schedule_path = os.path.join(material_dir, "Rare_schedule_2025.pdf")
        wine_list_path = os.path.join(material_dir, "Wine_list_2025.pdf")
        preferences_path = os.path.join(material_dir, "preferences.txt")

        rare_schedule = parse_rare_schedule(rare_schedule_path)
        wine_details, house_names = parse_wine_list(wine_list_path)
        preferences = parse_preferences(preferences_path)
        print("Data loading complete.")

        return {
            "rare_schedule": rare_schedule,
            "wine_details": wine_details,
            "house_names": house_names,
            "preferences": preferences,
        }
    except FileNotFoundError as e:
        print(f"Error loading data: Input file not found. {e}", file=sys.stderr)
        raise  # Re-raise the exception to be caught by the caller (app.py)
    except Exception as e:
        print(f"An unexpected error occurred during data loading: {e}", file=sys.stderr)
        raise  # Re-raise


# --- Helper function for name normalization ---
def normalize_name(name):
    """Normalizes champagne names for better matching."""
    if not name:
        return ""
    name = name.lower()
    # Remove specific patterns like (base YYYY)
    name = re.sub(r"\(base \d{4}\)", "", name)
    # Remove trailing asterisk if it's the VERY last character
    # name = name.rstrip("*").strip() # We handle '*' below now
    # Remove only bottle sizes and 'nv'
    suffixes_to_remove = ["magnum", "jeroboam", "methuselah", "nabuchodonosor", "nv"]

    # Split, filter, rejoin to handle suffixes as separate words
    words = name.split()
    normalized_words = [word for word in words if word not in suffixes_to_remove]
    name = " ".join(normalized_words)

    # Keep years and common descriptors
    # Remove extra whitespace that might have been introduced
    name = re.sub(r"\s+", " ", name).strip()

    # --- Updated: Remove trailing asterisk and anything after it --- #
    name = re.sub(r"\s*\*.*$", "", name).strip()
    # ------------------------------------------------------------

    # --- Remove Debug Print ---
    # if "canard" in original_input.lower():
    #     print(f"DEBUG NORMALIZE: Input='{original_input}' -> Output='{name}'", file=sys.stderr)
    # -------------------------
    return name


# --- Updated Name Matching Logic --- (Using House Names)
def find_price_for_rare_wine(rare_wine_name, wine_details, house_names):
    """
    Attempts to find the price details for a rare wine name by first matching
    the house name and then fuzzy matching the specific wine part.
    """
    if not rare_wine_name or not wine_details or not house_names:
        return None

    # Find the house name that matches the start of the rare wine name
    matched_house = None
    specific_wine_part = None
    rare_wine_name_lower = rare_wine_name.lower()

    # Sort houses by length descending to check longer names first
    sorted_house_names = sorted(house_names, key=len, reverse=True)

    for house in sorted_house_names:
        house_lower = house.lower()
        # Check if rare name starts with house name, ensuring a word boundary or end of string
        # This prevents partial matches like 'Bonnet' matching 'Bonnet-Gilmert'
        if rare_wine_name_lower.startswith(house_lower) and (
            len(rare_wine_name) == len(house)
            or not rare_wine_name_lower[len(house)].isalnum()
        ):
            matched_house = house
            # Extract the part after the house name
            specific_wine_part = rare_wine_name[len(house) :].strip()
            break  # Found the longest matching house

    if not matched_house or not specific_wine_part:
        # --- Remove specific debug block ---
        # if rare_wine_name in [
        #     "Lombard Vintage 2008",
        #     "Leclaire-Thiefaine Cuvée 03 Grand Cru de Cramant 2020",
        # ]:
        #     print(
        #         f"DEBUG Price Match: Could not identify house for '{rare_wine_name}'",
        #         file=sys.stderr,
        #     )
        # ----------------------------------
        return None

    # --- Remove specific debug block ---
    # debug_this_wine = rare_wine_name in [
    #     "Lombard Vintage 2008",
    #     "Leclaire-Thiefaine Cuvée 03 Grand Cru de Cramant 2020",
    # ]
    debug_this_wine = False  # Keep variable defined, but always false
    # ----------------------------------

    if debug_this_wine:
        print(f"\nDEBUG Price Match Attempt for: '{rare_wine_name}'", file=sys.stderr)
        print(
            f"  -> Identified House: '{matched_house}', Specific Part: '{specific_wine_part}'",
            file=sys.stderr,
        )

    normalized_specific_part = normalize_name(specific_wine_part)
    if not normalized_specific_part:
        # --- Remove specific debug block ---
        # if debug_this_wine:
        #     print(
        #         f"  -> Failed to normalize specific part: '{specific_wine_part}'",
        #         file=sys.stderr,
        #     )
        # ----------------------------------
        return None

    # Filter wine_details to only include items from the matched house
    house_wines = {
        name: details
        for name, details in wine_details.items()
        if name.lower().startswith(matched_house.lower())
    }

    if not house_wines:
        # --- Remove specific debug block ---
        # if debug_this_wine:
        #     print(
        #         f"  -> No wines found in price list for house '{matched_house}'",
        #         file=sys.stderr,
        #     )
        # ----------------------------------
        return None

    # Prepare normalized names map ONLY for this house's wines
    house_price_name_map = {}
    for k in house_wines.keys():
        if not k:
            continue
        specific_part = k[len(matched_house) :].strip()
        normalized_key = normalize_name(specific_part)
        house_price_name_map[normalized_key] = k

    normalized_house_price_names = list(house_price_name_map.keys())

    # --- Remove specific debug block ---
    # if debug_this_wine:
    #     print(
    #         f"  -> Searching '{normalized_specific_part}' against {len(normalized_house_price_names)} normalized names from house '{matched_house}'. Full list:",
    #         file=sys.stderr,
    #     )
    #     for i, price_name in enumerate(normalized_house_price_names):
    #         print(f"     [{i}] '{price_name}'", file=sys.stderr)
    # ----------------------------------

    # 1. Try exact match on normalized specific parts within the house
    if normalized_specific_part in house_price_name_map:
        original_full_name = house_price_name_map[normalized_specific_part]
        # --- Remove specific debug block ---
        # if debug_this_wine:
        #     print(
        #         f"  SUCCESS (Exact): Found exact normalized match '{normalized_specific_part}' for house '{matched_house}'",
        #         file=sys.stderr,
        #     )
        # ----------------------------------
        return wine_details[original_full_name].get("glass_price")

    # 2. Try fuzzy matching on normalized specific parts within the house
    top_matches = []
    best_match_tuple = None

    try:
        extracted_matches = process.extractWithoutOrder(
            normalized_specific_part,
            normalized_house_price_names,
            scorer=fuzz.WRatio,
            score_cutoff=60,  # Keep cutoff low for potential matches
        )

        if isinstance(extracted_matches, list) and extracted_matches:
            top_matches = extracted_matches
            best_match_tuple = max(top_matches, key=lambda x: x[1])

            # --- Remove specific debug block ---
            # if debug_this_wine:
            #     print(f"  -> Top Fuzzy Candidates (Score >= 60):", file=sys.stderr)
            #     for match, score in sorted(
            #         top_matches, key=lambda x: x[1], reverse=True
            #     )[:5]:
            #         print(f"     - '{match}' (Score: {score})", file=sys.stderr)
            # elif debug_this_wine:
            #     print("  -> No fuzzy matches found above cutoff 60.", file=sys.stderr)
            # ----------------------------------

    except Exception as e:
        print(
            f"ERROR during fuzzy matching process for house '{matched_house}', specific part '{normalized_specific_part}': {e}",
            file=sys.stderr,
        )
        return None

    SIMILARITY_THRESHOLD = 80  # Lowered threshold
    if best_match_tuple:
        best_match_str, best_score = best_match_tuple
        if best_score >= SIMILARITY_THRESHOLD:
            original_full_name = house_price_name_map[best_match_str]
            # --- Remove specific debug block ---
            # if debug_this_wine:
            #     print(
            #         f"  SUCCESS (Fuzzy): Found fuzzy match '{best_match_str}' with score {best_score} >= {SIMILARITY_THRESHOLD}",
            #         file=sys.stderr,
            #     )
            # ----------------------------------
            return wine_details[original_full_name].get("glass_price")
        # --- Remove specific debug block ---
        # elif debug_this_wine:
        #     print(
        #         f"  FAILURE: Best fuzzy match '{best_match_str}' score {best_score} < {SIMILARITY_THRESHOLD}",
        #         file=sys.stderr,
        #     )
        # ----------------------------------

    return None  # Price not found


# --- Helper function to extract year ---
def extract_year_from_name(name):
    """Extracts a 4-digit year from a string, returning None if not found."""
    match = re.search(r"\b(\d{4})\b", name)
    if match:
        return int(match.group(1))
    return None


# --- Core Filtering/Ranking Logic ---
def find_next_rare_opening(all_data, current_time=None, dynamic_preferences=None):
    """Finds the next available rare opening based on schedule and preferences."""
    if current_time is None:
        current_time = datetime.now()
    print(f"Finding next opening based on current time: {current_time}")

    rare_schedule = all_data.get("rare_schedule", [])
    wine_details = all_data.get("wine_details", {})
    house_names = all_data.get("house_names", set())
    base_preferences = all_data.get("preferences", {})

    # Create effective preferences for THIS request, starting with base
    effective_preferences = base_preferences.copy()
    if dynamic_preferences:
        effective_preferences.update(dynamic_preferences)  # Update the local copy

    # --- Combine tasted and excluded wines --- #
    # Determine if we should ignore the MC wines
    ignore_tasted_flag_from_prefs = effective_preferences.get("ignore_tasted", False)

    # Start with wines excluded dynamically (e.g., from selected MCs)
    final_excluded_wines = set()
    dynamically_excluded = set(effective_preferences.get("excluded_wines", []))
    # Only add the dynamically excluded (MC) wines if the flag is False
    if dynamically_excluded and not ignore_tasted_flag_from_prefs:
        normalized_dynamic_excluded = {
            normalize_name(wine) for wine in dynamically_excluded
        }
        final_excluded_wines.update(normalized_dynamic_excluded)

    # -------------------------------------------- #

    # --- Pre-process schedule: Add datetime objects --- #
    processed_schedule = []
    for item in rare_schedule:
        try:
            # Combine date and time strings and parse into datetime
            opening_time = datetime.strptime(
                f"{item['date']} {item['time']}", "%Y-%m-%d %H:%M"
            )
            item["datetime"] = opening_time  # Add the datetime object
            processed_schedule.append(item)
        except (KeyError, ValueError) as e:
            print(
                f"Warning: Skipping schedule item due to missing/invalid date/time: {item}. Error: {e}",
                file=sys.stderr,
            )
            continue
    # ------------------------------------------------- #

    # --- Filtering Logic --- #
    possible_openings = []
    # Get MC slots from effective preferences, default to empty list
    attended_mc_slots = effective_preferences.get("attended_mc_slots", [])

    # Filter PROCESSED schedule for future openings
    for opening in processed_schedule:
        opening_time = opening["datetime"]  # Now this key exists
        if opening_time > current_time:
            # Check ONLY against attended MC slots for time conflicts
            is_free = True
            if attended_mc_slots:
                for mc_slot in attended_mc_slots:
                    if mc_slot["start"] <= opening_time < mc_slot["end"]:
                        is_free = False
                        # print(f"DEBUG: {opening['name']} conflicts with MC slot {mc_slot}") # Optional debug
                        break

            if is_free:
                # Normalize wine name from schedule for exclusion check
                normalized_opening_name = normalize_name(opening.get("name"))
                # Check if excluded (now only based on selected MCs + ignore_tasted flag)
                if normalized_opening_name not in final_excluded_wines:
                    possible_openings.append(opening)

    if not possible_openings:
        print(
            "No future rare openings available or free after schedule/tasting/exclusion checks."
        )
        return []

    # --- Apply Preferences and Score --- #
    scored_openings = []
    for opening in possible_openings:
        preference_score = 0
        opening_house = None
        opening_name_lower = opening.get("name", "").lower()

        # Find house (consider caching or pre-processing this)
        for house in house_names:
            house_lower = house.lower()
            if opening_name_lower.startswith(house_lower) and (
                len(opening.get("name", "")) == len(house)
                or not opening_name_lower[len(house)].isalnum()
            ):
                opening_house = house
                break
        opening["house"] = opening_house

        # Extract size from name for scoring
        opening_size = None
        size_patterns = {
            "magnum": ["magnum"],
            "jeroboam": ["jeroboam"],
            "methuselah": ["methuselah"],
            "nabuchodonosor": ["nabuchodonosor"],  # Key is now lowercase
        }  # Define sizes recognized for scoring
        for size_key, patterns in size_patterns.items():
            for pattern in patterns:
                # Use regex word boundary search for robustness
                if re.search(r"\b" + pattern + r"\b", opening_name_lower):
                    opening_size = size_key
                    break
            if opening_size:
                break

        # --- Use effective_preferences for scoring --- #

        # 1. House Preference (+1)
        pref_houses = effective_preferences.get(
            "houses", []
        )  # Use effective_preferences
        if pref_houses and opening_house and opening_house in pref_houses:
            preference_score += 1
            # print(f"DEBUG Score: +1 House match ({opening_house}) for '{opening['name']}'")

        # 2. Size Preference (+1)
        pref_sizes = effective_preferences.get("sizes", [])  # Use effective_preferences
        if pref_sizes and opening_size and opening_size in pref_sizes:
            preference_score += 1
            # print(f"DEBUG Score: +1 Size match ({opening_size}) for '{opening['name']}'")

        # 3. Age Preference (+1)
        pref_older_than_year = effective_preferences.get(
            "older_than_year"
        )  # Use effective_preferences
        if pref_older_than_year:
            extracted_year = extract_year_from_name(opening.get("name"))
            if extracted_year and extracted_year <= pref_older_than_year:
                preference_score += 1
                # print(f"DEBUG Score: +1 Age match ({extracted_year} <= {pref_older_than_year}) for '{opening['name']}'")
        # -------------------------------------------- #

        # Add glass price info
        opening["glass_price"] = find_price_for_rare_wine(
            opening.get("name"), wine_details, house_names
        )
        opening["preference_score"] = preference_score

        if preference_score >= 2:
            scored_openings.append(opening)

    # --- Sort Results --- #
    # Sort primarily by datetime (ascending), secondarily by score (descending)
    scored_openings.sort(key=lambda x: (x["datetime"], -x["preference_score"]))

    # Return top 4
    return scored_openings[:4]


if __name__ == "__main__":
    # Example of using the core logic
    # Get the directory of the current script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up one level to the project root
    project_root = os.path.dirname(script_dir)
    # Construct the path to the Material directory
    material_path = os.path.join(project_root, "Material")

    all_parsed_data = load_all_data(material_path)

    if all_parsed_data["rare_schedule"]:  # Basic check if data loaded
        # Simulate current time for testing (e.g., Friday morning)
        simulated_time = datetime(2025, 4, 25, 10, 0, 0)
        # Get preferences directly from the loaded data for this test run
        test_preferences = all_parsed_data.get("preferences", {})
        next_up = find_next_rare_opening(
            all_parsed_data,
            current_time=simulated_time,
            dynamic_preferences=test_preferences,
        )

        print("\n--- Next Recommended Opening(s) ---")
        if next_up:
            for opening in next_up:
                print(
                    f"  Time: {opening['datetime']} ({opening['datetime'].strftime('%A %H:%M')})"
                )
                print(f"  Name: {opening['name']}")
                print(f"  Stand: {opening['stand']}")
                print(
                    f"  Glass Price: {opening['glass_price']}€"
                    if opening["glass_price"]
                    else "  Glass Price: N/A"
                )
                print(f"  Preference Score: {opening['preference_score']}")
                print("---")
        else:
            print("No suitable upcoming rare openings found.")
    else:
        print("Could not load schedule data to find next opening.")
