from log import *
from helper import *

import multiprocessing
import teslapy
import os
import time

tesla_stream_process_handle = None

vehicle_last_seen_ts = None
vehicle_charge_percent = None
vehicle_lat = None
vehicle_lng = None
vehicle_speed_kmh = None
vehicle_heading = None
vehicle_altitude_m = None
vehicle_range_km = None
vehicle_shift_state = None

def tesla_get_data():
	return vehicle_last_seen_ts, vehicle_charge_percent, vehicle_lat, vehicle_lng, vehicle_speed_kmh, vehicle_heading, vehicle_altitude_m, vehicle_range_km, vehicle_shift_state

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
    log("Got Tesla update:")
    if 'timestamp' in data:
        global vehicle_last_seen_ts
        vehicle_last_seen_ts = int(data['timestamp'] / 1000) # Convert ms to s
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
        vehicle_speed_kmh = data['speed']
        if not vehicle_speed_kmh:
            vehicle_speed_kmh = 0
        else:
            vehicle_speed_kmh = int(vehicle_speed_kmh * 1.60934) # Convert mph to kmh
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
        vehicle_range_km = int(data['range'] * 1.60934) # Convert miles to km
        log(f"  Range: {vehicle_range_km}km")
    if 'shift_state' in data:
        global vehicle_shift_state
        vehicle_shift_state = data['shift_state']
        log(f"  Shift state: {vehicle_shift_state}")

def tesla_update_force(tesla, vehicle_nr):
    log("Forced Tesla update, waking up vehicle...")
    vehicle = tesla_get_vehicle(tesla, vehicle_nr)
    try:
        vehicle.sync_wake_up()

        log("Forced Tesla update results:")
        vehicle_state = vehicle['vehicle_state']
        log(f"  Vehicle name: {vehicle_state['vehicle_name']}")

        drive_state = vehicle['drive_state']
        global vehicle_last_seen_ts
        vehicle_last_seen_ts = drive_state['gps_as_of']
        log(f"  Timestamp: {vehicle_last_seen_ts}")

        global vehicle_charge_percent
        charge_state = vehicle['charge_state']
        vehicle_charge_percent = charge_state['battery_level']
        log(f"  Charge percent: {vehicle_charge_percent}%")

        global vehicle_lat
        vehicle_lat = drive_state['latitude']
        log(f"  Latitude: {vehicle_lat}")

        global vehicle_lng
        vehicle_lng = drive_state['longitude']
        log(f"  Longitude: {vehicle_lng}")

        global vehicle_speed_kmh
        vehicle_speed_kmh = drive_state['speed']
        if not vehicle_speed_kmh:
            vehicle_speed_kmh = 0
        else:
            vehicle_speed_kmh = int(vehicle_speed_kmh * 1.60934) # Convert mph to kmh
        log(f"  Speed: {vehicle_speed_kmh}km/h")

        global vehicle_heading
        vehicle_heading = drive_state['heading']
        log(f"  Heading: {vehicle_heading}")

        global vehicle_range_km
        vehicle_range_km = int(charge_state['battery_range'] * 1.60934) # Convert miles to km
        log(f"  Range: {vehicle_range_km}km")

        global vehicle_shift_state
        vehicle_shift_state = drive_state['shift_state']
        log(f"  Shift state: {vehicle_shift_state}")
    except Exception as e:
        print(e)
        exit(1)
