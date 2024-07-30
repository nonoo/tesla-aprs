from log import *
from teslaaprs import *

import sys
import getopt
import os
import signal
import logging

def sigint_handler(signum, frame):
    exit(0)

def print_usage():
    script_name = os.path.basename(__file__)
    print("tesla-aprs - Send Tesla vehicle location data to the APRS-IS https://github.com/nonoo/tesla-aprs")
    print(f"Usage: python {script_name} -e <email> -c <callsign> -m <msg>")
    print("Options:")
    print("  -e, --email\t\tEmail address for Tesla account")
    print("  -c, --callsign\tAPRS callsign")
    print("  -m, --msg\t\tAPRS message")
    print("  -s, --silent\t\tSuppress output")
    print("  -i, --interval\t\tInterval in seconds between updates, default 15")
    print("  -n, --vehiclenr\tVehicle number, default 0")
    print("  -f, --forceupdate\tForce update on start")
    print("  -d, --debug\t\tEnable debug output")

def main(argv):
    email = os.environ.get('TESLAAPRS_EMAIL')
    callsign = os.environ.get('TESLAAPRS_CALLSIGN')
    msg = os.environ.get('TESLAAPRS_MSG')
    if os.environ.get('TESLAAPRS_SILENT'):
        log_set_silent(True)
    interval_sec = os.environ.get('TESLAAPRS_INTERVAL')
    vehicle_nr = os.environ.get('TESLAAPRS_VEHICLE_NR')
    wakeup_on_start = False

    try:
        opts, _ = getopt.getopt(argv, "e:c:m:si:n:dw", ["email=", "callsign=", "msg=", "silent=", "interval=", "vehiclenr=", "wakeup=", "debug="])
    except getopt.GetoptError:
        print_usage()
        exit(1)

    for opt, arg in opts:
        if opt in ("-e", "--email"):
            email = arg
        elif opt in ("-c", "--callsign"):
            callsign = arg.upper()
        elif opt in ("-m", "--msg"):
            msg = arg
        elif opt in ("-s", "--silent"):
            log_set_silent(True)
        elif opt in ("-i", "--interval"):
            interval_sec = int(arg)
        elif opt in ("-n", "--vehiclenr"):
            vehicle_nr = int(arg)
        elif opt in ("-w", "--wakeup"):
            wakeup_on_start = True
        elif opt in ("-d", "--debug"):
            logging.basicConfig(level=logging.DEBUG)

    if not email or not callsign:
        print_usage()
        exit(1)

    signal.signal(signal.SIGINT, sigint_handler)

    process(email, vehicle_nr, wakeup_on_start, interval_sec, callsign, msg)

if __name__ == "__main__":
    main(sys.argv[1:])
