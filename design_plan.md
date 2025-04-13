# Grand Champagne Helper - Design Plan

## 1. Project Goal

To develop a web application that identifies and displays the next available rare champagne opening at the Grand Champagne event. The application must consider the user's personal tasting schedule (to avoid conflicts and duplicate champagnes) and potentially their preferences.
The primary output should be the single next best opening, but if multiple highly preferred openings occur simultaneously (or very close together), up to 3 may be highlighted.

## 2. Architecture

-   **Backend:** Python using the Flask framework. Its simplicity is well-suited for this focused application.
    -   **Data Parsing Module (`src/data_parser.py`):** Responsible for reading and extracting relevant information from the provided PDF and TXT files (`Material/Rare_schedule_2025.pdf`, `Material/Wine_list_2025.pdf`, `Material/tastings.txt`, `Material/preferences.txt`).
-   **Scheduling & Filtering Logic Module:** Contains the core logic to:
    **Scheduling & Filtering Logic Module (`src/core_logic.py` - TBD):** Contains the core logic to:
        -   Combine parsed data (rare schedule, prices, tastings, preferences).
        -   Normalize/match champagne names across different lists.
        -   Determine upcoming rare openings based on the current time.
        -   Add price information (glass price) to rare schedule entries.
        -   Filter out openings that conflict with the user's tasting schedule (read from `tastings.txt`, assuming a 1-hour duration per tasting).
        -   Filter out openings featuring champagnes the user will already try in tastings (`tastings.txt`).
        -   Score or rank openings based on matching user preferences (`preferences.txt`).
        -   Identify the next available, non-conflicting opening(s), potentially highlighting up to 3 simultaneous preferred options.
    -   **API Endpoint(s):** Flask routes that will process requests and serve the calculated information (e.g., the next available opening) to the frontend.
-   **Frontend:** Simple HTML, CSS, and potentially minimal JavaScript for displaying the information retrieved from the backend. No complex client-side framework is anticipated initially.
-   **Data Handling:**
    -   Parse input files (`Material/*.pdf`, `Material/*.txt`) using `src/data_parser.py`, likely when the Flask application starts or on the first request.
    -   Store parsed data in memory in suitable Python data structures (e.g., lists of dictionaries, custom objects). Persistence (like a database) is likely not needed for the core use case but could be added later.

## 3. Data Processing Strategy

-   **PDF Parsing (`Rare_schedule_2025.pdf`, `Wine_list_2025.pdf`):**
    -   **Status:** Implemented in `src/data_parser.py`.
    -   **Tool:** Using `pdfplumber`.
    -   **Extraction (`Rare_schedule_2025.pdf`):**
        -   Structure: Detects Day Headers (e.g., `THURSDAY 24.4.`), then parses subsequent lines containing `Time Name StandNumber`.
        -   Output: List of dicts `{'date': str(YYYY-MM-DD), 'time': str(HH:MM), 'name': str, 'stand': str}`.
    -   **Extraction (`Wine_list_2025.pdf`):**
        -   Structure: Detects Stand Headers (e.g., `STAND_NAME STAND X`), then the House Name on the next relevant line, followed by Price Lines. The parsing logic identifies house names as standalone lines that don't start with a price (`X€`), aren't just grape info, aren't ignored headers (like RARE CHAMPAGNE), aren't purely numeric, and contain at least one letter. The price line regex (`PRICE_LINE_PATTERN`) is designed to handle potentially missing bottle prices (only glass price is mandatory).
        -   Output:
            - Dictionary mapping `Full Name` (House + Specific) to a dict `{'glass_price': str, 'bottle_price': str|None, 'stand_number': str, 'stand_name': str}`.
            - A sorted list of unique `House Names` identified during parsing.
    -   **Challenges:** PDF layout inconsistencies might still require minor tolerance adjustments in `pdfplumber`. Error handling for parsing failures is crucial.
    -   **Name Matching (Implemented in `find_price_for_rare_wine` in `src/core_logic.py`):**
        -   Uses a two-step approach leveraging the identified list of House Names.
        -   Step 1: Identify the House. Iterate through the known `House Names` and check if the beginning of the `rare_wine_name` matches one.
        -   Step 2: Match Specific Wine. If a house is matched, extract the remaining part of the `rare_wine_name` (the specific description). Filter the `wine_details` to only include wines from the identified house. Normalize and fuzzy match (using `thefuzz.WRatio`) the extracted specific description against the normalized specific descriptions of wines from that house only.
        -   This avoids attempting to match the full name against the entire wine list, significantly improving accuracy.

