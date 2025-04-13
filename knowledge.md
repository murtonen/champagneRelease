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
    *   Format: `GlassPrice€ Specific Name [Optional Grapes] [Optional BottlePrice€]`
    *   **Glass Price (`X€`):** Mandatory at the beginning of the line.
    *   **Specific Name:** The name of the champagne, excluding the house.
    *   **Grapes:** Optional, typically uppercase letters separated by `/` (e.g., `PN/C`, `C/PN/M`).
    *   **Bottle Price (`X.XX€` or `X,XX€`):** Optional at the end of the line.
*   **Rare Wines (`*`):** Wines marked with a trailing asterisk (`*`) in the price list correspond to the rare wines listed in `Rare_schedule_2025.pdf`.
*   **Other Lines:** Lines containing only grape abbreviations (like `PN/C`), specific headers (`RARE CHAMPAGNE`, etc.), or purely numeric lines are ignored.

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

## Matching Logic

*   **Rare Wine Price Matching:**
    *   Use the list of House Names extracted from `Wine_list_2025.pdf`.
    *   For a given `rare_wine_name` from the schedule:
        1.  Identify the corresponding `House Name` by checking if the `rare_wine_name` starts with any known house name (longest match preferred).
        2.  Extract the `specific_wine_part` from the `rare_wine_name`.
        3.  Filter the `wine_details` dictionary to wines belonging only to the identified house.
        4.  Normalize the `specific_wine_part` and the specific names of the house's wines (removing bottle sizes, `NV`, trailing `*`).
        5.  Attempt an exact match on the normalized specific parts.
        6.  If no exact match, attempt fuzzy matching (`thefuzz.WRatio`) with a threshold (e.g., 80).
        7.  If a match is found, retrieve the `glass_price` from the corresponding entry in `wine_details`.

*   **Tasting Conflict Filtering:**
    *   Compare the `datetime` of a rare opening against the `start` and `end` times of each slot in `tasting_slots`.
*   **Tasted Champagne Filtering:**
    *   Check if the `rare_wine_name` exists in the `tasted_champagnes_set`.

*   **Preference Scoring:**
    *   Applied to openings *after* time and tasting conflicts are filtered.
    *   Uses preferences parsed from `preferences.txt`.
    *   **Rules (Additive):**
        *   **House Match (+1pt):** Check if the identified `House Name` for the opening exists in the `preferences['houses']` list (case-insensitive).
        *   **Size Match (+1pt):** Check if the original `rare_wine_name` contains any of the bottle sizes listed in `preferences['sizes']` (case-insensitive).
        *   **Age Match (+1pt):** Extract the year (e.g., `Vintage YYYY`, `\d{4}`) from the `rare_wine_name`. If a year is found and `preferences['older_than_year']` is set, add point if `opening_year <= preferences['older_than_year']`.
    *   The final score is stored alongside the opening details.
*   **Final Recommendation:**
    *   After filtering and scoring, the list of openings is sorted primarily by time, secondarily by score (descending).
    *   The list is then filtered to include only openings with `preference_score >= 2`.
    *   The top 1-3 entries from this highly preferred list are returned as the recommendations.

## Open Questions / Potential Issues

*   Consistency of house names between `Rare_schedule_2025.pdf` and `Wine_list_2025.pdf` (e.g., accents, abbreviations like `Moët & Chandon` vs `Moet et Chandon`). Fuzzy matching on house names might be needed if simple prefix matching fails.
*   Accuracy of the `pdfplumber` text extraction, especially around complex layouts or slightly misaligned columns.
*   Handling of edge cases or unexpected formats in the input files. 