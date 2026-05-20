import time
import board
import adafruit_ads1x15.ads1015 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
from gpiozero import Button

# --- Ρυθμίσεις Αισθητήρα Ροής (YF-S201) ---
FLOW_SENSOR_PIN = 17

flow_sensor = Button(FLOW_SENSOR_PIN, pull_up=True)
pulse_count = 0

def count_pulse():
    global pulse_count
    pulse_count += 1

flow_sensor.when_pressed = count_pulse

# --- Ρυθμίσεις ADS1015 & Υγρασίας ---
i2c = board.I2C()
ads = ADS.ADS1015(i2c)

# ΔΙΟΡΘΩΣΗ: Χρησιμοποιούμε το 0 απευθείας αντί για ADS.P0
chan = AnalogIn(ads, 0)

print("🚀 Το τεστ ξεκινάει! Πάτα Ctrl+C για να το σταματήσεις.\n")

try:
    while True:
        raw_value = chan.value
        voltage = chan.voltage
        
        print(f"💧 Υγρασία (Ακατέργαστη): {raw_value:5d} | Τάση: {voltage:.2f}V  ---  💦 Παλμοί: {pulse_count}")
        
        time.sleep(1)

except KeyboardInterrupt:
    print("\n🛑 Το τεστ σταμάτησε.")
