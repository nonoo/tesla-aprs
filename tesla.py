from log import *

import helper

import multiprocessing
import teslapy
import os
import time

tesla_mutex = multiprocessing.Lock()

tesla_stream_update_timeout_sec = 30
tesla_stream_reconnect_retry_interval_sec = 10
tesla_stream_process_handle = None
tesla_last_stream_update_at = None
tesla_last_forced_update_try_at = None
tesla_last_forced_additional_update_try_at = None

tesla_vehicles_cached = None

tesla_vehicle_last_seen_ts = None
tesla_vehicle_charge_percent = None
tesla_vehicle_lat = None
tesla_vehicle_lng = None
tesla_vehicle_speed_kmh = None
tesla_vehicle_heading = None
tesla_vehicle_altitude_m = None
tesla_vehicle_range_km = None
tesla_vehicle_shift_state = None

tesla_vehicle_additional_ts = None
tesla_vehicle_additional_outside_temp_str = None
tesla_vehicle_additional_charger_pwr_kw = None
tesla_vehicle_additional_charger_rem_str = None

def tesla_get_data():
    with tesla_mutex:
	    return tesla_vehicle_last_seen_ts, tesla_vehicle_charge_percent, tesla_vehicle_lat, tesla_vehicle_lng, tesla_vehicle_speed_kmh, \
            tesla_vehicle_heading, tesla_vehicle_altitude_m, tesla_vehicle_range_km, tesla_vehicle_shift_state, tesla_vehicle_additional_ts, \
            tesla_vehicle_additional_outside_temp_str, tesla_vehicle_additional_charger_pwr_kw, tesla_vehicle_additional_charger_rem_str

def tesla_init(email):
    tesla = teslapy.Tesla(email)
    if not tesla.authorized:
        refresh_token = os.environ.get('TESLAAPRS_REFRESH_TOKEN')
        if not refresh_token:
            refresh_token = input('Enter Tesla refresh token (see README for details): ')
        tesla.refresh_token(refresh_token=refresh_token)
    return tesla

def tesla_get_vehicle(tesla, vehicle_nr):
    global tesla_vehicles_cached
    while not tesla_vehicles_cached:
        try:
            tesla_vehicles_cached = tesla.vehicle_list()
        except Exception as e:
            log(f"Vehicle list error: {e}, retrying...")
            tesla_vehicles_cached = None
            time.sleep(5)
            pass

    if not tesla_vehicles_cached:
        print("No registered vehicles")
        exit(1)

    if vehicle_nr >= len(tesla_vehicles_cached):
        print("Invalid vehicle number")
        exit(1)

    return tesla_vehicles_cached[vehicle_nr]

def tesla_stream_cb(data):
    global stream_msg_queue
    stream_msg_queue.put(data)

def tesla_stream_process(email, vehicle_nr, msg_queue):
    log("Stream process started")

    global stream_msg_queue
    stream_msg_queue = msg_queue

    tesla = teslapy.Tesla(email)
    if not tesla.authorized:
        refresh_token = os.environ.get('TESLAAPRS_REFRESH_TOKEN')
        if not refresh_token:
            print("No refresh token provided")
            stream_msg_queue.put(None)
            return
        tesla.refresh_token(refresh_token=refresh_token)

    vehicle = tesla_get_vehicle(tesla, vehicle_nr)
    while True:
        log("Stream connecting...")
        last_connect_ts = int(time.time())
        try:
            vehicle.stream(tesla_stream_cb) # This call blocks
        except Exception as e:
            log(f"Stream error: {e}")
            pass

        remaining_sec_until_retry = tesla_stream_reconnect_retry_interval_sec - (int(time.time()) - last_connect_ts)
        if remaining_sec_until_retry > 0:
            log(f"Stream disconnected, retrying in {remaining_sec_until_retry} seconds...")
            time.sleep(remaining_sec_until_retry)

def tesla_stream_process_start(email, vehicle_nr, msg_queue):
    log("Stream process starting")
    global tesla_stream_process_handle
    if tesla_stream_process_handle:
        log("Stream process already running")
        return
    tesla_stream_process_handle = multiprocessing.Process(target=tesla_stream_process, args=(email, vehicle_nr, msg_queue))
    tesla_stream_process_handle.daemon = True
    tesla_stream_process_handle.start()

def tesla_stream_process_stop():
    global tesla_stream_process_handle
    if tesla_stream_process_handle:
        log("Stream process stopping")
        tesla_stream_process_handle.terminate()
        tesla_stream_process_handle.join()
        tesla_stream_process_handle = None

