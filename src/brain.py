import json
from datetime import datetime

import paho.mqtt.client as mqtt
import requests
from requests.auth import HTTPBasicAuth

# --- MQTT CONFIGURATION ---
BROKER = "194.177.207.38"
PORT = 1883
TEAM = "edge12"
MQTT_TEAM = "XLR8"

MQTT_USERNAME = "team1"
MQTT_PASSWORD = "team1!@#$"
TELEMETRY_TOPIC = f"iot/{MQTT_TEAM}/telemetry/soilMoisture"
COMMAND_TOPIC = f"iot/{MQTT_TEAM}/control/irrigation"

# --- INFLUXDB CONFIGURATION ---
INFLUXDB_URL = "http://194.177.207.38:8086"
DB_NAME = f"{TEAM}_db"
DB_USERNAME = "edge12"
DB_PASSWORD = "team1@#$"

# --- IRRIGATION RULES ---
MOISTURE_THRESHOLD = 35.0
COOLDOWN_MINUTES = 10
RAIN_PROBABILITY_THRESHOLD = 60.0
RAIN_VOLUME_THRESHOLD = 2.0
HEATWAVE_THRESHOLD = 32.0
ACTUAL_RAIN_THRESHOLD = 2.0

# Dynamic Duty Cycling policy
SLEEP_NORMAL_SECONDS = 5
SLEEP_DRY_SECONDS = 5
SLEEP_RAIN_DELAY_SECONDS = 5


def influx_auth():
    return HTTPBasicAuth(DB_USERNAME, DB_PASSWORD)


def escape_influx_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def write_to_influxdb(line_protocol: str):
    """Write a line-protocol record to InfluxDB."""
    response = requests.post(
        f"{INFLUXDB_URL}/write",
        params={"db": DB_NAME},
        auth=influx_auth(),
        data=line_protocol,
        timeout=5,
    )
    response.raise_for_status()


def write_telemetry(moisture_percent: float, water_liters: float):
    line = (
        f"telemetry,team={TEAM} "
        f"moisture_percent={moisture_percent:.1f},"
        f"water_liters={water_liters:.3f}"
    )
    write_to_influxdb(line)
    print(f"[DATABASE] Telemetry written: {line}")


def write_decision(action: int, rule_id: int, status_message: str):
    line = (
        f"decision_log,team={TEAM} "
        f"action={action},"
        f"active_rule={rule_id},"
        f"status_msg=\"{escape_influx_string(status_message)}\""
    )
    write_to_influxdb(line)
    print(f"[DATABASE] Decision written: {status_message}")


def query_influx(query: str):
    response = requests.get(
        f"{INFLUXDB_URL}/query",
        params={"db": DB_NAME, "q": query},
        auth=influx_auth(),
        timeout=5,
    )
    response.raise_for_status()
    return response.json()

def on_log(_client, _userdata, _level, buffer):
    print(f"[MQTT DEBUG] {buffer}")

def get_latest_value(measurement: str, field: str, as_string: bool = False):
    query = (
        f'SELECT last("{field}") FROM "{measurement}" '
        f'WHERE "team"=\'{TEAM}\''
    )

    try:
        data = query_influx(query)
        series = data["results"][0].get("series", [])
        if not series:
            return None

        value = series[0]["values"][0][1]
        return str(value) if as_string else float(value)

    except (requests.RequestException, KeyError, IndexError, TypeError, ValueError) as exc:
        print(f"[DATABASE] Failed to read {measurement}.{field}: {exc}")
        return None


def get_recent_water_liters(minutes: int) -> float:
    query = (
        f'SELECT sum("water_liters") FROM "telemetry" '
        f'WHERE "team"=\'{TEAM}\' AND time >= now() - {minutes}m'
    )

    try:
        data = query_influx(query)
        series = data["results"][0].get("series", [])
        return float(series[0]["values"][0][1]) if series else 0.0
    except (requests.RequestException, KeyError, IndexError, TypeError, ValueError):
        return 0.0


def is_daytime(sunrise: str, sunset: str) -> bool:
    try:
        sunrise_dt = datetime.fromisoformat(sunrise.replace("Z", "+00:00"))
        sunset_dt = datetime.fromisoformat(sunset.replace("Z", "+00:00"))
        now = datetime.now(sunrise_dt.tzinfo)
        return sunrise_dt <= now <= sunset_dt
    except (TypeError, ValueError):
        hour = datetime.now().hour
        return 7 <= hour <= 20


def get_weather():
    """Return latest weather values written by weather_api.py."""
    weather = {
        "temperature": get_latest_value("weather_forecast", "temperature"),
        "rain_probability": get_latest_value("weather_forecast", "rain_prob_12h"),
        "rain_volume": get_latest_value("weather_forecast", "rain_12h"),
        "actual_rain": get_latest_value("weather_forecast", "actual_rain_6h"),
        "sunrise": get_latest_value("weather_forecast", "sunrise", as_string=True),
        "sunset": get_latest_value("weather_forecast", "sunset", as_string=True),
    }

    if any(value is None for value in weather.values()):
        return None

    return weather


