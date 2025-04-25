import os
import sys
import json
import re
from flask import Flask, jsonify, render_template, request
from datetime import datetime, timedelta

# Ensure the src directory is in the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.core_logic import load_all_data, find_next_rare_opening

# --- Flask App Initialization ---
app = Flask(__name__)

# --- Constants for MC Time Parsing ---
EVENT_YEAR = 2025
EVENT_DATES = {
    "TORSTAI": f"{EVENT_YEAR}-04-24",  # Thursday
    "PERJANTAI": f"{EVENT_YEAR}-04-25",  # Friday (Finnish)
    "LAUANTAI": f"{EVENT_YEAR}-04-26",  # Saturday (Finnish)
    # Add other days if necessary
}
MC_DURATION_MINUTES = 60  # Assume 1 hour duration
# ----------------------------------

# --- Global Data Store ---
# Load data once when the app starts
ALL_DATA = None
LAST_LOAD_TIME = None
DATA_LOAD_ERROR = None
MASTER_CLASSES_DATA = None


def load_data_if_needed():
    """Loads data from files if not already loaded or if outdated."""
    global ALL_DATA, LAST_LOAD_TIME, DATA_LOAD_ERROR, MASTER_CLASSES_DATA
    now = datetime.now()
    # Reload data if older than, say, 1 hour (adjust as needed)
    # Or if it hasn't been loaded yet
    if ALL_DATA is None or (now - LAST_LOAD_TIME).total_seconds() > 3600:
        print(f"[{now}] Loading/Reloading data...")
        try:
            material_dir = os.path.join(project_root, "Material")
            ALL_DATA = load_all_data(material_dir)

            # Load and Pre-process master class data
            master_classes_path = os.path.join(app.static_folder, "master_classes.json")
            if os.path.exists(master_classes_path):
                with open(master_classes_path, "r", encoding="utf-8") as f:
                    raw_mc_data = json.load(f)

                processed_mc_data = []
                for mc in raw_mc_data:
                    try:
                        raw_day_string = mc.get("day", "")
                        time_str = mc.get("time", "")

                        # Extract only the first word (day name) and uppercase it
                        day_name_match = re.match(r"^(\w+)", raw_day_string)
                        day_name_upper = (
                            day_name_match.group(1).upper() if day_name_match else ""
                        )

                        date_str = EVENT_DATES.get(day_name_upper)

                        if date_str and time_str:
                            # Combine date and time, assuming HH:MM format for time
                            start_dt_str = f"{date_str} {time_str}"
                            mc["start_datetime"] = datetime.strptime(
                                start_dt_str, "%Y-%m-%d %H:%M"
                            )
                            mc["end_datetime"] = mc["start_datetime"] + timedelta(
                                minutes=MC_DURATION_MINUTES
                            )
                        else:
                            mc["start_datetime"] = None
                            mc["end_datetime"] = None
                            print(
                                f"Warning: Could not parse datetime for MC: {mc.get('title')} (Raw Day: '{raw_day_string}', Time: '{time_str}')",
                                file=sys.stderr,
                            )
                        processed_mc_data.append(mc)
                    except ValueError as ve:
                        print(
                            f"Warning: Invalid datetime format for MC: {mc.get('title')} (Raw Day: '{raw_day_string}', Time: '{time_str}'). Error: {ve}",
                            file=sys.stderr,
                        )
                        mc["start_datetime"] = None
                        mc["end_datetime"] = None
                        processed_mc_data.append(mc)  # Still append, but without times
                    except (
                        Exception
                    ) as inner_e:  # Catch other potential errors during MC processing
                        print(
                            f"Error processing MC item {mc.get('title')}: {inner_e}",
                            file=sys.stderr,
                        )
                        mc["start_datetime"] = None
                        mc["end_datetime"] = None
                        processed_mc_data.append(mc)

                MASTER_CLASSES_DATA = processed_mc_data
                print(
                    f"[{now}] Loaded and processed {len(MASTER_CLASSES_DATA)} master classes."
                )
            else:
                MASTER_CLASSES_DATA = []
                print(
                    f"[{now}] WARNING: master_classes.json not found in static folder."
                )

            LAST_LOAD_TIME = now
            DATA_LOAD_ERROR = None
            print(f"[{now}] Main data loaded successfully.")
        except Exception as e:
            ALL_DATA = None
            MASTER_CLASSES_DATA = None
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
    if MASTER_CLASSES_DATA is None:
        print(
            "Warning: Master class data not loaded, cannot exclude wines from attended classes."
        )

    # --- Parse Preferences from Query Parameters --- #
    dynamic_preferences = {}
    excluded_wines = set()

    pref_houses = request.args.getlist("house")
    if pref_houses:
        dynamic_preferences["houses"] = pref_houses

    pref_size = request.args.get("size")
    if pref_size and pref_size != "any":
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

    pref_older_than = request.args.get("older_than_year")
    if pref_older_than:
        try:
            dynamic_preferences["older_than_year"] = int(pref_older_than)
        except ValueError:
            return (
                jsonify({"error": "Invalid year format for older_than parameter."}),
                400,
            )

    # --- Check for ignore_tasted flag --- #
    ignore_tasted_flag = request.args.get("ignore_tasted", "false").lower() == "true"
    if ignore_tasted_flag:
        dynamic_preferences["ignore_tasted"] = True
    # ---------------------------------- #

    # --- Get wines and time slots from attended Master Classes --- #
    attended_mc_ids = request.args.getlist("attended_mc_id")
    attended_mc_slots = []
    excluded_wines_from_mc = set()  # Renamed to be specific

    if attended_mc_ids and MASTER_CLASSES_DATA:
        for mc_id in attended_mc_ids:
            found_mc = None
            for mc in MASTER_CLASSES_DATA:
                # Use the pre-processed data
                identifier = (
                    mc.get("link") or f"{mc.get('presenter')}-{mc.get('title')}"
                )
                if identifier == mc_id:
                    found_mc = mc
                    break
            if found_mc:
                # Collect the slot if datetimes are valid
                if found_mc.get("start_datetime") and found_mc.get("end_datetime"):
                    attended_mc_slots.append(
                        {
                            "start": found_mc["start_datetime"],
                            "end": found_mc["end_datetime"],
                        }
                    )
                # Collect wines to potentially exclude (based on flag later)
                if found_mc.get("wines"):
                    excluded_wines_from_mc.update(found_mc["wines"])

    # Add collected data to dynamic preferences
    # Conditionally add MC wines to exclusion list
    if excluded_wines_from_mc and not ignore_tasted_flag:
        dynamic_preferences["excluded_wines"] = list(excluded_wines_from_mc)
        # print(f"DEBUG: Excluding MC wines because ignore_tasted is False: {excluded_wines_from_mc}")
    elif excluded_wines_from_mc:
        # Ensure the key exists but is empty if ignore_tasted is True, so core_logic doesn't mix things up
        # If the flag is true, we still collected them, but we don't pass them for exclusion.
        # dynamic_preferences["excluded_wines"] = [] # This line might be redundant if core_logic handles absence okay
        pass  # Don't add MC wines to exclusion list if ignore_tasted is True
        # print(f"DEBUG: NOT excluding MC wines because ignore_tasted is True: {excluded_wines_from_mc}")

    if attended_mc_slots:
        dynamic_preferences["attended_mc_slots"] = attended_mc_slots
    # ---------------------------------------------------------- #

    # --- Determine Current Time (Allow Override for Testing) --- #
    custom_time_str = request.args.get("custom_time")

    # Get server's naive time (which we know is UTC)
    current_time_naive_utc = datetime.now()

    # --- ADJUSTMENT FOR EASIEST FIX ---
    # Add 3 hours to approximate EEST (since event is during EEST/UTC+3)
    current_time_approx_eest = current_time_naive_utc + timedelta(hours=3)
    current_time = current_time_approx_eest  # Pass this approximated EEST time
    # ----------------------------------

    # --- Update Logging (Optional but Recommended) ---
    print(
        f"LOG_APP: Request received. Server Naive Time (UTC): {current_time_naive_utc.isoformat()}",
        file=sys.stderr,
    )
    print(
        f"LOG_APP: Approximated Naive EEST passed to core: {current_time.isoformat()}",
        file=sys.stderr,
    )
    # --------------------------

    # --- Pass preferences (including excluded wines) to core logic --- #
    next_openings = find_next_rare_opening(
        ALL_DATA,
        current_time,
        dynamic_preferences=dynamic_preferences if dynamic_preferences else None,
    )
    # -------------------------------------------------------------- #

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
    # This block is for local testing ONLY.
    # Production servers (Gunicorn, PythonAnywhere) will import the 'app' object directly.
    # If you need to run locally for testing, you can temporarily add:
    # app.run(host='0.0.0.0', debug=True, port=5000) # Use a specific port
    pass  # Or just leave empty
