import requests
from requests.auth import HTTPBasicAuth

INFLUXDB_URL = "http://194.177.207.38:8086/write?db=edge12_db"
AUTH = HTTPBasicAuth("edge12", "team1@#$")
TEAM = "XLR8"

print("\n🧪 --- ΕΡΓΑΛΕΙΟ ΔΟΚΙΜΩΝ (DATA SPOOFER) ---")
moisture = input("👉 Δώσε ψεύτικη Υγρασία (0-100): ")
rain = input("👉 Δώσε ψεύτικη Πιθανότητα Βροχής (0-100): ")

# Φτιάχνουμε τα μηνύματα ακριβώς όπως τα περιμένει το brain.py
line_telemetry = f"telemetry,team={TEAM} moisture_percent={moisture}"
line_weather = f"weather_forecast,team={TEAM} rain_probability={rain}"

try:
    # Στέλνουμε τα ψεύτικα δεδομένα στη βάση
    requests.post(INFLUXDB_URL, auth=AUTH, data=line_telemetry)
    requests.post(INFLUXDB_URL, auth=AUTH, data=line_weather)
    print("\n✅ Τα δεδομένα στάλθηκαν επιτυχώς στην InfluxDB!")
    print("👀 Κοίτα το τερματικό του 'brain.py' να δεις τι απόφαση θα πάρει στο επόμενο λεπτό!")
except Exception as e:
    print(f"❌ Σφάλμα: {e}")