def evaluate_rules(moisture: float, weather: dict | None, recent_water: float):
    """
    Seven-rule decision engine.

    Rule 2 is evaluated first for normal moisture levels. Weather is queried
    only when moisture is below 25%, satisfying the Rain Delay policy flow.
    """
    if moisture >= MOISTURE_THRESHOLD:
        return 0, 2, "RULE 2 - MOISTURE SUFFICIENT", SLEEP_NORMAL_SECONDS

    if weather is None:
        return (
            0,
            0,
            "WEATHER DATA UNAVAILABLE - IRRIGATION DEFERRED",
            SLEEP_DRY_SECONDS,
        )

    if recent_water > 0.1:
        return 0, 1, "RULE 1 - COOLDOWN ACTIVE", SLEEP_NORMAL_SECONDS

    if weather["temperature"] >= HEATWAVE_THRESHOLD:
        return 0, 5, "RULE 5 - HEATWAVE PROTECTION", SLEEP_DRY_SECONDS

    if is_daytime(weather["sunrise"], weather["sunset"]):
        return 0, 6, "RULE 6 - DAYTIME EVAPORATION PREVENTION", SLEEP_NORMAL_SECONDS

    if weather["actual_rain"] >= ACTUAL_RAIN_THRESHOLD:
        return 0, 7, "RULE 7 - RECENT RAIN CONFIRMED", SLEEP_RAIN_DELAY_SECONDS

    if weather["rain_volume"] >= RAIN_VOLUME_THRESHOLD:
        return 0, 4, "RULE 4 - STORM INCOMING", SLEEP_RAIN_DELAY_SECONDS

    if weather["rain_probability"] >= RAIN_PROBABILITY_THRESHOLD:
        return 0, 3, "RULE 3 - RAIN DELAY POLICY", SLEEP_RAIN_DELAY_SECONDS

    return 1, 0, "CONDITIONS PERFECT - IRRIGATION REQUIRED", SLEEP_DRY_SECONDS


def publish_sleep_command(client, sleep_seconds: int):
    command = {
        "command": "SET_SLEEP",
        "value": sleep_seconds,
    }

    result = client.publish(COMMAND_TOPIC, json.dumps(command), qos=1)

    if result.rc == mqtt.MQTT_ERR_SUCCESS:
        print(f"[MQTT] QoS 1 command published: {command}")
    else:
        print(f"[MQTT] Command publish failed with code {result.rc}")


def parse_ngsi_ld_telemetry(payload: bytes) -> tuple[float, float]:
    entity = json.loads(payload.decode("utf-8"))

    if entity.get("type") != "AgriSoil":
        raise ValueError("Unexpected NGSI-LD entity type.")

    moisture = float(entity["moisture_percent"]["value"])
    water_liters = float(entity["water_liters"]["value"])

    return moisture, water_liters


def process_telemetry(client, payload: bytes):
    """Event-driven processing for one incoming edge telemetry message."""
    moisture, water_liters = parse_ngsi_ld_telemetry(payload)

    # Step A: immediately persist telemetry for Grafana.
    write_telemetry(moisture, water_liters)

    # Step B: query weather only if soil moisture is below 25%.
    weather = get_weather() if moisture < MOISTURE_THRESHOLD else None
    recent_water = get_recent_water_liters(COOLDOWN_MINUTES)

    # Steps C and D: make and persist the decision.
    action, rule_id, status, sleep_seconds = evaluate_rules(
        moisture=moisture,
        weather=weather,
        recent_water=recent_water,
    )
    write_decision(action, rule_id, status)

    # Step E: dynamically update the Pi duty cycle.
    publish_sleep_command(client, sleep_seconds)

    print(
        f"[DECISION] moisture={moisture:.1f}% | action={action} | "
        f"rule={rule_id} | sleep={sleep_seconds}s | {status}"
    )


def on_connect(client, _userdata, _flags, reason_code, _properties=None):
    if reason_code == 0:
        print("[MQTT] Logic Hub connected.")
        client.subscribe(TELEMETRY_TOPIC, qos=1)
        print(f"[MQTT] Subscribed to {TELEMETRY_TOPIC} with QoS 1.")
    else:
        print(f"[MQTT] Connection failed: {reason_code}")


def on_message(client, _userdata, message):
    print(
        f"[MQTT] RAW message received | "
        f"topic={message.topic} | payload={message.payload!r}"
    )

    if message.topic != TELEMETRY_TOPIC:
        return

    try:
        process_telemetry(client, message.payload)
    except (
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
        requests.RequestException,
    ) as exc:
        print(f"[ERROR] Failed to process telemetry event: {exc}")

def on_subscribe(_client, _userdata, mid, granted_qos, _properties=None):
    print(
        f"[MQTT] Subscription acknowledged. "
        f"Message id: {mid}, granted QoS: {granted_qos}"
    )


def on_disconnect(
        _client,
        _userdata,
        _disconnect_flags,
        reason_code,
        _properties,
    ):
        print(f"[MQTT] Disconnected from broker. Reason: {reason_code}")

def main():
    print("[SYSTEM] Starting event-driven Smart Agriculture Logic Hub...")

    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"{MQTT_TEAM}-brain",
    )
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_subscribe = on_subscribe
    client.on_disconnect = on_disconnect
    client.on_log = on_log
    client.reconnect_delay_set(min_delay=1, max_delay=30)

    client.connect(BROKER, PORT, keepalive=60)

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n[SYSTEM] Logic Hub stopped.")
    finally:
        client.disconnect()


if __name__ == "__main__":
    main()
