# Grand Champagne Helper - Current State (Post-UX Overhaul)

This document summarizes the state of the project after refactoring the UI to a mobile-first tabbed interface and deploying to PythonAnywhere.

## 1. Core Functionality

*   **Data Loading:** The Flask backend (`src/app.py`) loads data on startup (and reloads hourly) from files in the `Material/` directory using parsers in `src/data_parser.py`:
    *   `Rare_schedule_2025.pdf`: Parses rare champagne opening times, names, and stands.
    *   `Wine_list_2025.pdf`: Parses wine details (including glass prices) and identifies house names.
    *   `tastings.txt`: Parses personal tasting schedule slots and tasted champagnes.
    *   `preferences.txt`: Parses baseline user preferences (houses, size, age).
    *   `static/master_classes.json`: Loads pre-processed Master Class details (day, time, presenter, title, wines).
*   **Recommendation Logic (`src/core_logic.py`):**
    *   Combines schedule and price data (using fuzzy name matching).
    *   Filters openings based on:
        *   Current time (only future openings, determined per request).
        *   Conflicts with personal tasting schedule (`tastings.txt`).
        *   Champagnes already tasted (`tastings.txt`).
        *   Wines tasted in selected Master Classes (`master_classes.json` + user selection).
    *   Scores remaining openings based on dynamic preferences: **+1** for matching House, **+1** for matching Size (Magnum+), **+1** if vintage is less than or equal to the specified year. Uses a local copy of preferences per request to avoid state leakage.
    *   Returns the **top 3** openings with a score >= 2, sorted by time, then score.
*   **API (`src/app.py`):**
    *   `GET /`: Serves the main HTML page (`src/templates/index.html`).
    *   `GET /api/next-opening`: Accepts query parameters for dynamic preferences (`house`, `size`, `older_than_year`, `attended_mc_id`). Returns the top 3 recommended openings based on the core logic. Handles `size=magnum` correctly to represent Magnum+ sizes. Correctly reads `older_than_year`.

## 2. User Interface (`src/templates/index.html`)

*   **Layout:** Mobile-first, bottom-tabbed interface.
    *   **Header:** Simple title.
    *   **Content Area:** Scrollable container holding the active tab's content.
    *   **Navigation Bar:** Fixed bottom bar with buttons for switching tabs (Recommendations, Preferences, Master Classes).
*   **Tabs & Interaction:**
    *   **Recommendations Tab (Default):**
        *   Displays the list of 1-3 recommended openings using a clear card layout. Emphasizes Name and Time.
        *   Shows loading/error/no results states within the tab content area.
        *   Loads initially using "Ville Defaults".
        *   Automatically refreshes every 2 minutes to stay current with time.
    *   **Preferences Tab:**
        *   Controls stacked vertically.
        *   **House Selection:** Searchable filter input above a checkbox list.
        *   **Bottle Size:** Dropdown ("Any", "Magnum+").
        *   **Age:** Input field ("Vintage (or Older):", inclusive).
        *   **Buttons:** "Ville Defaults" (applies predefined settings), "Clear All Preferences".
        *   *Any change* to a preference control automatically triggers a refresh of the Recommendations tab.
    *   **Master Classes Tab:**
        *   Displays list grouped by day with checkboxes for selection.
        *   Selected items have a slight visual highlight.
        *   *Any change* to a checkbox automatically triggers a refresh of the Recommendations tab.
*   **Technology:** Uses vanilla JavaScript for DOM manipulation, tab switching, API calls (`fetch`), and dynamic filtering/updates. Styles are embedded within `<style>` tags in the HTML.

## 3. Data Flow Summary

1.  User opens the web page (`/`).
2.  Flask serves `index.html`.
3.  JavaScript fetches `master_classes.json` and populates the Master Class list.
4.  JavaScript applies "Ville Defaults" to preference controls (without fetching).
5.  JavaScript makes an initial call to `/api/next-opening` using the default preferences.
6.  Flask backend (`/api/next-opening`):
    *   Ensures data is loaded (from `Material/` files and `master_classes.json`).
    *   Parses query parameters.
    *   Creates effective preferences (base + dynamic) for the request.
    *   Calls `find_next_rare_opening` in `src/core_logic.py` with data and effective preferences.
    *   Receives top 3 results.
    *   Returns results as JSON.
7.  JavaScript receives JSON and displays the recommendations (or loading/error/no results message).
8.  User interacts with Preferences or Master Classes, OR 2-minute timer fires.
9.  Relevant interaction/timer triggers a new call to `/api/next-opening` with current preferences (Steps 6-7 repeat).

## 4. Deployment & Known Issues

*   **Deployment:** Successfully deployed to PythonAnywhere using manual configuration, WSGI, and static file mapping. Git repository is used for code management.
*   **Known Issues:**
    *   Persistent, non-critical linter errors reported in `src/templates/index.html` (potentially related to Jinja tags or linter configuration).
    *   Performance: No specific optimizations like debouncing implemented for preference changes (refresh triggers on every change).
    *   Error Handling: Basic, could be more user-friendly for edge cases (e.g., file parsing errors during load).
    *   Data Freshness: Main data reload happens hourly or on app restart; relies on source files (`Material/`, `static/`) being updated on the server manually or via `git pull`.