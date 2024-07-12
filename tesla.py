from log import *

import sys

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
