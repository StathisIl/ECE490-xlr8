import time
import socket
import json
import paho.mqtt.client as mqtt
import RPi.GPIO as GPIO
import board
import busio
import adafruit_ads1x15.ads1015 as ADS
from adafruit_ads1x15.analog_in import AnalogIn


# μην ξεχασω να σεταρω για τους σενσορες!!!!!!!
# μην ξεχασω να σεταρω για τους σενσορες!!!!!!!
# μην ξεχασω να σεταρω για τους σενσορες!!!!!!!
# μην ξεχασω να σεταρω για τους σενσορες!!!!!!!

BROKER = "194.177.207.38"
PORT = 1883
TEAM = socket.gethostname()

MQTT_USERNAME = "team1"
MQTT_PASSWORD = "team1!@#$"
MQTT_TOPIC = f"sensors/{TEAM}/telemetry"

FLOW_SENSOR_PIN = 17
pulse_count = 0
# Ρυθμίσεις ADS1015 και Υγρασίας 
i2c = board.I2C()
ads = ADS.ADS1015(i2c)



INFLUXDB_URL = "http://194.177.207.38:8086"
DB_NAME = f"{TEAM}_db"
DB_USERNAME = "edge12"
DB_PASSWORD = "team1@#$"


# MQTT SETUP
# MQTT SETUP
# MQTT SETUP
# MQTT SETUP

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to broker.")
    else:
        print(f"Connection failed with code {rc}")



def setup_mqtt():
    client = mqtt.Client(client_id=TEAM)
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.on_connect = on_connect

    try:
        client.connect(BROKER, PORT, 60)
        client.loop_start() 
        return client
    except Exception as e:
        print(f"Failed MQTT connection: {e}")
        return None

def publish_data(client, moisture, flow):
    if client is None:
        return 
        
    payload = {
        "team": TEAM,
        "moisture_raw": moisture,
        "flow_pulses": flow,
        "timestamp": int(time.time()) 
    }

    json_message = json.dumps(payload)
    client.publish(MQTT_TOPIC, json_message)
    print(f"Just Send: {json_message}")


#HARDWARE SETUP
#HARDWARE SETUF
#HARDWARE SETUF
#HARDWARE SETUF


def count_pulse(channel):
    global pulse_count
    pulse_count += 1


def setup_hardware():
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(FLOW_SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.add_event_detect(FLOW_SENSOR_PIN, GPIO.FALLING, callback=count_pulse)

# def main() -> None:
    




    