-   **TXT Parsing (`tastings.txt`, `preferences.txt`):**
    -   **Status:** Implemented in `src/data_parser.py`.
    -   **`tastings.txt` Format & Parsing:**
        -   Structure: Day header (`Day DD.MM.YYYY klo HH.MM:`), followed by champagne names, separated by blank lines.
        -   Output: List of dicts `{'start': datetime, 'end': datetime, 'names': [str, ...]}` and a set of unique tasted champagne names.
    -   **`preferences.txt` Format & Parsing:**
        -   Structure: Semi-free text. Parsed using regex/keyword matching.
        -   Output: Dict `{'sizes': [str, ...], 'older_than_year': int|None, 'houses': [str, ...]}`.

-   **Data Merging & Filtering (To be implemented in `src/core_logic.py`):**
    -   Create a consolidated list of upcoming rare openings with their names, times, and prices.
    -   Get the current time using Python's `datetime` module.
    -   Iterate through the rare openings:
        -   Discard openings in the past.
        -   Discard openings whose time slot overlaps with any user tasting (`tasting_start_time` to `tasting_start_time + 1 hour`).
        -   Discard openings whose champagne name is present in the user's tasted champagnes list.
        -   (Optional) Score or flag openings matching user preferences.
            -   **Implementation:** Calculate a score for each remaining opening based on `preferences.txt`.
            -   **Scoring Rules (Initial):**
                -   +1 point if opening's House matches preferred `houses`.
                -   +1 point if opening's bottle size (parsed from name) matches preferred `sizes`.
                -   +1 point if opening's year (parsed from name) is <= preferred `older_than_year`.
            -   Store the calculated score with the opening data.
        -   The result is a list of available, non-conflicting future rare openings, potentially ranked by preference. Identify the soonest one(s).
            -   **Sorting:** Keep sorting primarily by time to find the *next* opening. The score will be displayed.

## 4. Technology Stack

-   **Programming Language:** Python 3.x
-   **Web Framework:** Flask
-   **PDF Parsing:** `pdfplumber` (recommended) or `PyPDF2`
-   **Date/Time Handling:** Python `datetime` module
-   **Frontend:** HTML5, CSS3, JavaScript (vanilla, if needed)

## 5. API Design (Example)

-   `GET /api/next-opening`:
    -   **Action:** Calculates and returns the details of the very next available rare opening based on the server's current time and the loaded data.
    -   **Response (JSON):**
        ```json
        {
          "name": "Champagne Example Prestige",
          "time": "2025-03-15T14:30:00", // ISO format
          "price": "€55", // Or numeric + currency code
          "matches_preferences": true // Optional
        }
        // Or if none are available:
        {
          "message": "No further rare openings available matching your schedule."
        }
        ```
-   `GET /api/available-openings`:
    -   **Action:** Returns a list of *all* future available openings.
    -   **Response (JSON):** A list of objects similar to the `/api/next-opening` response.

## 6. User Interface (Conceptual)

-   A single-page web view.
-   Displays the current time.
-   Section: "Your Next Tasting" (displays info from `tastings.txt` if relevant).
-   Section: "Next Available Rare Opening"
    -   Champagne Name
    -   Scheduled Time
    -   Price
    -   (Optional) Indicator if it matches preferences.
-   (Optional) A list of the subsequent few available openings.

## 7. Deployment

-   Could be run locally using `flask run`.
-   For wider access, deployable via standard Python web hosting options (e.g., PythonAnywhere, Heroku, Render) or using Docker containers.

## 8. Future Enhancements

-   Allow uploading files through the web interface instead of relying on local files.
-   More sophisticated preference matching and filtering.
-   Handling multi-day events explicitly.
-   User accounts for saving different schedules/preferences.
-   Real-time updates (e.g., using WebSockets or polling).
-   Error handling for file not found or parsing errors.
-   Adding location information if available in the PDFs.
-   Mobile-responsive design. 