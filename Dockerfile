FROM python:3.12-alpine

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD [ "python", "teslaaprs.py" ]

ENV TESLAAPRS_EMAIL= TESLAAPRS_CALLSIGN= TESLAAPRS_MSG= TESLAAPRS_SILENT= TESLAAPRS_INTERVAL= TESLAAPRS_VEHICLE_NR= TESLAAPRS_REFRESH_TOKEN=
