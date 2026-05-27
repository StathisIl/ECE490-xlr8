import time
import socket
import json
import paho.mqtt.client as mqtt
import requests
from requests.auth import HTTPBasicAuth
from gpiozero import Button
import board
import busio
import adafruit_ads1x15.ads1015 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

# --- CONFIGURATION ---
BROKER = "194.177.207.38"
PORT = 1883
TEAM = "XLR8"

MQTT_USERNAME = "team1"
MQTT_PASSWORD = "team1!@#$"
MQTT_TOPIC = f"sensors/{TEAM}/telemetry"

INFLUXDB_URL = "http://194.177.207.38:8086"
DB_NAME = "edge12_db"
DB_USERNAME = "edge12"
DB_PASSWORD = "team1@#$"

# Flow sensor calibration
PULSES_PER_LITER = 613.3


# Number when sensor is dry
DRY_VALUE = 25350.0  
# Number when sensor is completely submerged in water
WET_VALUE = 8000.0  

# HARDWARE SETUP 
FLOW_SENSOR_PIN = 17
pulse_count = 0

i2c = board.I2C()
ads = ADS.ADS1015(i2c)
moisture_chan = AnalogIn(ads, 0)

def count_pulse(*args):
    global pulse_count
    pulse_count += 1

def setup_hardware():
    flow_sensor = Button(FLOW_SENSOR_PIN, pull_up=True)
    flow_sensor.when_pressed = count_pulse

#  MQTT SETUP 
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("[MQTT] Connected to broker.")
    else:
        print(f"[MQTT] Connection failed (code {rc})")

def setup_mqtt():
    client = mqtt.Client(client_id=TEAM)
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.on_connect = on_connect
    try:
        client.connect(BROKER, PORT, 60)
        client.loop_start()
        return client
    except Exception as e:
        print(f"[MQTT] Connection error: {e}")
        return None

# INFLUXDB DIRECT WRITE
def write_to_influxdb(moisture_pct: float, liters: float):
    url = f"{INFLUXDB_URL}/write"
    params = {"db": DB_NAME}
    auth = HTTPBasicAuth(DB_USERNAME, DB_PASSWORD)
    
    # Format data for InfluxDB 
    line = f"telemetry,team={TEAM} moisture_percent={moisture_pct:.1f},water_liters={liters:.3f}"
    
    try:
        response = requests.post(url, params=params, auth=auth, data=line, timeout=2)
        if response.status_code in (200, 204):
            print(f"[InfluxDB] Success: {line}")
        else:
            print(f"[InfluxDB] Error {response.status_code}: {response.text}")
    except requests.RequestException as e:
        print(f"[InfluxDB] Connection error: {e}")

# PUBLISH DATA 
def publish_data(client, moisture_pct, liters):
    #  Write directly to InfluxDB (For Grafana)
    write_to_influxdb(moisture_pct, liters)

    # 2. Publish to MQTT (For project requirements)
    if client is not None:
        payload = {
            "team": TEAM,
            "moisture_percent": round(moisture_pct, 1),
            "water_liters": round(liters, 3),
            "timestamp": int(time.time())
        }
        json_message = json.dumps(payload)
        client.publish(MQTT_TOPIC, json_message)
        print(f"[MQTT] Sent: {json_message}")

#  MAIN LOOP 
def main() -> None:
    global pulse_count
    print("Starting Edge Node...")
    
    setup_hardware()
    mqtt_client = setup_mqtt()

    try:
        while True:
            #. Read raw sensor values
            current_raw_moisture = moisture_chan.value
            current_pulses = pulse_count
            pulse_count = 0  # Reset pulse counter for the next loop
            
            #  Convert raw pulses to liters
            water_liters = current_pulses / PULSES_PER_LITER
            
            # Convert raw moisture to percentage (0% to 100%)
            if DRY_VALUE != WET_VALUE:
                moisture_percent = 100.0 * (DRY_VALUE - current_raw_moisture) / (DRY_VALUE - WET_VALUE)
            else:
                moisture_percent = 0.0
                
            # Keep percentage strictly between 0 and 100 (clamp)
            moisture_percent = max(0.0, min(100.0, moisture_percent))
            
            #  Send the processed data
            publish_data(mqtt_client, moisture_percent, water_liters)
            
            # Wait 5 seconds
            time.sleep(5)
            
    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        if mqtt_client is not None:
            mqtt_client.loop_stop()
            mqtt_client.disconnect()
        print("Cleanup complete.")

if __name__ == "__main__":
    main()
