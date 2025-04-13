# Grand Champagne Helper - Next Steps: UI/UX Overhaul Plan

This document outlines the plan to refactor the UI for a mobile-first experience, focusing on usability at the event.

## Target Context & Goals

*   **Primary User:** Attendee using a mobile phone at the Grand Champagne event.
*   **Primary Need:** Quickly see the next best rare champagne(s) to try based on schedule and preferences.
*   **Key Goals:**
    *   Optimize for mobile portrait view.
    *   Prioritize displaying recommendations clearly and immediately.
    *   Simplify preference and Master Class selection.
    *   Improve overall usability and visual polish for the event context.

## Proposed Strategy: Mobile-First Tabbed Interface

Shift from the current three-column desktop layout to a bottom-tabbed navigation interface common in mobile applications.

**Tabs:**

1.  **Recommendations (Default):** Shows the top 1-3 recommended openings.
2.  **Preferences:** Allows selection of Houses, Size, and Age.
3.  **Master Classes:** Allows selection of attended Master Classes.

## Detailed Plan

**A. Implement Responsive Tabbed Layout:**

1.  **HTML (`index.html`):**
    *   Create a main container for tab content.
    *   Create separate `div`s for the content of each tab (`#recommendations-tab-content`, `#preferences-tab-content`, `#masterclass-tab-content`).
    *   Create a fixed bottom navigation bar (`nav`) containing buttons/links for each tab.
2.  **CSS (`style.css` or inline):**
    *   Style the bottom tab bar (layout, appearance, active state).
    *   Use CSS to show only the active tab's content `div` and hide others.
    *   Ensure layout within each tab content `div` is responsive (vertical stacking on mobile).
    *   Use media queries (`@media (min-width: 768px) { ... }`) to potentially adjust layout for larger screens if desired (e.g., side-by-side elements within tabs on tablets).
3.  **JavaScript:**
    *   Add event listeners to tab buttons.
    *   Implement logic to toggle visibility of content `div`s based on the selected tab.
    *   Update the visual "active" state of the selected tab button.

**B. Enhance Recommendations Display (Tab 1 Content):**

1.  **Layout:** Use clear card or list item design for each recommendation.
2.  **Hierarchy:** Emphasize Champagne Name and Time. Make Stand, Price, Score clearly visible but secondary.
3.  **Readability:** Use appropriate font sizes, padding, and contrast.
4.  **States:** Implement clear loading (e.g., skeleton placeholders), error, and "no results" states *within this tab's content area*.
5.  **(Optional):** Consider a "Refresh" button, although auto-refresh on preference changes is preferred.

**C. Streamline Preferences Interaction (Tab 2 Content):**

1.  **Layout:** Stack controls vertically.
2.  **House Selection:** Replace the multi-select box with a **searchable filter list**:
    *   Add an `<input type="text">` field.
    *   Use JavaScript to filter the list of house checkboxes below it as the user types.
3.  **Button Placement:** Group "Ville Defaults" and "Clear All" buttons clearly, likely at the bottom of this view.
4.  **Feedback:** Provide visual confirmation when defaults are applied or preferences are cleared.

**D. Improve Master Class Selection (Tab 3 Content):**

1.  **Layout:** Display the list grouped by day, stacked vertically.
2.  **Readability:** Ensure good spacing and clear distinction between days and classes.
3.  **Selection Indication:** Consider highlighting the entire list item slightly when its checkbox is selected.
4.  **(Optional):** Add search/filter if the list is excessively long.

**E. General & Event-Specific Polish:**

1.  **Auto-Refresh:** Modify JavaScript so that *any* change in the Preferences tab or Master Classes tab automatically triggers `fetchRecommendations()`. The "Apply Preferences" button can potentially be removed or repurposed.
2.  **Performance:** Optimize data fetching and display.
3.  **Touch Targets:** Ensure all interactive elements are adequately sized and spaced for touch interaction.

## Implementation Order Suggestion

1.  **Task A:** Implement the basic tabbed structure (HTML, CSS, JS for tab switching).
2.  **Task B:** Refine the display of recommendations within Tab 1.
3.  **Task C:** Implement the improved House selection (searchable list) and layout within Tab 2.
4.  **Task D:** Refine the Master Class list display within Tab 3.
5.  **Task E:** Implement auto-refresh logic and general polish.
