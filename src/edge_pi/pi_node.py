import json
import random
import socket
import time
from typing import Optional, List

import paho.mqtt.client as mqtt
import requests
from requests.auth import HTTPBasicAuth



BROKER = "194.177.207.38"
PORT = 1883
TEAM = socket.gethostname()

MQTT_USERNAME = "team1"
MQTT_PASSWORD = "team1!@#$"

MQTT_TOPIC = f"sensors/{TEAM}/telemetry"

INFLUXDB_URL = "http://194.177.207.38:8086"
DB_NAME = f"{TEAM}_db"
DB_USERNAME = "edge12"
DB_PASSWORD = "team1@#$"

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

    





