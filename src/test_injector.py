import json
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
import requests
from requests.auth import HTTPBasicAuth

# MQTT: official Lab 5 namespace
MQTT_TEAM = "XLR8"
BROKER = "194.177.207.38"
PORT = 1883
MQTT_USERNAME = "team1"
MQTT_PASSWORD = "team1!@#$"

TELEMETRY_TOPIC = f"iot/{MQTT_TEAM}/telemetry/soilMoisture"
COMMAND_TOPIC = f"iot/{MQTT_TEAM}/control/irrigation"

# Keep existing InfluxDB / Grafana structure
INFLUXDB_URL = "http://194.177.207.38:8086"
DB_NAME = "edge12_db"
DB_USERNAME = "edge12"
DB_PASSWORD = "team1@#$"
INFLUX_TEAM = "edge12"


def write_weather(temperature, rain_probability, rain_volume, actual_rain, mode):
    if mode == "day":
        sunrise = "2000-01-01T07:00"
        sunset = "2099-01-01T20:00"
    elif mode == "night":
        sunrise = "2099-01-01T07:00"
        sunset = "2100-01-01T20:00"
    else:
        today = datetime.now().strftime("%Y-%m-%d")
        sunrise = f"{today}T07:00"
        sunset = f"{today}T20:00"

    line = (
        f"weather_forecast,team={INFLUX_TEAM} "
        f"temperature={temperature},"
        f"rain_12h={rain_volume},"
        f"rain_prob_12h={rain_probability},"
        f"actual_rain_6h={actual_rain},"
        f'sunrise="{sunrise}",'
        f'sunset="{sunset}"'
    )

    response = requests.post(
        f"{INFLUXDB_URL}/write",
        params={"db": DB_NAME},
        auth=HTTPBasicAuth(DB_USERNAME, DB_PASSWORD),
        data=line,
        timeout=5,
    )
    response.raise_for_status()
    print("[TEST] Weather values written to InfluxDB.")


def on_connect(client, _userdata, _flags, reason_code, _properties):
    if reason_code == 0:
        client.subscribe(COMMAND_TOPIC, qos=1)
        print(f"[MQTT] Connected. Listening on {COMMAND_TOPIC}")


def on_message(_client, _userdata, message):
    print(f"[MQTT] Brain command received: {message.payload.decode()}")


def main():
    print("\n--- SMART AGRICULTURE RULE TEST INJECTOR ---")

    moisture = float(input("Moisture %: "))
    water_liters = float(input("Water liters for this event (usually 0): "))
    temperature = float(input("Temperature C: "))
    rain_probability = float(input("Rain probability next 12h %: "))
    rain_volume = float(input("Forecast rain next 12h mm: "))
    actual_rain = float(input("Actual rain last 6h mm: "))

    mode = input("Day mode [day/night/real]: ").strip().lower()
    if mode not in {"day", "night", "real"}:
        mode = "real"

    write_weather(
        temperature,
        rain_probability,
        rain_volume,
        actual_rain,
        mode,
    )

    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"{MQTT_TEAM}-test-injector",
    )
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(BROKER, PORT, 60)
    client.loop_start()
    time.sleep(1)

    observed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    payload = {
        "@context": [
            "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld"
        ],
        "id": f"urn:ngsi-ld:AgriSoil:{MQTT_TEAM}",
        "type": "AgriSoil",
        "moisture_percent": {
            "type": "Property",
            "value": moisture,
            "unitCode": "P1",
            "observedAt": observed_at,
        },
        "water_liters": {
            "type": "Property",
            "value": water_liters,
            "unitCode": "LTR",
            "observedAt": observed_at,
        },
    }

    result = client.publish(
        TELEMETRY_TOPIC,
        json.dumps(payload),
        qos=1,
    )
    result.wait_for_publish()

    print("[TEST] Telemetry published. Check brain.py and Grafana.")
    time.sleep(5)

    client.loop_stop()
    client.disconnect()


if __name__ == "__main__":
    main()