def tesla_stream_process_data(data):
    with tesla_mutex:
        global tesla_last_stream_update_at
        tesla_last_stream_update_at = int(time.time())

        log("Stream update received:")
        if 'timestamp' in data:
            global tesla_vehicle_last_seen_ts
            tesla_vehicle_last_seen_ts = int(data['timestamp'] / 1000) # Convert ms to s
            log(f"  Timestamp: {tesla_vehicle_last_seen_ts}")
        if 'soc' in data:
            global tesla_vehicle_charge_percent
            tesla_vehicle_charge_percent = data['soc']
            log(f"  Charge percent: {tesla_vehicle_charge_percent}%")
        if 'est_lat' in data:
            global tesla_vehicle_lat
            tesla_vehicle_lat = data['est_lat']
            log(f"  Latitude: {tesla_vehicle_lat}")
        if 'est_lng' in data:
            global tesla_vehicle_lng
            tesla_vehicle_lng = data['est_lng']
            log(f"  Longitude: {tesla_vehicle_lng}")
        if 'speed' in data:
            global tesla_vehicle_speed_kmh
            tesla_vehicle_speed_kmh = data['speed']
            if not tesla_vehicle_speed_kmh:
                tesla_vehicle_speed_kmh = 0
            else:
                tesla_vehicle_speed_kmh = int(tesla_vehicle_speed_kmh * 1.60934) # Convert mph to kmh
            log(f"  Speed: {tesla_vehicle_speed_kmh}km/h")
        if 'est_heading' in data:
            global tesla_vehicle_heading
            tesla_vehicle_heading = data['est_heading']
            log(f"  Heading: {tesla_vehicle_heading}")
        if 'elevation' in data:
            global tesla_vehicle_altitude_m
            tesla_vehicle_altitude_m = data['elevation']
            log(f"  Altitude: {tesla_vehicle_altitude_m}m")
        if 'range' in data:
            global tesla_vehicle_range_km
            tesla_vehicle_range_km = int(data['range'] * 1.60934) # Convert miles to km
            log(f"  Range: {tesla_vehicle_range_km}km")
        if 'shift_state' in data:
            global tesla_vehicle_shift_state
            tesla_vehicle_shift_state = data['shift_state']
            log(f"  Shift state: {tesla_vehicle_shift_state}")

def tesla_update_force(vehicle):
    result = True
    log("Forced update...")
    try:
        with tesla_mutex:
            global tesla_last_forced_update_try_at
            tesla_last_forced_update_try_at = int(time.time())

            global tesla_vehicle_altitude_m
            tesla_vehicle_altitude_m = None # Elevation data is only provided in the stream update.

            log("Forced update results:")
            vehicle_state = vehicle['vehicle_state']
            log(f"  Vehicle name: {vehicle_state['vehicle_name']}")

            if vehicle['mobile_access_disabled']:
                log("WARNING: Mobile access disabled")

            drive_state = vehicle['drive_state']
            global tesla_vehicle_last_seen_ts
            tesla_vehicle_last_seen_ts = drive_state['gps_as_of']
            log(f"  Timestamp: {tesla_vehicle_last_seen_ts}")

            global tesla_vehicle_charge_percent
            charge_state = vehicle['charge_state']
            tesla_vehicle_charge_percent = charge_state['battery_level']
            log(f"  Charge percent: {tesla_vehicle_charge_percent}%")

            global tesla_vehicle_lat
            tesla_vehicle_lat = drive_state['latitude']
            log(f"  Latitude: {tesla_vehicle_lat}")

            global tesla_vehicle_lng
            tesla_vehicle_lng = drive_state['longitude']
            log(f"  Longitude: {tesla_vehicle_lng}")

            global tesla_vehicle_speed_kmh
            tesla_vehicle_speed_kmh = drive_state['speed']
            if not tesla_vehicle_speed_kmh:
                tesla_vehicle_speed_kmh = 0
            else:
                tesla_vehicle_speed_kmh = int(tesla_vehicle_speed_kmh * 1.60934) # Convert mph to kmh
            log(f"  Speed: {tesla_vehicle_speed_kmh}km/h")

            global tesla_vehicle_heading
            tesla_vehicle_heading = drive_state['heading']
            log(f"  Heading: {tesla_vehicle_heading}")

            global tesla_vehicle_range_km
            tesla_vehicle_range_km = int(charge_state['battery_range'] * 1.60934) # Convert miles to km
            log(f"  Range: {tesla_vehicle_range_km}km")

            global tesla_vehicle_shift_state
            tesla_vehicle_shift_state = drive_state['shift_state']
            log(f"  Shift state: {tesla_vehicle_shift_state}")
    except Exception as e:
        log(f"Forced update failed: {e}")
        result = False
        pass

    return result

