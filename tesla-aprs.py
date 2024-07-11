import teslapy
import sys
import getopt
import sys
import os
import aprslib
import datetime
from datetime import datetime, timezone

silent = False

def get_tesla_data(email):
    global silent
    if not silent:
        print("Querying Tesla API...")

    with teslapy.Tesla(email) as tesla:
        if not tesla.authorized:
            tesla.refresh_token(refresh_token=input('Enter SSO refresh token: '))
        vehicles = tesla.vehicle_list()
        if not vehicles:
            print("No registered cars")
            return None
        vehicle = vehicles[0]
        return vehicle['drive_state'], vehicle['charge_state']

def get_aprs_passcode_for_callsign(callsign):
    hash = 0x73e2
    callsign = callsign[:10]

    for i in range(0, len(callsign), 2):
        hash ^= ord(callsign[i]) << 8
        if i+1 < len(callsign):
            hash ^= ord(callsign[i + 1])
        hash &= 0xFFFF

    return hash

def convert_coord_to_aprs(degrees, is_latitude):
    degrees = abs(degrees)
    degree_whole = int(degrees)
    degree_fraction = degrees - degree_whole
    minutes = degree_fraction * 60
    if is_latitude:
        return f"{degree_whole:02d}{minutes:05.2f}"
    else:
        return f"{degree_whole:03d}{minutes:05.2f}"

def convert_unix_timestamp_to_aprs(utc_timestamp):
    dt = datetime.fromtimestamp(utc_timestamp, tz=timezone.utc)
    day = str(dt.day).zfill(2)
    hours = str(dt.hour).zfill(2)
    minutes = str(dt.minute).zfill(2)
    return day, hours, minutes

def send_aprs_location_report(callsign, ts, latitude, longitude, speed, course, msg, state):
    callsign_without_ssid = callsign.split("-")[0]
    aprs_lat = convert_coord_to_aprs(latitude, True)
    aprs_lng = convert_coord_to_aprs(longitude, False)
    lat_hemisphere = 'N' if latitude >= 0 else 'S'
    lng_hemisphere = 'E' if longitude >= 0 else 'W'
    aprs_speed = int(speed * 0.539957) # Km/h to knots
    aprs_course = int(course)
    day, hours, minutes = convert_unix_timestamp_to_aprs(ts)

    global silent
    if not silent:
        print(f"Sending location report for {callsign_without_ssid} to APRS as {callsign}...")

    try:
        aprs_conn = aprslib.IS(callsign_without_ssid, get_aprs_passcode_for_callsign(callsign_without_ssid))
        aprs_conn.connect()
        aprs_conn.sendall(f"{callsign}>APRS,TCPIP*:@{day}{hours}{minutes}z{aprs_lat}{lat_hemisphere}/{aprs_lng}{lng_hemisphere}>{aprs_course:03d}/{aprs_speed:03d}{msg}")
        aprs_conn.sendall(f"{callsign}>APRS,TCPIP*:>{day}{hours}{minutes}z{state}")
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

def main(argv):
    email = None
    callsign = None
    msg = ""
    global silent

    try:
        opts, _ = getopt.getopt(argv, "e:c:m:s", ["email=", "callsign=", "msg=", "silent="])
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
            silent = True

    if not email or not callsign:
        print_usage()
        sys.exit(1)

    drive_state, charge_state = get_tesla_data(email)
    if not drive_state or not charge_state:
        print("Can't get vehicle data, exiting")
        sys.exit(1)

    range_miles = charge_state['battery_range']
    range_km = str(int(range_miles * 1.60934)) + "km"
    chg_pwr = str(charge_state['charger_power']) + "W"

    if not silent:
        print(f"  Timestamp: {drive_state['gps_as_of']}")
        print(f"  Latitude: {drive_state['latitude']}")
        print(f"  Longitude: {drive_state['longitude']}")
        print(f"  Speed: {drive_state['speed']}")
        print(f"  Heading: {drive_state['heading']}")
        print(f"  Shift state: {drive_state['shift_state']}")
        print(f"  Battery level: {charge_state['battery_level']}%")
        print(f"  Est. range: {range_km}")
        print(f"  Charger power: {chg_pwr}")

    speed = drive_state['speed']
    if not speed:
        speed = 0

    state = f"Battery {charge_state['battery_level']}% Est. range: {range_km}"
    if charge_state['charger_power']:
        state += f" (Charging {chg_pwr})"
    elif not drive_state['shift_state']:
        state += " (Parked)"

    send_aprs_location_report(callsign, drive_state['gps_as_of'], drive_state['latitude'], drive_state['longitude'], speed, drive_state['heading'], msg, state)

if __name__ == "__main__":
    main(sys.argv[1:])
