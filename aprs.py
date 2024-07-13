from helper import *
from log import *

import aprslib

def send_aprs_location_report(callsign, ts, lat, lng, speed_kmh, heading, altitude_m, msg, state):
    callsign_without_ssid = callsign.split("-")[0]
    aprs_lat = convert_coord_to_aprs(lat, True)
    aprs_lng = convert_coord_to_aprs(lng, False)
    lat_hemisphere = 'N' if lat >= 0 else 'S'
    lng_hemisphere = 'E' if lng >= 0 else 'W'
    aprs_speed = int(speed_kmh * 0.539957) # Km/h to knots
    aprs_course = heading
    day, hours, minutes = convert_unix_timestamp_to_aprs(ts)

    log(f"Sending location report...")

    try:
        aprs_conn = aprslib.IS(callsign_without_ssid, get_aprs_passcode_for_callsign(callsign_without_ssid))
        aprs_conn.connect()
        pkt = f"{callsign}>APTSLA,TCPIP*:@{day}{hours}{minutes}z{aprs_lat}{lat_hemisphere}/{aprs_lng}{lng_hemisphere}>{aprs_course:03d}/{aprs_speed:03d}{msg}"
        if altitude_m != None:
            altitude_feet = int(altitude_m * 3.28084)
            pkt += f"/A={altitude_feet:06d}"
        log(f"  {pkt}")
        aprs_conn.sendall(pkt)
        pkt = f"{callsign}>APTSLA,TCPIP*:>{day}{hours}{minutes}z{state}"
        log(f"  {pkt}")
        aprs_conn.sendall(pkt)
    except Exception as e:
        log(f"Error sending APRS message: {e}")
        pass
