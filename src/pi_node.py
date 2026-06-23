import json
import time
from datetime import datetime, timezone

import board
import paho.mqtt.client as mqtt
from adafruit_ads1x15.analog_in import AnalogIn
import adafruit_ads1x15.ads1015 as ADS
from gpiozero import Button

# --- CONFIGURATION ---
BROKER = "194.177.207.38"
PORT = 1883
TEAM = "edge12"
MQTT_TEAM = "XLR8"

MQTT_USERNAME = "team1"
MQTT_PASSWORD = "team1!@#$"
TELEMETRY_TOPIC = f"iot/{MQTT_TEAM}/telemetry/soilMoisture"
COMMAND_TOPIC = f"iot/{MQTT_TEAM}/control/irrigation"

# Dynamic Duty Cycling default, updated by SET_SLEEP MQTT commands.
sleep_interval_seconds = 5

# Flow sensor calibration
PULSES_PER_LITER = 1621.3
FLOW_SENSOR_PIN = 17

# Soil moisture calibration
DRY_RAW = 21800.0
WATERED_RAW = 6208.0

DRY_TARGET_PERCENT = 25.0
WATERED_TARGET_PERCENT = 65.0

pulse_count = 0

# --- HARDWARE SETUP ---
i2c = board.I2C()
ads = ADS.ADS1015(i2c)
moisture_chan = AnalogIn(ads, 0)


def count_pulse(*_args):
    global pulse_count
    pulse_count += 1


def setup_hardware():
    flow_sensor = Button(FLOW_SENSOR_PIN, pull_up=True)
    flow_sensor.when_pressed = count_pulse
    return flow_sensor


# --- MQTT CALLBACKS ---
def on_connect(client, _userdata, _flags, reason_code, _properties=None):
    if reason_code == 0:
        print("[MQTT] Connected to broker.")
        client.subscribe(COMMAND_TOPIC, qos=1)
        print(f"[MQTT] Listening for commands on {COMMAND_TOPIC}")
    else:
        print(f"[MQTT] Connection failed: {reason_code}")


def on_message(_client, _userdata, message):
    global sleep_interval_seconds

    if message.topic != COMMAND_TOPIC:
        return

    try:
        command = json.loads(message.payload.decode("utf-8"))

        if command.get("command") == "SET_SLEEP":
            new_interval = int(command["value"])

            if new_interval < 1 or new_interval > 86400:
                raise ValueError("Sleep interval must be between 1 and 86400 seconds.")

            sleep_interval_seconds = new_interval
            print(f"[COMMAND] Sleep interval updated to {sleep_interval_seconds} seconds.")
        else:
            print(f"[COMMAND] Unsupported command: {command}")

    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(f"[COMMAND] Invalid command payload: {exc}")


def on_publish(_client, _userdata, mid, _reason_code=None, _properties=None):
    print(f"[MQTT] Broker acknowledged QoS 1 telemetry (message id: {mid}).")


def on_disconnect(_client, _userdata, disconnect_flags, reason_code, _properties=None):
    print(f"[MQTT] Disconnected from broker. Reason: {reason_code}")

def setup_mqtt():
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"{MQTT_TEAM}-pi",
    )
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_publish = on_publish
    client.on_disconnect = on_disconnect
    client.reconnect_delay_set(min_delay=1, max_delay=30)

    client.connect(BROKER, PORT, keepalive=60)
    client.loop_start()
    return client


# --- NGSI-LD TELEMETRY ---
def build_ngsi_ld_payload(moisture_percent: float, water_liters: float) -> dict:
    observed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    return {
        "@context": [
            "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld"
        ],
        "id": f"urn:ngsi-ld:AgriSoil:{TEAM}",
        "type": "AgriSoil",
        "moisture_percent": {
            "type": "Property",
            "value": round(moisture_percent, 1),
            "unitCode": "P1",
            "observedAt": observed_at,
        },
        "water_liters": {
            "type": "Property",
            "value": round(water_liters, 3),
            "unitCode": "LTR",
            "observedAt": observed_at,
        },
    }


def publish_data(client, moisture_percent: float, water_liters: float):
    payload = build_ngsi_ld_payload(moisture_percent, water_liters)
    payload_json = json.dumps(payload)

    # QoS 1 guarantees at-least-once delivery to the broker.
    result = client.publish(TELEMETRY_TOPIC, payload_json, qos=1)

    if result.rc == mqtt.MQTT_ERR_SUCCESS:
        print(f"[MQTT] Published QoS 1 telemetry: {payload_json}")
    else:
        print(f"[MQTT] Publish failed with code {result.rc}")


def calculate_moisture_percent(raw_value: float) -> float:
    if DRY_RAW == WATERED_RAW:
        return 0.0

    moisture = (
        DRY_TARGET_PERCENT
        + (WATERED_TARGET_PERCENT - DRY_TARGET_PERCENT)
        * (DRY_RAW - raw_value)
        / (DRY_RAW - WATERED_RAW)
    )

    return max(0.0, min(100.0, moisture))

def main():
    global pulse_count

    print("[SYSTEM] Starting Edge Node...")
    sensor_keepalive = setup_hardware()  # Prevents GPIO object garbage collection.
    mqtt_client = setup_mqtt()

    try:
        while True:
            raw_moisture = moisture_chan.value

            current_pulses = pulse_count
            pulse_count = 0

            moisture_percent = calculate_moisture_percent(raw_moisture)
            water_liters = current_pulses / PULSES_PER_LITER

            publish_data(mqtt_client, moisture_percent, water_liters)

            print(f"[SYSTEM] Sleeping for {sleep_interval_seconds} seconds.")
            time.sleep(sleep_interval_seconds)

    except KeyboardInterrupt:
        print("\n[SYSTEM] Stopped by user.")

    finally:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        del sensor_keepalive
        print("[SYSTEM] Cleanup complete.")


if __name__ == "__main__":
    main()
