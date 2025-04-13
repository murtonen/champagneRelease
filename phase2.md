# Phase 2: Frontend Preference Customization

## Goal

Allow users to dynamically set preferences (Houses, Bottle Size, Age) through the web interface and see the recommended openings update based on their selections. Include a shortcut button to apply Ville's specific preferences.

## Plan

1.  **UI Enhancements (`src/templates/index.html`):**
    *   Add a "Preferences" section to the HTML.
    *   Dynamically generate checkboxes for all unique `house_names`. Requires passing the house list from the Flask backend to the template.
    *   Add controls for bottle size selection (e.g., a dropdown: Any, Magnum+).
    *   Add an input field for the `older_than_year` preference.
    *   Add a "Ville Preferences" button.
    *   Add an "Apply Preferences" button.

2.  **Frontend JavaScript (`src/templates/index.html`):**
    *   Modify the `fetch` logic:
        *   Trigger fetch on "Apply Preferences" click (and potentially initially).
        *   Gather selected values from the UI controls (houses, size, year).
        *   Construct a query string based on selected preferences (e.g., `?house=X&house=Y&size=magnum&older_than=1990`).
        *   Append the query string to the `/api/next-opening` fetch URL.
    *   Implement "Ville Preferences" button logic:
        *   Set the UI controls to match Ville's predefined preferences (Houses: Bollinger, Charles Heidsieck, Palmer; Size: Magnum+; Year <= 1990).
        *   Trigger the fetch logic after setting the controls.

3.  **Backend API (`src/app.py`):**
    *   Modify the `/` route to pass the `house_names` list to the `index.html` template.
    *   Modify the `/api/next-opening` endpoint:
        *   Import `request` from Flask.
        *   Read query parameters (`house`, `size`, `older_than`) using `request.args`.
        *   Parse these parameters into a `dynamic_preferences` dictionary (handle potential type errors, multiple values for houses).
        *   Pass this `dynamic_preferences` dict to `find_next_rare_opening`.
        *   Adjust the "No openings found" message based on whether dynamic preferences were applied.

4.  **Core Logic (`src/core_logic.py`):**
    *   Modify `find_next_rare_opening` function signature to accept `dynamic_preferences=None`.
    *   Inside the function, check if `dynamic_preferences` is provided.
        *   If yes, use it for scoring logic.
        *   If no (or empty), use the default preferences loaded from `preferences.txt`.
    *   Ensure the scoring logic correctly uses the determined preference source (dynamic or file-based).

5.  **Documentation (`design_plan.md`, `knowledge.md`):**
    *   Update relevant sections (UI, API, Core Logic) to describe the new dynamic preference handling via query parameters.

## Implementation Status

*   Steps 1-4 Completed.
*   Step 5 (Documentation Update) Pending. 