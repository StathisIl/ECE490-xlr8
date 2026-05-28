import time
import requests
from datetime import datetime
from requests.auth import HTTPBasicAuth
import paho.mqtt.client as mqtt

# --- 1. CONFIGURATION ---
TEAM = "edge12"

# InfluxDB Configuration
INFLUXDB_URL = "http://194.177.207.38:8086"
DB_NAME = f"{TEAM}_db"
DB_USERNAME = "edge12"
DB_PASSWORD = "team1@#$"

# MQTT Configuration
BROKER = "194.177.207.38"
PORT = 1883
MQTT_USERNAME = "team1"
MQTT_PASSWORD = "team1!@#$"

# MQTT Topics sent by the Raspberry Pi
HUMIDITY_TOPIC = f"sensors/{TEAM}/humidity"
FLOW_TOPIC = f"sensors/{TEAM}/flow"

# --- 2. THRESHOLDS (The Agricultural Rules) ---
MOISTURE_THRESHOLD = 30.0   # If moisture >= 30%, do not water
RAIN_THRESHOLD = 2.0        # If rain > 2.0mm, do not water
TEMP_THRESHOLD = 32.0       # If temp > 32C, do not water
FLOW_THRESHOLD = 0.5        # If flow >= 0.5 L/min, we consider it actively watering

# --- 3. GLOBAL MEMORY ---
# Stores the timestamp of the last detected water flow
last_watering_time = 0.0


# --- 4. HTTP FUNCTIONS (Database & Weather) ---
def send_decision_to_influxdb(decision: int):
    """Sends the final watering decision (0 or 1) to InfluxDB."""
    url = f"{INFLUXDB_URL}/write"
    params = {"db": DB_NAME}
    auth = HTTPBasicAuth(DB_USERNAME, DB_PASSWORD)
    line = f"watering_decision,team={TEAM} value={decision}"
    
    try:
        requests.post(url, params=params, auth=auth, data=line, timeout=5)
        print(f"[ACTION] Decision '{decision}' successfully written to InfluxDB.")
    except Exception as e:
        print(f"[ERROR] Could not write decision to DB: {e}")

def get_latest_weather():
    """Queries InfluxDB for the latest weather forecast."""
    url = f"{INFLUXDB_URL}/query"
    query = "SELECT temp, rain_12h, sunrise, sunset FROM weather_forecast ORDER BY time DESC LIMIT 1"
    params = {"db": DB_NAME, "q": query}
    auth = HTTPBasicAuth(DB_USERNAME, DB_PASSWORD)
    
    try:
        response = requests.get(url, params=params, auth=auth, timeout=5)
        data = response.json()
        series = data.get("results", [])[0].get("series", [])
        if not series: 
            return None
        return dict(zip(series[0]["columns"], series[0]["values"][0]))
    except Exception as e:
        print(f"[ERROR] Failed to fetch weather data: {e}")
        return None


# --- 5. THE DECISION ENGINE ---
def make_watering_decision(moisture: float) -> int:
    """Evaluates all conditions and returns 1 (Water) or 0 (Do not water)."""
    global last_watering_time

    # 1. Flow Sensor Check (Did we water in the last 10 minutes?)
    current_time = time.time()
    if (current_time - last_watering_time) < 600: # 600 seconds = 10 minutes
        print("[LOGIC] Watering occurred in the last 10 minutes! Status reset to 0.")
        return 0

    # 2. Moisture Check
    if moisture >= MOISTURE_THRESHOLD:
        print(f"[LOGIC] Soil is sufficiently wet ({moisture}%). No watering needed.")
        return 0

    print(f"[LOGIC] Soil is dry ({moisture}%). Evaluating weather conditions...")

    # 3. Weather Checks
    weather = get_latest_weather()
    if not weather:
        print("[LOGIC] WARNING: No weather data available. Defaulting to safe mode (0).")
        return 0

    temp = float(weather.get("temp", 0))
    rain = float(weather.get("rain_12h", 0))
    sunrise_str = weather.get("sunrise", "")
    sunset_str = weather.get("sunset", "")

    if rain >= RAIN_THRESHOLD:
        print(f"[LOGIC] Rain forecasted ({rain}mm in next 12h). Skipping watering.")
        return 0

    if temp >= TEMP_THRESHOLD:
        print(f"[LOGIC] Heatwave detected ({temp}°C). Skipping to avoid plant shock.")
        return 0

    # 4. Time Check (Timezone safe calculation for Greece)
    try:
        sunrise_hour = datetime.strptime(sunrise_str, "%Y-%m-%dT%H:%M").hour
        sunset_hour = datetime.strptime(sunset_str, "%Y-%m-%dT%H:%M").hour
        current_hour = (datetime.utcnow().hour + 3) % 24  # UTC+3 for Greece Summer Time
        
        if sunrise_hour <= current_hour < sunset_hour:
            print(f"[LOGIC] It is daytime (Current hour: {current_hour}:00). Skipping to avoid rapid evaporation.")
            return 0
    except Exception as e:
        print(f"[LOGIC] Time parsing error: {e}")
        pass
        
    print("[LOGIC] ✅ ALL CONDITIONS MET. GREEN LIGHT TO WATER!")
    return 1


# --- 6. MQTT CALLBACKS ---
def on_connect(client, userdata, flags, rc, properties=None):
    """Triggered upon successful connection to the MQTT Broker."""
    if rc == 0:
        print("[MQTT] Connected to Broker successfully!")
        client.subscribe(HUMIDITY_TOPIC)
        client.subscribe(FLOW_TOPIC)
        print(f"[MQTT] Listening to topic: {HUMIDITY_TOPIC}")
        print(f"[MQTT] Listening to topic: {FLOW_TOPIC}")
    else:
        print(f"[MQTT] Connection failed with code {rc}")

def on_message(client, userdata, msg):
    """Triggered every time a message is published to the subscribed topics."""
    global last_watering_time
    payload = msg.payload.decode("utf-8").strip()
    topic = msg.topic

    try:
        value = float(payload)
        
        # --- IF WATER FLOW DATA IS RECEIVED ---
        if topic == FLOW_TOPIC:
            if value >= FLOW_THRESHOLD:
                last_watering_time = time.time()
                print(f"\n[SENSOR] Water is currently flowing! ({value} L/min). Watering timer reset.")
                
        # --- IF MOISTURE DATA IS RECEIVED ---
        elif topic == HUMIDITY_TOPIC:
            print(f"\n{'='*50}\n[SENSOR] New moisture reading received: {value}%")
            decision = make_watering_decision(value)
            send_decision_to_influxdb(decision)
            
    except ValueError:
        print(f"[ERROR] Received non-numeric payload on {topic}: {payload}")


# --- 7. MAIN EXECUTION ---
if __name__ == "__main__":
    print("[SYSTEM] Starting Central Brain Node...")
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    
    client.on_connect = on_connect
    client.on_message = on_message
    
    print("[SYSTEM] Connecting to MQTT Broker...")
    client.connect(BROKER, PORT)
    
    # Keeps the script running and listening to MQTT forever
    client.loop_forever()
