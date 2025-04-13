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
    parse_tastings,
    parse_preferences,
)


def load_all_data(material_dir):
    """Loads all data from files within the specified directory."""
    print("Loading all data...")
    try:
        # Construct full paths using the provided directory
        rare_schedule_path = os.path.join(material_dir, "Rare_schedule_2025.pdf")
        wine_list_path = os.path.join(material_dir, "Wine_list_2025.pdf")
        tastings_path = os.path.join(material_dir, "tastings.txt")
        preferences_path = os.path.join(material_dir, "preferences.txt")

        rare_schedule = parse_rare_schedule(rare_schedule_path)
        wine_details, house_names = parse_wine_list(wine_list_path)
        tasting_slots, tasted_champagnes = parse_tastings(tastings_path)
        preferences = parse_preferences(preferences_path)
        print("Data loading complete.")

        return {
            "rare_schedule": rare_schedule,
            "wine_details": wine_details,
            "house_names": house_names,
            "tasting_slots": tasting_slots,
            "tasted_champagnes": tasted_champagnes,
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
    # Remove trailing asterisk often found in price list
    name = name.rstrip("*").strip()
    # Remove only bottle sizes and 'nv'
    suffixes_to_remove = ["magnum", "jeroboam", "methuselah", "nabuchodonosor", "nv"]

    # Split, filter, rejoin to handle suffixes as separate words
    words = name.split()
    normalized_words = [word for word in words if word not in suffixes_to_remove]
    name = " ".join(normalized_words)

    # Keep years and common descriptors
    # Remove extra whitespace that might have been introduced
    name = re.sub(r"\s+", " ", name).strip()
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
        # Print error only if specifically debugging the target wines
        if rare_wine_name in [
            "Lombard Vintage 2008",
            "Leclaire-Thiefaine Cuvée 03 Grand Cru de Cramant 2020",
        ]:
            print(
                f"DEBUG Price Match: Could not identify house for '{rare_wine_name}'",
                file=sys.stderr,
            )
        return None

    # --- Enable Debug printing only for target wines ---
    debug_this_wine = rare_wine_name in [
        "Lombard Vintage 2008",
        "Leclaire-Thiefaine Cuvée 03 Grand Cru de Cramant 2020",
    ]

    if debug_this_wine:
        print(f"\nDEBUG Price Match Attempt for: '{rare_wine_name}'", file=sys.stderr)
        print(
            f"  -> Identified House: '{matched_house}', Specific Part: '{specific_wine_part}'",
            file=sys.stderr,
        )

    normalized_specific_part = normalize_name(specific_wine_part)
    if not normalized_specific_part:
        if debug_this_wine:
            print(
                f"  -> Failed to normalize specific part: '{specific_wine_part}'",
                file=sys.stderr,
            )
        return None

    # Filter wine_details to only include items from the matched house
    house_wines = {
        name: details
        for name, details in wine_details.items()
        if name.lower().startswith(matched_house.lower())
    }

    if not house_wines:
        if debug_this_wine:
            print(
                f"  -> No wines found in price list for house '{matched_house}'",
                file=sys.stderr,
            )
        return None

    # Prepare normalized names map ONLY for this house's wines
    house_price_name_map = {
        normalize_name(k[len(matched_house) :].strip()): k
        for k in house_wines.keys()
        if k
    }
    normalized_house_price_names = list(house_price_name_map.keys())

    # --- Enable Debug printing only for target wines ---
    if debug_this_wine:
        print(
            f"  -> Searching '{normalized_specific_part}' against {len(normalized_house_price_names)} normalized names from house '{matched_house}'. Full list:",
            file=sys.stderr,
        )
        # Remove the limit to show all names for the house during debug
        for i, price_name in enumerate(normalized_house_price_names):
            # if i >= 5:
            #     break
            print(f"     [{i}] '{price_name}'", file=sys.stderr)

    # 1. Try exact match on normalized specific parts within the house
    if normalized_specific_part in house_price_name_map:
        original_full_name = house_price_name_map[normalized_specific_part]
        if debug_this_wine:
            print(
                f"  SUCCESS (Exact): Found exact normalized match '{normalized_specific_part}' for house '{matched_house}'",
                file=sys.stderr,
            )
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

            # --- Enable Debug printing only for target wines ---
            if debug_this_wine:
                print(f"  -> Top Fuzzy Candidates (Score >= 60):", file=sys.stderr)
                for match, score in sorted(
                    top_matches, key=lambda x: x[1], reverse=True
                )[:5]:
                    print(f"     - '{match}' (Score: {score})", file=sys.stderr)
        elif debug_this_wine:
            print("  -> No fuzzy matches found above cutoff 60.", file=sys.stderr)

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
            if debug_this_wine:
                print(
                    f"  SUCCESS (Fuzzy): Found fuzzy match '{best_match_str}' with score {best_score} >= {SIMILARITY_THRESHOLD}",
                    file=sys.stderr,
                )
            return wine_details[original_full_name].get("glass_price")
        elif debug_this_wine:
            print(
                f"  FAILURE: Best fuzzy match '{best_match_str}' score {best_score} < {SIMILARITY_THRESHOLD}",
                file=sys.stderr,
            )

    return None  # Price not found


# --- Helper function to extract year ---
def extract_year_from_name(name):
    """Extracts a 4-digit year from a string, returning None if not found."""
    match = re.search(r"\b(\d{4})\b", name)
    if match:
        return int(match.group(1))
    return None


# --- Core Filtering/Ranking Logic ---
def find_next_rare_opening(all_data, current_time=None):
    """
    Combines data, filters based on time/tastings/preferences, and finds the next opening(s).
    (Placeholder - Needs implementation)
    """
    if current_time is None:
        current_time = datetime.now()

    print(f"Finding next opening relative to: {current_time}")

    rare_schedule = all_data["rare_schedule"]
    wine_details = all_data["wine_details"]
    house_names = all_data["house_names"]
    tasting_slots = all_data["tasting_slots"]
    tasted_champagnes = all_data["tasted_champagnes"]
    preferences = all_data["preferences"]
    pref_houses_lower = {
        h.lower() for h in preferences.get("houses", [])
    }  # Lowercase set for efficient lookup
    pref_sizes_lower = {s.lower() for s in preferences.get("sizes", [])}
    pref_older_than = preferences.get("older_than_year")

    # -- DEBUG: Print first few house names ---
    # print("DEBUG: First 10 identified house names:", file=sys.stderr)
    # for i, house in enumerate(house_names):
    #     if i >= 10:
    #         break
    #     print(f"  [{i}] {house}", file=sys.stderr)
    # print("---", file=sys.stderr)
    # -----------------------------------------

    # Step 1: Combine schedule with prices and parse datetime
    print("Step 1: Combining schedule with prices...")
    combined_schedule = []
    for item in rare_schedule:
        try:
            opening_time = datetime.strptime(
                f"{item['date']} {item['time']}", "%Y-%m-%d %H:%M"
            )
            item["datetime"] = opening_time
            # Find price
            item["glass_price"] = find_price_for_rare_wine(
                item["name"], wine_details, house_names
            )
            # Initialize score
            item["preference_score"] = 0
            combined_schedule.append(item)
        except ValueError as e:
            print(
                f"Warning: Skipping schedule item due to date/time parse error: {item}. Error: {e}"
            )

    # Step 2: Filter out past openings
    print(f"Step 2: Filtering out past openings (before {current_time})...")
    future_openings = [
        item for item in combined_schedule if item["datetime"] >= current_time
    ]
    print(f"   {len(future_openings)} openings remaining.")

    # Step 3: Filter out openings conflicting with tasting slots
    print("Step 3: Filtering out openings conflicting with tasting slots...")
    available_slots = []
    for item in future_openings:
        conflict = False
        for slot in tasting_slots:
            # Check for overlap: (SlotStart <= ItemTime < SlotEnd)
            if slot["start"] <= item["datetime"] < slot["end"]:
                conflict = True
                break
        if not conflict:
            available_slots.append(item)
    print(f"   {len(available_slots)} openings remaining.")

    # Step 4: Filter out openings with already tasted champagnes
    print("Step 4: Filtering out openings with already tasted champagnes...")
    # Normalize tasted names for comparison
    tasted_champagnes_normalized = {normalize_name(name) for name in tasted_champagnes}
    unique_openings = []
    for item in available_slots:
        normalized_opening_name = normalize_name(item["name"])
        if normalized_opening_name not in tasted_champagnes_normalized:
            unique_openings.append(item)
    print(f"   {len(unique_openings)} openings remaining.")

    # Step 5: Apply preference scoring
    print("Step 6: Applying basic preference scoring...")  # Renumbered step
    scored_openings = []
    for item in unique_openings:
        score = 0
        item_name_lower = item["name"].lower()

        # Identify house for preference check (re-use logic from price match, slightly adapted)
        matched_house = None
        sorted_house_names = sorted(house_names, key=len, reverse=True)
        for house in sorted_house_names:
            house_lower = house.lower()
            if item_name_lower.startswith(house_lower) and (
                len(item["name"]) == len(house)
                or not item_name_lower[len(house)].isalnum()
            ):
                matched_house = house
                break

        # 1. House Preference
        if matched_house and matched_house.lower() in pref_houses_lower:
            score += 1

        # 2. Size Preference
        for size in pref_sizes_lower:
            if size in item_name_lower:
                score += 1
                break  # Only add score once per item even if multiple sizes match (e.g. Magnum Jeroboam)

        # 3. Age Preference
        opening_year = extract_year_from_name(item["name"])
        if opening_year and pref_older_than:
            if opening_year <= pref_older_than:
                score += 1

        item["preference_score"] = score
        scored_openings.append(item)

    # Step 6: Sort remaining openings by time (primary) and score (secondary, descending)
    print(
        "Step 5: Sorting remaining openings by time..."
    )  # Original step 5 is now just sorting
    # Sort primarily by datetime, then by score descending (higher score is better for same time)
    sorted_openings = sorted(
        scored_openings, key=lambda x: (x["datetime"], -x["preference_score"])
    )

    # Step 7: Determine next HIGHLY PREFERRED opening(s) (Score >= 2)
    print("Step 7: Determining next highly preferred opening(s) (Score >= 2)...")

    # Filter for openings with score >= 2
    highly_preferred_openings = [
        item for item in sorted_openings if item["preference_score"] >= 2
    ]

    if not highly_preferred_openings:
        print(
            "No further rare openings available matching your schedule and high preference (Score >= 2)."
        )
        # Optional: Fallback to showing the next chronological opening regardless of score?
        # if sorted_openings:
        #     print("Showing the next chronological opening instead:")
        #     next_opening_time = sorted_openings[0]["datetime"]
        #     next_openings_at_time = [
        #         item for item in sorted_openings if item["datetime"] == next_opening_time
        #     ]
        #     return next_openings_at_time # Return original next regardless of score
        return None  # Return None if no highly preferred options found

    # Return up to the first 3 highly preferred openings
    return highly_preferred_openings[:3]


if __name__ == "__main__":
    # Example of using the core logic
    all_parsed_data = load_all_data()

    if all_parsed_data["rare_schedule"]:  # Basic check if data loaded
        # Simulate current time for testing (e.g., Friday morning)
        simulated_time = datetime(2025, 4, 25, 10, 0, 0)
        next_up = find_next_rare_opening(all_parsed_data, current_time=simulated_time)

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
