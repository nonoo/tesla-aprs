from helper import *

import teslapy
import sys
import getopt
import sys
import os
import aprslib
import time
import signal
import multiprocessing

tesla_stream_proc = None
silent = False
last_report_ts = None

vehicle_last_seen_ts = None
vehicle_charge_percent = None
vehicle_lat = None
vehicle_lng = None
vehicle_speed_kmh = None
vehicle_heading = None
vehicle_altitude_m = None
vehicle_range_km = None
vehicle_shift_state = None

def sigint_handler(signum, frame):
    if tesla_stream_proc:
        tesla_stream_proc.terminate()
        tesla_stream_proc.join()
    sys.exit(0)

def log(*args, **kwargs):
    if not silent:
        print(*args, **kwargs)

def tesla_get_vehicle(tesla, vehicle_nr):
    vehicles = tesla.vehicle_list()
    if not vehicles:
        print("No registered vehicles")
        sys.exit(1)

    if vehicle_nr >= len(vehicles):
        print("Invalid vehicle number")
        sys.exit(1)

    return vehicles[vehicle_nr]

def tesla_stream_cb(data):
    global stream_msg_queue
    stream_msg_queue.put(data)

def tesla_stream_thread_handler(tesla, vehicle_nr, msg_queue):
    global stream_msg_queue
    stream_msg_queue = msg_queue
    vehicle = tesla_get_vehicle(tesla, vehicle_nr)
    log("Starting Tesla update stream...")
    vehicle.stream(tesla_stream_cb)
    sys.exit(1)

def tesla_stream_process_data(data):
    print(data) # TODO: remove, power field?
    log("Tesla update:")
    if 'timestamp' in data:
        global vehicle_last_seen_ts
        vehicle_last_seen_ts = data['timestamp'] / 1000 # Convert ms to s
        log(f"  Timestamp: {vehicle_last_seen_ts}")
    if 'soc' in data:
        global vehicle_charge_percent
        vehicle_charge_percent = data['soc']
        log(f"  Charge percent: {vehicle_charge_percent}%")
    if 'est_lat' in data:
        global vehicle_lat
        vehicle_lat = data['est_lat']
        log(f"  Latitude: {vehicle_lat}")
    if 'est_lng' in data:
        global vehicle_lng
        vehicle_lng = data['est_lng']
        log(f"  Longitude: {vehicle_lng}")
    if 'speed' in data:
        global vehicle_speed_kmh
        vehicle_speed_kmh = data['speed'] # Convert mph to kmh
        if not vehicle_speed_kmh:
            vehicle_speed_kmh = 0
        else:
            vehicle_speed_kmh = int(vehicle_speed_kmh * 1.60934)
        log(f"  Speed: {vehicle_speed_kmh}km/h")
    if 'est_heading' in data:
        global vehicle_heading
        vehicle_heading = data['est_heading']
        log(f"  Heading: {vehicle_heading}")
    if 'elevation' in data:
        global vehicle_altitude_m
        vehicle_altitude_m = data['elevation']
        log(f"  Altitude: {vehicle_altitude_m}m")
    if 'range' in data:
        global vehicle_range_km
        vehicle_range_km = int(data['range'] * 1.60934)
        log(f"  Range: {vehicle_range_km}km")
    if 'shift_state' in data:
        global vehicle_shift_state
        vehicle_shift_state = data['shift_state']
        log(f"  Shift state: {vehicle_shift_state}")

