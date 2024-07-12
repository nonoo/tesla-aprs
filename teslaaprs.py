from helper import *
from aprs import *
from log import *
from tesla import *

import teslapy
import sys
import getopt
import sys
import os
import time
import signal
import multiprocessing
import logging

tesla_stream_process_handle = None
last_report_ts = None

def sigint_handler(signum, frame):
    if tesla_stream_process_handle:
        tesla_stream_process_handle.terminate()
        tesla_stream_process_handle.join()
    sys.exit(0)

def tesla_stream_cb(data):
    global stream_msg_queue
    stream_msg_queue.put(data)

def tesla_stream_process(tesla, vehicle_nr, msg_queue):
    global stream_msg_queue
    stream_msg_queue = msg_queue
    vehicle = tesla_get_vehicle(tesla, vehicle_nr)
    log("Starting Tesla update stream...")
    vehicle.stream(tesla_stream_cb) # This call blocks
    sys.exit(1)

def update(tesla, vehicle_nr, callsign, msg):
    global last_report_ts

    vehicle_last_seen_ts, vehicle_charge_percent, vehicle_lat, vehicle_lng, vehicle_speed_kmh, vehicle_heading, vehicle_altitude_m, vehicle_range_km, vehicle_shift_state = tesla_get_data()

    if vehicle_last_seen_ts == last_report_ts:
        if vehicle_last_seen_ts:
            log("Last update same as last report, skipping")
        return

    last_report_ts = vehicle_last_seen_ts

    state = f"Batt. {vehicle_charge_percent}% {vehicle_range_km}km"

    vehicle = tesla_get_vehicle(tesla, vehicle_nr)
    if vehicle.available():
        log("Vehicle awake, querying data...")
        climate_state = vehicle['climate_state']
        if climate_state:
            state += " " + str(climate_state['outside_temp']) + "C"

        charge_state = vehicle['charge_state']
        if charge_state:
            charger_pwr_kw = charge_state['charger_power']
            charger_rem_mins = charge_state['minutes_to_full_charge']

    if charger_pwr_kw:
        charger_pwr_str = str(charger_pwr_kw) + "kW"
        log(f"  Charger pwr: {charger_pwr_str}")
        state += f" (Chg {charger_pwr_str}"

        if charger_rem_mins:
            hours, mins = get_hours_and_mins_from_mins(charger_rem_mins)
            charger_rem_str = f"{hours}h{mins}m"
            log(f"  Charge rem.: {charger_rem_str}")
            state += f"/{charger_rem_str}"

        state += ")"
    elif not vehicle_shift_state:
        log("  Parked")
        state += " (Parked)"

    send_aprs_location_report(callsign, vehicle_last_seen_ts, vehicle_lat, vehicle_lng, vehicle_speed_kmh,
                              vehicle_heading, vehicle_altitude_m, msg, state)

def print_usage():
    script_name = os.path.basename(__file__)
    print("tesla-aprs - Send Tesla vehicle location data to the APRS-IS https://github.com/nonoo/tesla-aprs")
    print(f"Usage: python {script_name} -e <email> -c <callsign> -m <msg>")
    print("Options:")
    print("  -e, --email\t\tEmail address for Tesla account")
    print("  -c, --callsign\tAPRS callsign")
    print("  -m, --msg\t\tAPRS message")
    print("  -s, --silent\t\tSuppress output")
    print("  -i, --interval\t\tInterval in seconds between updates, default 30")

def main(argv):
    email = os.environ.get('TESLAAPRS_EMAIL')
    if email:
        email = email.strip()

    callsign = os.environ.get('TESLAAPRS_CALLSIGN')
    if callsign:
        callsign = callsign.strip().upper()

    msg = os.environ.get('TESLAAPRS_MSG')
    if msg:
        msg = msg.strip()
    else:
        msg = "github.com/nonoo/tesla-aprs"

    if os.environ.get('TESLAAPRS_SILENT'):
        log_set_silent(True)

    interval_sec = os.environ.get('TESLAAPRS_INTERVAL')
    if interval_sec:
        interval_sec = int(interval_sec)
    else:
        interval_sec = 30

    vehicle_nr = os.environ.get('TESLAAPRS_VEHICLE_NR')
    if vehicle_nr:
        vehicle_nr = int(vehicle_nr)
    else:
        vehicle_nr = 0

    try:
        opts, _ = getopt.getopt(argv, "e:c:m:si:n:d", ["email=", "callsign=", "msg=", "silent=", "interval=", "vehiclenr=", "debug="])
    except getopt.GetoptError:
        print_usage()
        sys.exit(1)

    for opt, arg in opts:
        if opt in ("-e", "--email"):
            email = arg
        elif opt in ("-c", "--callsign"):
            callsign = arg.upper()
        elif opt in ("-m", "--msg"):
            msg = arg
        elif opt in ("-s", "--silent"):
            log_set_silent(True)
        elif opt in ("-i", "--interval"):
            interval_sec = int(arg)
        elif opt in ("-n", "--vehiclenr"):
            vehicle_nr = int(arg)
        elif opt in ("-d", "--debug"):
            logging.basicConfig(level=logging.DEBUG)

    if not email or not callsign:
        print_usage()
        sys.exit(1)

    signal.signal(signal.SIGINT, sigint_handler)

    tesla = teslapy.Tesla(email)
    if not tesla.authorized:
        refresh_token = os.environ.get('TESLAAPRS_REFRESH_TOKEN')
        if not refresh_token:
            refresh_token = input('Enter Tesla refresh token (see README for details): ')
        tesla.refresh_token(refresh_token=refresh_token)

    msg_queue = multiprocessing.Queue()
    global tesla_stream_process_handle
    tesla_stream_process_handle = multiprocessing.Process(target=tesla_stream_process, args=(tesla, vehicle_nr, msg_queue)).start()

    while True:
        while not msg_queue.empty():
            tesla_stream_process_data(msg_queue.get())

        update(tesla, vehicle_nr, callsign, msg)
        log(f"Sleeping for {interval_sec} seconds...")
        time.sleep(interval_sec)

if __name__ == "__main__":
    main(sys.argv[1:])