def tesla_update_force_additional(vehicle):
    log("Forced additional data update...")
    try:
        with tesla_mutex:
            global tesla_last_forced_additional_update_try_at
            tesla_last_forced_additional_update_try_at = int(time.time())

            climate_state = vehicle['climate_state']
            if climate_state:
                global tesla_vehicle_additional_outside_temp_str
                tesla_vehicle_additional_outside_temp_str = helper.format_float_str(str(climate_state['outside_temp']))
                log(f"  Outside temp: {tesla_vehicle_additional_outside_temp_str}C")
            else:
                tesla_vehicle_additional_outside_temp_str = None
                log("  Outside temp: N/A")

            charge_state = vehicle['charge_state']
            if charge_state:
                global tesla_vehicle_additional_charger_pwr_kw
                tesla_vehicle_additional_charger_pwr_kw = charge_state['charger_power']
                charger_pwr_str = str(tesla_vehicle_additional_charger_pwr_kw) + "kW"
                log(f"  Charger pwr: {charger_pwr_str}")

                global tesla_vehicle_additional_charger_rem_str
                hours, mins = helper.get_hours_and_mins_from_mins(charge_state['minutes_to_full_charge'])
                tesla_vehicle_additional_charger_rem_str = f"{mins}m"
                if hours > 0 and mins > 0:
                    tesla_vehicle_additional_charger_rem_str = f"{hours}h{mins}m"
                elif hours > 0:
                    tesla_vehicle_additional_charger_rem_str = f"{hours}h"
                log(f"  Charge rem.: {tesla_vehicle_additional_charger_rem_str}")
            else:
                tesla_vehicle_additional_charger_pwr_kw = None
                tesla_vehicle_additional_charger_rem_str = None
                log("  Not charging")

            global tesla_vehicle_additional_ts
            tesla_vehicle_additional_ts = int(time.time())
    except Exception as e:
        log(f"Forced additional data update failed: {e}")
        pass

def tesla_update_force_needed(interval_sec):
    with tesla_mutex:
        min_update_interval_sec = interval_sec
        if not tesla_vehicle_shift_state or tesla_vehicle_shift_state == "P": # Vehicle parked? Update less frequently to let it sleep.
            min_update_interval_sec = max(min_update_interval_sec, 60)

        global tesla_last_forced_update_try_at
        if tesla_last_forced_update_try_at and int(time.time()) - tesla_last_forced_update_try_at < min_update_interval_sec:
            return False

        # Not doing a forced update if we got a stream update recently.
        if tesla_last_stream_update_at and int(time.time()) - tesla_last_stream_update_at < min_update_interval_sec:
            return False
    return True

def tesla_update_force_additional_needed(interval_sec):
    with tesla_mutex:
        global tesla_last_forced_additional_update_try_at
        if not tesla_last_forced_additional_update_try_at or int(time.time()) - tesla_last_forced_additional_update_try_at >= max(interval_sec, 60):
            return True
    return False

def tesla_update_force_if_needed(tesla, vehicle_nr, interval_sec):
    update_needed = tesla_update_force_needed(interval_sec)
    update_additional_needed = tesla_update_force_additional_needed(interval_sec)

    if not update_needed and not update_additional_needed:
        return

    vehicle = tesla_get_vehicle(tesla, vehicle_nr)
    try:
        awake = vehicle.available(max_age=0)
    except Exception as e:
        log(f"Vehicle availability check failed: {e}")
        return

    if awake:
        log(f"Vehicle awake, forcing update")
        if update_needed:
            tesla_update_force(vehicle)
        if update_additional_needed:
            tesla_update_force_additional(vehicle)
    else:
        log("Vehicle sleeping")
        global tesla_last_forced_update_try_at
        tesla_last_forced_update_try_at = int(time.time())
        global tesla_last_forced_additional_update_try_at
        tesla_last_forced_additional_update_try_at = int(time.time())

def tesla_wakeup(tesla, vehicle_nr):
    log("Waking up vehicle...")
    vehicle = tesla_get_vehicle(tesla, vehicle_nr)
    vehicle.sync_wake_up()
