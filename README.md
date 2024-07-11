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

Get the command line arguments using `-h`

Example position upload:

```
python tesla-aprs.py -e nonoo@nonoo.hu -c HA2NON-12 -m "BEER 1 2 3"
```
