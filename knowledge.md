# Grand Champagne Helper - Knowledge Base

This file captures key insights, assumptions, and structural details discovered during the development process.

## Input File Structures & Conventions

### `Wine_list_2025.pdf`

*   **Overall Structure:** Organized by Stand (e.g., `STAND_NAME STAND X`).
*   **House Names:**
    *   Appear on their own line after a Stand header or after the price lines of a previous house within the same stand.
    *   Consist only of the house name (no price, grape info, or other data on the same line).
    *   Are not purely numeric and contain at least one alphabetic character.
    *   Examples: `Domaine Alexandre Bonnet`, `Collard-Picard`, `Herbert Beaufort`.
*   **Price Lines:**
    *   Appear under a House Name line.
    *   Format: `GlassPrice€ Specific Name [Optional Grapes] [Optional Other Info] [Optional BottlePrice€]`
    *   **Glass Price (`X€`):** Mandatory at the beginning of the line.
    *   **Specific Name:** The name of the champagne, excluding the house.
    *   **Grapes / Other Info:** Optional text (e.g., `PN/C`, `V`, `O/Bio`) might appear before an optional bottle price.
    *   **Bottle Price (`X.XX€` or `X,XX€`):** Optional at the end of the line.
*   **Rare Wines (`*`):** Wines marked with a trailing asterisk (`*`) in the price list correspond to the rare wines listed in `Rare_schedule_2025.pdf`.
    *   The asterisk and any text following it (like grapes or other codes) are ignored during name normalization for matching purposes.
*   **Other Lines:** Lines containing only grape abbreviations, specific headers (`RARE CHAMPAGNE`, etc.), or purely numeric lines are ignored by the parser.

### `Rare_schedule_2025.pdf`

*   **Overall Structure:** Organized by Day (e.g., `THURSDAY DD.MM.`).
*   **Opening Lines:**
    *   Format: `HH:MM Full Champagne Name StandNumber`
    *   `Full Champagne Name`: Includes the House Name and the Specific Name (often matching a line marked with `*` in `Wine_list_2025.pdf`).

### `tastings.txt`

*   **Structure:** Blocks starting with `Day DD.MM.YYYY klo HH.MM:`, followed by one or more champagne names on separate lines. Blocks are separated by blank lines.
*   **Assumption:** Each tasting slot lasts approximately 1 hour.

### `preferences.txt`

*   **Structure:** Mostly free-form, but keywords are used:
    *   Bottle sizes (e.g., `magnum`, `jeroboam`).
    *   Age requirement (e.g., `older than YYYY`, `before YYYY`).
    *   List of preferred houses (e.g., `Houses: House A, House B`).

## Matching & Logic

*   **Name Normalization (`normalize_name` in `core_logic.py`):
    *   Lowercase.
    *   Removes `(base YYYY)` patterns.
    *   Removes common suffixes like `magnum`, `jeroboam`, `nv`.
    *   Removes trailing `*` and any text following it.
    *   Collapses extra whitespace.
*   **Rare Wine Price Matching (`find_price_for_rare_wine`):
    *   Uses the list of House Names extracted from `Wine_list_2025.pdf`.
    *   For a given `rare_wine_name` from the schedule:
        1.  Identify the corresponding `House Name` (longest match preferred).
        2.  Extract the `specific_wine_part`.
        3.  Filter the `wine_details` dictionary to wines belonging only to the identified house.
        4.  Normalize the `specific_wine_part` and the specific names of the house's wines (using `normalize_name`).
        5.  Attempt an exact match on the normalized specific parts.
        6.  If no exact match, attempt fuzzy matching (`thefuzz.WRatio`, threshold 80).
        7.  If a match is found, retrieve the `glass_price`.
*   **Tasting Conflict Filtering:**
    *   Compare the `datetime` of a rare opening against the `start` and `end` times of each slot in `tasting_slots`.
*   **Tasted Champagne Filtering:**
    *   Check if the normalized `rare_wine_name` exists in the normalized `tasted_champagnes_set`.
*   **Preference Scoring:**
    *   Applied after filtering.
    *   Uses preferences from `preferences.txt`.
    *   **Rules (Additive):**
        *   **House Match (+1pt):** Check if identified `House Name` is in `preferences['houses']`.
        *   **Size Match (+1pt):** Check if original `rare_wine_name` contains sizes from `preferences['sizes']`.
        *   **Age Match (+1pt):** Check if extracted year from `rare_wine_name` is `<= preferences['older_than_year']`.
*   **Final Recommendation (`find_next_rare_opening`):
    *   Sorts filtered, scored openings by time, then score (desc).
    *   Filters for `preference_score >= 2`.
    *   Returns top 1-3 results.

## Application Structure

*   **Backend:** Flask app (`src/app.py`).
*   **Core Logic:** `src/data_parser.py`, `src/core_logic.py`.
*   **API:** `/api/next-opening` (`src/app.py`).
*   **Frontend:** HTML (`src/templates/index.html`), served by `/` (`src/app.py`).
*   **Data:** Input files in `Material/`.

## Open Questions / Potential Issues

*   Consistency of house names between files (accents, abbreviations).
*   Accuracy of `pdfplumber` text extraction on complex layouts.
*   Handling of unexpected formats in input files. 