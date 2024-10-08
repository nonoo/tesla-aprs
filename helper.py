from tesla import *

import datetime
from datetime import datetime, timezone
import sys

def exit(code):
    tesla_stream_process_stop()
    sys.exit(code)

def convert_unix_timestamp_to_hours_mins(utc_timestamp):
    dt = datetime.fromtimestamp(utc_timestamp)
    hours = str(dt.hour).zfill(2)
    minutes = str(dt.minute).zfill(2)
    return hours, minutes

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
    seconds = str(dt.second).zfill(2)
    return day, hours, minutes, seconds

def format_float_str(str):
    if '.' in str:
        whole_part, decimal_part = str.split('.')
        if decimal_part == '0' * len(decimal_part):
            return whole_part
    return str