def send_aprs_location_report(callsign, msg, state):
    global vehicle_last_seen_ts
    global vehicle_lat
    global vehicle_lng
    global vehicle_speed_kmh
    global vehicle_heading
    global vehicle_altitude_m

    callsign_without_ssid = callsign.split("-")[0]
    aprs_lat = convert_coord_to_aprs(vehicle_lat, True)
    aprs_lng = convert_coord_to_aprs(vehicle_lng, False)
    lat_hemisphere = 'N' if vehicle_lat >= 0 else 'S'
    lng_hemisphere = 'E' if vehicle_lng >= 0 else 'W'
    aprs_speed = int(vehicle_speed_kmh * 0.539957) # Km/h to knots
    aprs_course = vehicle_heading
    day, hours, minutes = convert_unix_timestamp_to_aprs(vehicle_last_seen_ts)
    altitude_feet = int(vehicle_altitude_m * 3.28084)

    log(f"Sending location report...")

    try:
        aprs_conn = aprslib.IS(callsign_without_ssid, get_aprs_passcode_for_callsign(callsign_without_ssid))
        aprs_conn.connect()
        pkt = f"{callsign}>APRS,TCPIP*:@{day}{hours}{minutes}z{aprs_lat}{lat_hemisphere}/{aprs_lng}{lng_hemisphere}>{aprs_course:03d}/{aprs_speed:03d}{msg}/A={altitude_feet:06d}"
        log(f"  {pkt}")
        aprs_conn.sendall(pkt)
        pkt = f"{callsign}>APRS,TCPIP*:>{day}{hours}{minutes}z{state}"
        log(f"  {pkt}")
        aprs_conn.sendall(pkt)
    except Exception as e:
        print(f"Error sending APRS message: {e}")
        sys.exit(1)

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

def update(tesla, vehicle_nr, callsign, msg):
    global last_report_ts
    global vehicle_last_seen_ts

    if vehicle_last_seen_ts == last_report_ts:
        if vehicle_last_seen_ts:
            log("Last update same as last report, skipping")
        return

    last_report_ts = vehicle_last_seen_ts

    global vehicle_charge_percent
    global vehicle_range_km
    global vehicle_shift_state

    vehicle = tesla_get_vehicle(tesla, vehicle_nr)
    if vehicle.available():
        log("Vehicle awake, querying data...")
        climate_state = vehicle['climate_state']
        if climate_state:
            state = str(climate_state['outside_temp']) + "C "

        charge_state = vehicle['charge_state']
        if charge_state:
            charger_pwr_kw = charge_state['charger_power']
            charger_rem_mins = charge_state['minutes_to_full_charge']

    state += f"Batt. {vehicle_charge_percent}% ({vehicle_range_km}km)"
    if charger_pwr_kw:
        charger_pwr_str = str(charger_pwr_kw) + "kW"
        log(f"  Charger pwr: {charger_pwr_str}")

        if charger_rem_mins:
            hours, mins = get_hours_and_mins_from_mins(charger_rem_mins)
            charger_rem_str = f"{hours}h{mins}m"
            log(f"  Charge rem.: {charger_rem_str}")
            state += f" (Charging {charger_pwr_str}/{charger_rem_str})"
        else:
            state += f" (On charger {charger_pwr_str})"
    elif not vehicle_shift_state:
        log("  Parked")
        state += " (Parked)"

    send_aprs_location_report(callsign, msg, state)

def main(argv):
    email = None
    callsign = None
    msg = ""
    interval_sec = 30
    vehicle_nr = 0

    try:
        opts, _ = getopt.getopt(argv, "e:c:m:si:n:", ["email=", "callsign=", "msg=", "silent=", "interval=", "vehiclenr="])
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
            global silent
            silent = True
        elif opt in ("-i", "--interval"):
            interval_sec = int(arg)
        elif opt in ("-n", "--vehiclenr"):
            vehicle_nr = int(arg)

    if not email or not callsign:
        print_usage()
        sys.exit(1)

    signal.signal(signal.SIGINT, sigint_handler)

    tesla = teslapy.Tesla(email)
    if not tesla.authorized:
        tesla.refresh_token(refresh_token=input('Enter Tesla refresh token (see README for details): '))

    msg_queue = multiprocessing.Queue()
    global tesla_stream_proc
    tesla_stream_proc = multiprocessing.Process(target=tesla_stream_thread_handler, args=(tesla, vehicle_nr, msg_queue)).start()

    while True:
        while not msg_queue.empty():
            tesla_stream_process_data(msg_queue.get())

        update(tesla, vehicle_nr, callsign, msg)
        log(f"Sleeping for {interval_sec} seconds...")
        time.sleep(interval_sec)

if __name__ == "__main__":
    main(sys.argv[1:])
