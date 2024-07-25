from helper import *
from log import *

import aprslib

aprs_conn = None

def aprs_disconnect():
    global aprs_conn
    if aprs_conn:
        aprs_conn.close()
        aprs_conn = None

def aprs_connect_if_needed(callsign):
    global aprs_conn
    if not aprs_conn:
        try:
            log("Connecting to APRS-IS...")
            aprs_conn = aprslib.IS(callsign, get_aprs_passcode_for_callsign(callsign))
            aprs_conn.connect()
        except Exception as e:
            log(f"  Error connecting: {e}")
            aprs_disconnect()
            pass

    return aprs_conn != None

def aprs_send_pkt(pkt):
    log(f"  Sending to APRS-IS: {pkt}")
    global aprs_conn
    aprs_conn.sendall(pkt)

def aprs_send_location_report(callsign, ts, lat, lng, speed_kmh, heading, altitude_m, msg, state):
    callsign_without_ssid = callsign.split("-")[0]
    aprs_lat = convert_coord_to_aprs(lat, True)
    aprs_lng = convert_coord_to_aprs(lng, False)
    lat_hemisphere = 'N' if lat >= 0 else 'S'
    lng_hemisphere = 'E' if lng >= 0 else 'W'
    aprs_speed = int(speed_kmh * 0.539957) # Km/h to knots
    aprs_course = heading
    day, hours, minutes, seconds = convert_unix_timestamp_to_aprs(ts)

    log(f"Sending location report...")

    pkt1 = f"{callsign}>APTSLA,TCPIP*:@{hours}{minutes}{seconds}h{aprs_lat}{lat_hemisphere}/{aprs_lng}{lng_hemisphere}>{aprs_course:03d}/{aprs_speed:03d}{msg}"
    if altitude_m != None:
        altitude_feet = int(altitude_m * 3.28084)
        pkt1 += f"/A={altitude_feet:06d}"
    pkt2 = f"{callsign}>APTSLA,TCPIP*:>{day}{hours}{minutes}z{state}"

    try_count = 0
    while try_count < 3:
        try:
            if aprs_connect_if_needed(callsign_without_ssid):
                aprs_send_pkt(pkt1)
                aprs_send_pkt(pkt2)
            log("Location report sent")
            return
        except Exception as e:
            log(f"  Error sending: {e}")
            aprs_disconnect()
            pass
        try_count += 1
