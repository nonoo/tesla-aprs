# tesla-aprs

## Installation

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

## Running

You don't need to activate the virtual environment to run the script.
Use `env/bin/python` instead of the system Python binary.

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

## Example

Get the command line arguments using `-h`

Example usage:

```
env/bin/python tesla-aprs.py -e nonoo@nonoo.hu -c HA2NON-12 -m "BEER 1 2 3"
```
