# Grand Champagne Helper - Current State (As of 3-Column Layout)

This document summarizes the state of the project after implementing the initial backend logic, data parsing, and the desktop-focused three-column UI.

## 1. Core Functionality

*   **Data Loading:** The Flask backend (`src/app.py`) loads data on startup (and potentially reloads periodically) from files in the `Material/` directory using parsers in `src/data_parser.py`:
    *   `Rare_schedule_2025.pdf`: Parses rare champagne opening times, names, and stands.
    *   `Wine_list_2025.pdf`: Parses wine details (including glass prices) and identifies house names.
    *   `tastings.txt`: Parses personal tasting schedule slots and tasted champagnes.
    *   `preferences.txt`: Parses baseline user preferences (houses, size, age).
    *   `static/master_classes.json`: Loads pre-processed Master Class details (day, time, presenter, title, wines).
*   **Recommendation Logic (`src/core_logic.py`):**
    *   Combines schedule and price data (using fuzzy name matching).
    *   Filters openings based on:
        *   Current time (only future openings).
        *   Conflicts with personal tasting schedule (`tastings.txt`).
        *   Champagnes already tasted (`tastings.txt`).
        *   Wines tasted in selected Master Classes (`master_classes.json` + user selection).
    *   Scores remaining openings based on dynamic preferences (House +2, Age +1, Size +1).
    *   Returns the **top 3** openings with a score >= 2, sorted by time, then score.
*   **API (`src/app.py`):**
    *   `GET /`: Serves the main HTML page (`src/templates/index.html`).
    *   `GET /api/next-opening`: Accepts query parameters for dynamic preferences (`house`, `size`, `older_than_year`, `attended_mc_id`) and returns the top 3 recommended openings based on the core logic.

## 2. User Interface (`src/templates/index.html`)

*   **Layout:** Desktop-oriented three-column layout implemented using Flexbox:
    *   **Column 1 (Left):** Preferences (Houses checkbox list, Size dropdown, Older Than Year input, Apply/Defaults/Clear buttons).
    *   **Column 2 (Middle):** Results (Displays the list of 1-3 recommended openings, including name, time, stand, price, score). Shows loading/error/no results states.
    *   **Column 3 (Right):** Attended Master Classes (Displays list grouped by day with checkboxes for selection).
*   **Interaction:**
    *   JavaScript fetches initial recommendations and Master Class list on page load.
    *   Clicking "Apply Preferences", "Ville Defaults", or "Clear All" buttons updates the preferences in the left column and re-fetches recommendations.
    *   Checking/unchecking a Master Class checkbox in the right column *also* immediately re-fetches recommendations.
    *   Uses vanilla JavaScript for DOM manipulation and API calls (`fetch`).
    *   Styles are currently embedded within `<style>` tags in the HTML.

## 3. Data Flow Summary

1.  User opens the web page (`/`).
2.  Flask serves `index.html`.
3.  JavaScript fetches `master_classes.json` and populates the Master Class list.
4.  JavaScript makes an initial call to `/api/next-opening` (no specific preferences).
5.  Flask backend (`/api/next-opening`):
    *   Ensures data is loaded (from `Material/` files and `master_classes.json`).
    *   Parses query parameters (if any).
    *   Calls `find_next_rare_opening` in `src/core_logic.py` with combined data and dynamic preferences (including excluded MC wines).
    *   Receives top 3 results.
    *   Returns results as JSON.
6.  JavaScript receives JSON and displays the recommendations (or loading/error/no results message).
7.  User interacts with Preferences or Master Classes.
8.  Relevant interaction triggers a new call to `/api/next-opening` with updated query parameters (Steps 5-6 repeat).

## 4. Known Limitations / Areas for Improvement (prior to UX overhaul)

*   **Mobile Experience:** The three-column layout is not suitable for mobile devices.
*   **UI Polish:** Styling is basic; interactions could be smoother.
*   **List Interaction:** Selecting from long lists (Houses, Master Classes) via simple checkboxes/scrolling is inefficient on mobile.
*   **Error Handling:** Basic error messages are shown, but could be more user-friendly.
*   **Data Freshness:** Data is loaded on startup; relies on Flask process restart or time-based reload for updates to source files.