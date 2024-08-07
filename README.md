# Tesla APRS

Sends Tesla vehicle location and status to the APRS-IS.

## Installation

Note that you can also get this app as a [Home Assistant addon](https://github.com/nonoo/ha-addons).

### Create a Python virtual environment

```
python -m venv env
```

### Activate the virtual environment

On Linux/MacOS:

```
source env/bin/activate
```

On Windows:

```
.\env\Scripts\activate
```

### Install requirements

```
pip install -r requirements.txt
```

## Tesla refresh token

The script asks for a Tesla refresh token when run for the first time.
You will need an application to generate a refresh token:

- Android: [Tesla Tokens](https://play.google.com/store/apps/details?id=net.leveugle.teslatokens)
- iOS: [Auth App for Tesla](https://apps.apple.com/us/app/auth-app-for-tesla/id1552058613)
- Chromium/Edge: [Chromium Tesla Token Generator](https://github.com/DoctorMcKay/chromium-tesla-token-generator)

Login session data is stored into the file `cache.json`, so you don't need to
enter the refresh token every time the script runs. Make sure the current
working directory is set to the script's directory, so `cache.json` can be
found by the script.

## Running

You don't need to activate the virtual environment to run the script.
Use `env/bin/python` instead of the system Python binary.

Get the command line arguments using `-h`

Example usage:

```
env/bin/python main.py -e nonoo@nonoo.hu -c HA2NON-12 -m "LOAD\"*\",8,1 ~ github.com/nonoo/tesla-aprs"
```

## Environment variables

You can set the following environment variables to avoid passing them as
command line arguments:

- `TESLAAPRS_EMAIL`: Tesla account email address
- `TESLAAPRS_CALLSIGN`: APRS callsign
- `TESLAAPRS_MSG`: APRS message
- `TESLAAPRS_SILENT`: Suppress logging
- `TESLAAPRS_INTERVAL`: APRS message interval in seconds
- `TESLAAPRS_VEHICLE_NR`: Tesla vehicle number
- `TESLAAPRS_REFRESH_TOKEN`: Tesla refresh token
