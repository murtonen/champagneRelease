# Grand Champagne Helper - Design Plan

## 1. Project Goal

To develop a web application that identifies and displays the next available rare champagne opening(s) at the Grand Champagne event. The application must consider the user's personal tasting schedule (to avoid conflicts and duplicate champagnes) and preferences.
The primary output should be the next highly preferred opening(s) (Preference Score >= 2), showing up to 3 simultaneous or chronologically next preferred options.

## 2. Architecture

-   **Backend:** Python using the Flask framework.
    -   **Data Parsing Module (`src/data_parser.py`):** Responsible for reading and extracting relevant information from the provided PDF and TXT files (`Material/Rare_schedule_2025.pdf`, `Material/Wine_list_2025.pdf`, `Material/tastings.txt`, `Material/preferences.txt`).
    -   **Core Logic Module (`src/core_logic.py`):** Contains the core logic to:
        -   Combine parsed data (rare schedule, prices, tastings, preferences).
        -   Normalize/match champagne names across different lists.
        -   Determine upcoming rare openings based on the current time.
        -   Add price information (glass price) to rare schedule entries using a two-step house/specific name matching approach.
        -   Filter out openings that conflict with the user's tasting schedule (read from `tastings.txt`).
        -   Filter out openings featuring champagnes the user will already try in tastings (`tastings.txt`).
        -   Score openings based on matching user preferences (`preferences.txt`: house, size, age).
        -   Identify the next available, non-conflicting, highly preferred opening(s) (Score >= 2, up to 3 results).
    -   **API Endpoint(s):** Flask route `/api/next-opening` serves the calculated information to the frontend.
-   **Frontend:** Simple HTML, CSS, and JavaScript (`src/templates/index.html`).
    -   **Status:** Basic HTML/CSS/JS implemented, served via Flask route `/`. Fetches and displays data from `/api/next-opening`.
-   **Data Handling:**
    -   Parses input files from `Material/` on Flask app startup.
    -   Stores parsed data in memory.

## 3. Data Processing Strategy

-   **PDF Parsing (`Rare_schedule_2025.pdf`, `Wine_list_2025.pdf`):**
    -   **Status:** Implemented in `src/data_parser.py` using `pdfplumber`.
    -   **Extraction (`Rare_schedule_2025.pdf`):** Extracts date, time, name, stand.
    -   **Extraction (`Wine_list_2025.pdf`):** Detects Stands and Houses, parses Price Lines (handling optional bottle price). Outputs wine details dict and list of house names.
    -   **Name Matching (Implemented in `find_price_for_rare_wine` in `src/core_logic.py`):
        -   Uses a two-step House/Specific matching process with fuzzy matching (`thefuzz`) on the specific part.

-   **TXT Parsing (`tastings.txt`, `preferences.txt`):**
    -   **Status:** Implemented in `src/data_parser.py`.
    -   Extracts tasting slots/names and preference criteria (sizes, year, houses).

-   **Data Merging & Filtering (Implemented in `src/core_logic.py`):**
    -   Combines schedule with prices.
    -   Filters by time, tasting conflicts, and tasted champagnes.
    -   Applies preference scoring based on house, size, age.
    -   Sorts by time, then score (descending).
    -   **Final Selection:** Filters for score >= 2 and returns top 1-3 results.

## 4. Technology Stack

-   **Programming Language:** Python 3.x
-   **Web Framework:** Flask
-   **PDF Parsing:** `pdfplumber`
-   **Fuzzy Matching:** `thefuzz` (with `python-Levenshtein`)
-   **Date/Time Handling:** Python `datetime` module
-   **Frontend:** HTML5, CSS3, JavaScript (vanilla)

## 5. API Design

-   `GET /api/next-opening`:
    -   **Action:** Calculates and returns the details of the next available highly preferred rare opening(s).
    -   **Response (JSON):** List of opening objects `[{name, time, stand, glass_price, preference_score}]` or `{"message": "..."}` if none available.

## 6. User Interface

-   A single-page web view (`index.html`).
-   Fetches data via JavaScript `fetch`.
-   Displays the recommended opening(s) with name, time, stand, price, and score.

## 7. Deployment

-   Currently runs locally using `python -m src.app`.
-   Deployable via standard Python web hosting options.

## 8. Future Enhancements

-   Allow uploading files through the web interface.
-   More sophisticated preference matching.
-   User accounts.
-   Real-time updates.
-   More robust error handling (e.g., for file parsing).
-   Mobile-responsive design.