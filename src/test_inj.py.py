import requests
from requests.auth import HTTPBasicAuth

# --- CONFIGURATION ---
INFLUXDB_URL = "http://194.177.207.38:8086/write?db=edge12_db"
AUTH = HTTPBasicAuth("edge12", "team1@#$")
TEAM = "edge12"  # ΔΙΟΡΘΩΘΗΚΕ: Από XLR8 έγινε edge12

print("\n🧪 --- ΕΡΓΑΛΕΙΟ ΔΟΚΙΜΩΝ V2 (ADVANCED DATA SPOOFER) ---")
print("Ας ξεγελάσουμε τον 7-Core Εγκέφαλο δίνοντάς του ακραία σενάρια!\n")

# 1. Ζητάμε τα δεδομένα από τον χρήστη
moisture = input("👉 Δώσε Υγρασία Εδάφους (π.χ. 15 για ξερό, 60 για υγρό): ")
temp = input("👉 Δώσε Θερμοκρασία (π.χ. 25 για κανονική, 35 για καύσωνα): ")
rain_prob = input("👉 Δώσε Πιθανότητα Βροχής % (π.χ. 0 ή 80): ")
future_rain = input("👉 Δώσε Επερχόμενη Βροχή mm (π.χ. 0 ή 10 για μπόρα): ")
past_rain = input("👉 Δώσε Πραγματική Βροχή Παρελθόντος mm (π.χ. 0 ή 5): ")
is_day = input("👉 Είναι Μέρα; (ν/ο): ").strip().lower()

# 2. Ρύθμιση Ήλιου (Μέρα vs Νύχτα)
if is_day == 'ν':
    sunrise = "2026-06-20T05:00"
    sunset = "2026-06-20T21:00"
else:
    # Αν θέλουμε να νομίζει ότι είναι "νύχτα", βάζουμε τη δύση σε ώρα που έχει ήδη περάσει
    sunrise = "2026-06-20T00:00"
    sunset = "2026-06-20T01:00"

# 3. Φτιάχνουμε τα μηνύματα ακριβώς όπως τα περιμένει το νέο brain.py
line_telemetry = f"telemetry,team={TEAM} moisture_percent={moisture}"

line_weather = (
    f"weather_forecast,team={TEAM} "
    f"temperature={temp},rain_12h={future_rain},rain_prob_12h={rain_prob},"
    f"actual_rain_6h={past_rain},"
    f"sunrise=\"{sunrise}\",sunset=\"{sunset}\""
)

try:
    # Στέλνουμε τα ψεύτικα δεδομένα στη βάση
    requests.post(INFLUXDB_URL, auth=AUTH, data=line_telemetry)
    requests.post(INFLUXDB_URL, auth=AUTH, data=line_weather)
    print("\n✅ Τα δεδομένα στάλθηκαν επιτυχώς στην InfluxDB!")
    print("👀 Κοίτα το τερματικό του 'brain.py' να δεις ποιον Κανόνα θα ενεργοποιήσει!")
except Exception as e:
    print(f"❌ Σφάλμα: {e}")