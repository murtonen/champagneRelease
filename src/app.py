import os
import sys
from flask import Flask, jsonify, render_template, request
from datetime import datetime

# Ensure the src directory is in the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.core_logic import load_all_data, find_next_rare_opening

# --- Flask App Initialization ---
app = Flask(__name__)

# --- Global Data Store ---
# Load data once when the app starts
ALL_DATA = None
LAST_LOAD_TIME = None
DATA_LOAD_ERROR = None


def load_data_if_needed():
    """Loads data from files if not already loaded or if outdated."""
    global ALL_DATA, LAST_LOAD_TIME, DATA_LOAD_ERROR
    now = datetime.now()
    # Reload data if older than, say, 1 hour (adjust as needed)
    # Or if it hasn't been loaded yet
    if ALL_DATA is None or (now - LAST_LOAD_TIME).total_seconds() > 3600:
        print(f"[{now}] Loading/Reloading data...")
        try:
            material_dir = os.path.join(project_root, "Material")
            ALL_DATA = load_all_data(material_dir)
            LAST_LOAD_TIME = now
            DATA_LOAD_ERROR = None
            print(f"[{now}] Data loaded successfully.")
        except Exception as e:
            ALL_DATA = None  # Ensure data is None on error
            DATA_LOAD_ERROR = f"Failed to load data: {e}"
            print(f"[{now}] ERROR loading data: {e}", file=sys.stderr)


# Initial data load on startup
load_data_if_needed()


# --- Frontend Route ---
@app.route("/")
def index():
    """Serves the main HTML page."""
    # Ensure data is loaded for house list
    load_data_if_needed()
    house_list = []
    if ALL_DATA and "house_names" in ALL_DATA:
        house_list = sorted(list(ALL_DATA["house_names"]))  # Pass sorted list

    # Pass error status too, so template can show message if data failed
    data_load_error = DATA_LOAD_ERROR

    return render_template(
        "index.html", houses=house_list, data_load_error=data_load_error
    )


# --- API Endpoints ---
@app.route("/api/next-opening", methods=["GET"])
def get_next_opening():
    """API endpoint to get the next highly recommended rare opening(s)."""
    load_data_if_needed()

    if DATA_LOAD_ERROR:
        return (
            jsonify({"error": "Data loading failed", "details": DATA_LOAD_ERROR}),
            500,
        )
    if not ALL_DATA:
        return jsonify({"error": "Data not loaded"}), 500

    # --- Parse Preferences from Query Parameters --- #
    dynamic_preferences = {}
    pref_houses = request.args.getlist("house")  # Use getlist for multiple values
    if pref_houses:
        dynamic_preferences["houses"] = pref_houses

    pref_size = request.args.get("size")
    if pref_size:
        # Translate 'magnum' query param to list expected by core logic
        if pref_size == "magnum":
            dynamic_preferences["sizes"] = [
                "magnum",
                "jeroboam",
                "methuselah",
                "nabuchodonosor",
            ]
        # Add other size mappings if UI offers more options
        # else:
        #    dynamic_preferences['sizes'] = [pref_size]

    pref_older_than = request.args.get("older_than")
    if pref_older_than:
        try:
            dynamic_preferences["older_than_year"] = int(pref_older_than)
        except ValueError:
            return (
                jsonify({"error": "Invalid year format for older_than parameter."}),
                400,
            )
    # -------------------------------------------- #

    current_time = datetime.now()

    # --- Pass dynamic preferences to core logic --- #
    next_openings = find_next_rare_opening(
        ALL_DATA,
        current_time,
        dynamic_preferences=dynamic_preferences if dynamic_preferences else None,
    )
    # --------------------------------------------- #

    if not next_openings:
        # Message depends on whether preferences were applied
        message = (
            "No highly preferred rare openings available matching your schedule"
            + (" and selected preferences." if dynamic_preferences else ".")
        )
        return jsonify({"message": message}), 200

    # Format the response according to API design
    response_data = []
    for opening in next_openings:
        response_data.append(
            {
                "name": opening.get("name"),
                "time": (
                    opening.get("datetime").isoformat()
                    if opening.get("datetime")
                    else None
                ),
                "stand": opening.get("stand"),
                "glass_price": opening.get("glass_price"),
                "preference_score": opening.get("preference_score", 0),
            }
        )

    return jsonify(response_data)


# --- Main Execution ---
if __name__ == "__main__":
    # Note: debug=True is useful for development but should be False in production
    app.run(debug=True)
