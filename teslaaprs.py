from helper import *
from aprs import *
from log import *
from tesla import *

import time
import multiprocessing

def update(callsign, aprs_symbol_table_char, aprs_symbol_code_char, msg):
    vehicle_last_seen_ts, vehicle_charge_percent, vehicle_lat, vehicle_lng, vehicle_speed_kmh, vehicle_heading, \
        vehicle_altitude_m, vehicle_range_km, vehicle_shift_state, ts_state, outside_temp_str, charger_pwr_kw, charger_fin_str = tesla_get_data()

    if not vehicle_last_seen_ts:
        return

    state = f"Batt. {vehicle_charge_percent}% {vehicle_range_km}km"

    if outside_temp_str:
        state += " " + outside_temp_str + "C"

    if charger_pwr_kw:
        charger_pwr_str = str(charger_pwr_kw) + "kW"
        state += f" (Chg {charger_pwr_str}"

        if charger_fin_str:
            state += f" {charger_fin_str}"

        state += ")"
    elif not vehicle_shift_state or vehicle_shift_state == "P":
        state += " (Parked)"

    aprs_send_location_report(callsign, aprs_symbol_table_char, aprs_symbol_code_char, vehicle_last_seen_ts, vehicle_lat, vehicle_lng,
                              vehicle_speed_kmh, vehicle_heading, vehicle_altitude_m, msg, ts_state, state)

def process(email, refresh_token, vehicle_nr, wakeup_on_start, enable_streaming_updates, interval_sec, callsign,
            aprs_symbol_table_char, aprs_symbol_code_char, msg):
    if email:
        email = email.strip()
    if callsign:
        callsign = callsign.strip().upper()
    if msg:
        msg = msg.strip()
    else:
        msg = "github.com/nonoo/tesla-aprs"
    if interval_sec:
        interval_sec = int(interval_sec)
    else:
        interval_sec = 15
    if vehicle_nr:
        vehicle_nr = int(vehicle_nr)
    else:
        vehicle_nr = 0

    if aprs_symbol_table_char:
        aprs_symbol_table_char.strip()
        if aprs_symbol_table_char:
            aprs_symbol_table_char = aprs_symbol_table_char[0]
    if not aprs_symbol_table_char:
        aprs_symbol_table_char = "/"

    if aprs_symbol_code_char:
        aprs_symbol_code_char.strip()
        if aprs_symbol_code_char:
            aprs_symbol_code_char = aprs_symbol_code_char[0]
    if not aprs_symbol_code_char:
        aprs_symbol_code_char = ">"

    tesla = tesla_init(email, refresh_token)

    msg_queue = multiprocessing.Queue()

    if enable_streaming_updates:
        tesla_stream_process_start(email, refresh_token, vehicle_nr, msg_queue)

    if wakeup_on_start:
        try:
            tesla_wakeup(tesla, vehicle_nr)
        except Exception as e:
            print(f"Wakeup failed: {e}")
            exit(1)

    log(f"Sleeping for {interval_sec} seconds...")
    sec_to_sleep = interval_sec
    last_update_at = int(time.time())

    while True:
        while not msg_queue.empty():
            msg_from_queue = msg_queue.get()
            if not msg_from_queue:
                print("Tesla update stream error, exiting")
                exit(1)
            tesla_stream_process_data(msg_from_queue)
            last_update_at = int(time.time())

        while sec_to_sleep > 0:
            time.sleep(1)
            sec_to_sleep -= 1

            tesla_update_force_if_needed(tesla, vehicle_nr, interval_sec)

            if sec_to_sleep == 0:
                update(callsign, aprs_symbol_table_char, aprs_symbol_code_char, msg)
                log(f"Sleeping for {interval_sec} seconds...")
                sec_to_sleep = interval_sec

            if not msg_queue.empty():
                break

            if enable_streaming_updates and int(time.time()) - last_update_at > TESLA_STREAM_UPDATE_TIMEOUT_SEC:
                log("Tesla update stream timeout, restarting...")
                tesla_stream_process_stop()
                tesla_stream_process_start(email, refresh_token, vehicle_nr, msg_queue)
                last_update_at = int(time.time())
