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
    print("  -r, --enable-streaming\tEnable streaming updates")
    print("  -t, --aprs-symbol-table\tAPRS symbol table character, default /")
    print("  -o, --aprs-symbol-code\tAPRS symbol code character, default >")

def main(argv):
    email = os.environ.get('TESLAAPRS_EMAIL')
    refresh_token = os.environ.get('TESLAAPRS_REFRESH_TOKEN')
    callsign = os.environ.get('TESLAAPRS_CALLSIGN')
    msg = os.environ.get('TESLAAPRS_MSG')
    if os.environ.get('TESLAAPRS_SILENT'):
        log_set_silent(True)
    interval_sec = os.environ.get('TESLAAPRS_INTERVAL')
    vehicle_nr = os.environ.get('TESLAAPRS_VEHICLE_NR')
    wakeup_on_start = False
    enable_streaming_updates = False
    aprs_symbol_table_char = os.environ.get('TESLAAPRS_APRS_SYMBOL_TABLE_CHAR')
    aprs_symbol_code_char = os.environ.get('TESLAAPRS_APRS_SYMBOL_CODE_CHAR')

    try:
        opts, _ = getopt.getopt(argv, "e:c:m:si:n:wdrt:o:", ["email=", "callsign=", "msg=", "silent=", "interval=", "vehiclenr=", "wakeup=", "debug=",
                                                             "enablestreaming=", "aprssymboltable=", "aprssymbolcode="])
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
        elif opt in ("-r", "--enable-streaming"):
            enable_streaming_updates = True
        elif opt in ("-t", "--aprs-symbol-table"):
            aprs_symbol_table_char = arg
        elif opt in ("-o", "--aprs-symbol-code"):
            aprs_symbol_code_char = arg

    if not email or not callsign:
        print_usage()
        exit(1)

    signal.signal(signal.SIGINT, sigint_handler)

    process(email, refresh_token, vehicle_nr, wakeup_on_start, enable_streaming_updates, interval_sec, callsign, aprs_symbol_table_char, aprs_symbol_code_char, msg)

if __name__ == "__main__":
    main(sys.argv[1:])
