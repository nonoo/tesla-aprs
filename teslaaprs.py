from helper import *
from aprs import *
from log import *
from tesla import *

import time
import multiprocessing

last_report_ts = None

def update(callsign, msg):
    vehicle_last_seen_ts, vehicle_charge_percent, vehicle_lat, vehicle_lng, vehicle_speed_kmh, vehicle_heading, \
        vehicle_altitude_m, vehicle_range_km, vehicle_shift_state, outside_temp_str, charger_pwr_kw, charger_rem_str = tesla_get_data()

    global last_report_ts
    if vehicle_last_seen_ts == last_report_ts:
        if vehicle_last_seen_ts:
            log("Last update timestamp same as last report, skipping")
        return

    last_report_ts = vehicle_last_seen_ts

    state = f"Batt. {vehicle_charge_percent}% {vehicle_range_km}km"

    if outside_temp_str:
        state += " " + outside_temp_str + "C"

    if charger_pwr_kw:
        charger_pwr_str = str(charger_pwr_kw) + "kW"
        state += f" (Chg {charger_pwr_str}"

        if charger_rem_str:
            state += f"/{charger_rem_str}"

        state += ")"
    elif not vehicle_shift_state or vehicle_shift_state == "P":
        log("  Parked")
        state += " (Parked)"

    aprs_send_location_report(callsign, vehicle_last_seen_ts, vehicle_lat, vehicle_lng, vehicle_speed_kmh,
                              vehicle_heading, vehicle_altitude_m, msg, state)

def process(email, vehicle_nr, wakeup_on_start, force_update_only, interval_sec, callsign, msg):
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

    tesla = tesla_init(email)

    msg_queue = multiprocessing.Queue()

    if not force_update_only:
        tesla_stream_process_start(email, vehicle_nr, msg_queue)

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
                update(tesla, vehicle_nr, callsign, msg)
                log(f"Sleeping for {interval_sec} seconds...")
                sec_to_sleep = interval_sec

            if not msg_queue.empty():
                break

            if not force_update_only and int(time.time()) - last_update_at > tesla_stream_update_timeout_sec:
                log("Tesla update stream timeout, restarting...")
                tesla_stream_process_stop()
                tesla_stream_process_start(email, vehicle_nr, msg_queue)
                last_update_at = int(time.time())
