from log import *
from helper import *

import multiprocessing
import teslapy
import os
import time

tesla_mutex = multiprocessing.Lock()

tesla_stream_update_timeout_sec = 30
tesla_stream_process_handle = None
tesla_last_forced_update_try_at = None

tesla_vehicle_last_seen_ts = None
tesla_vehicle_charge_percent = None
tesla_vehicle_lat = None
tesla_vehicle_lng = None
tesla_vehicle_speed_kmh = None
tesla_vehicle_heading = None
tesla_vehicle_altitude_m = None
tesla_vehicle_range_km = None
tesla_vehicle_shift_state = None

def tesla_get_data():
    with tesla_mutex:
	    return tesla_vehicle_last_seen_ts, tesla_vehicle_charge_percent, tesla_vehicle_lat, tesla_vehicle_lng, tesla_vehicle_speed_kmh, \
            tesla_vehicle_heading, tesla_vehicle_altitude_m, tesla_vehicle_range_km, tesla_vehicle_shift_state

def tesla_init(email):
    tesla = teslapy.Tesla(email)
    if not tesla.authorized:
        refresh_token = os.environ.get('TESLAAPRS_REFRESH_TOKEN')
        if not refresh_token:
            refresh_token = input('Enter Tesla refresh token (see README for details): ')
        tesla.refresh_token(refresh_token=refresh_token)
    return tesla

def tesla_get_vehicle(tesla, vehicle_nr):
    vehicles = tesla.vehicle_list()
    if not vehicles:
        print("No registered vehicles")
        exit(1)

    if vehicle_nr >= len(vehicles):
        print("Invalid vehicle number")
        exit(1)

    return vehicles[vehicle_nr]

def tesla_stream_cb(data):
    global stream_msg_queue
    stream_msg_queue.put(data)

def tesla_stream_process(email, vehicle_nr, msg_queue):
    log("Started")

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
        log("Connecting...")
        last_connect_ts = int(time.time())
        try:
            vehicle.stream(tesla_stream_cb) # This call blocks
        except Exception as e:
            log(e)
            pass

        retry_interval_sec = 10
        remaining_sec_until_retry = retry_interval_sec - (int(time.time()) - last_connect_ts)
        if remaining_sec_until_retry > 0:
            log(f"Disconnected, retrying in {remaining_sec_until_retry} seconds...")
            time.sleep(remaining_sec_until_retry)

def tesla_stream_process_start(email, vehicle_nr, msg_queue):
    log("Starting")
    global tesla_stream_process_handle
    if tesla_stream_process_handle:
        log("Already running")
        return
    tesla_stream_process_handle = multiprocessing.Process(target=tesla_stream_process, args=(email, vehicle_nr, msg_queue))
    tesla_stream_process_handle.daemon = True
    tesla_stream_process_handle.start()

def tesla_stream_process_stop():
    global tesla_stream_process_handle
    if tesla_stream_process_handle:
        log("Stopping")
        tesla_stream_process_handle.terminate()
        tesla_stream_process_handle.join()
        tesla_stream_process_handle = None

def tesla_stream_process_data(data):
    with tesla_mutex:
        log("Got Tesla update:")
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

def tesla_update_force(tesla, vehicle_nr, wake_up):
    result = True
    log("Forced Tesla update...")
    vehicle = tesla_get_vehicle(tesla, vehicle_nr)
    try:
        if wake_up:
            log("  Waking up vehicle...")
            vehicle.sync_wake_up()

        with tesla_mutex:
            log("Forced Tesla update results:")
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
        log(f"Forced Tesla update failed: {e}")
        result = False
        pass

    return result

def tesla_update_force_if_needed(tesla, vehicle_nr, interval_sec):
    with tesla_mutex:
        min_update_interval_sec = interval_sec
        if not tesla_vehicle_shift_state: # Vehicle parked? Update less frequently to let it sleep.
            min_update_interval_sec = max(min_update_interval_sec, 60)

        global tesla_last_forced_update_try_at
        if tesla_last_forced_update_try_at and int(time.time()) - tesla_last_forced_update_try_at < min_update_interval_sec:
            return
        tesla_last_forced_update_try_at = int(time.time())

        # Not doing a forced update if we got a stream update recently.
        if tesla_vehicle_last_seen_ts and int(time.time()) - tesla_vehicle_last_seen_ts < interval_sec:
            return

    vehicle = tesla_get_vehicle(tesla, vehicle_nr)
    if vehicle.available(max_age=0):
        log(f"Vehicle awake, no data received for {min_update_interval_sec} seconds, forcing update")
        tesla_update_force(tesla, vehicle_nr, False)
    else:
        log("Vehicle sleeping")
