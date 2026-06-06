import time
import requests
from requests.auth import HTTPBasicAuth

# --- CONFIGURATION ΔΙΚΤΥΟΥ ---
INFLUXDB_URL = "http://194.177.207.38:8086"
DB_NAME = "edge12_db"
DB_USERNAME = "edge12"
DB_PASSWORD = "team1@#$"
TEAM = "XLR8"

# --- ΟΡΙΑ ΑΠΟΦΑΣΗΣ (THRESHOLDS) ---
CRITICAL_MOISTURE = 30.0          # Αν η υγρασία πέσει κάτω από 30%, το φυτό διψάει
RAIN_PROBABILITY_THRESHOLD = 50   # Αν η πιθανότητα βροχής είναι >= 50%, ενεργοποιείται το Rain Delay

def get_latest_value(measurement: str, field: str):
    """
    Κάνει query στην InfluxDB για να πάρει την τελευταία χρονικά τιμή
    ενός συγκεκριμένου πεδίου από ένα συγκεκριμένο measurement.
    """
    url = f"{INFLUXDB_URL}/query"

    # SQL-like ερώτημα στην InfluxDB για την τελευταία καταγραφή της ομάδας μας
    query = f'SELECT last("{field}") FROM "{measurement}" WHERE "team"=\'{TEAM}\''

    params = {
        "db": DB_NAME,
        "q": query
    }
    auth = HTTPBasicAuth(DB_USERNAME, DB_PASSWORD)

    try:
        response = requests.get(url, params=params, auth=auth, timeout=5)
        response.raise_for_status()
        data = response.json()

        # Αποσυμπίεση του σύνθετου JSON που επιστρέφει η InfluxDB
        if "results" in data and len(data["results"]) > 0:
            result = data["results"][0]
            if "series" in result and len(result["series"]) > 0:
                series = result["series"][0]
                if "values" in series and len(series["values"]) > 0:
                    # Το values[0][0] είναι το timestamp, το values[0][1] είναι η τιμή
                    return float(series["values"][0][1])

        print(f"⚠️ [Προειδοποίηση] Δεν βρέθηκαν δεδομένα για το πεδίο '{field}' στο measurement '{measurement}'.")
        return None

    except Exception as e:
        print(f"❌ [Σφάλμα Βάσης] Αποτυχία ανάγνωσης του {field}: {e}")
        return None

def make_decision(moisture: float, rain_prob: float):
    """
    Ο Εγκέφαλος του συστήματος: Συγκρίνει τις τιμές και παίρνει την απόφαση.
    """
    print("\n" + "="*50)
    print(" 🧠 SMART IRRIGATION SYSTEM: DECISION ENGINE")
    print("="*50)
    print(f" 📊 Υγρασία Χώματος  : {moisture:.1f}%")
    print(f" ☁️  Πιθανότητα Βροχής: {rain_prob:.1f}%\n")

    # ΣΕΝΑΡΙΟ 1: Το χώμα είναι στεγνό (Κάτω από το όριο)
    if moisture < CRITICAL_MOISTURE:

        # Έλεγχος για Rain Delay Policy
        if rain_prob >= RAIN_PROBABILITY_THRESHOLD:
            print(" ⏳ [STATUS: RAIN DELAY POLICY - ACTIVE]")
            print("    ΛΟΓΟΣ   : Το χώμα είναι ξηρό, αλλά η πιθανότητα βροχής είναι υψηλή.")
            print("    ΕΝΕΡΓΕΙΑ: Αναβολή αυτόματου ποτίσματος για εξοικονόμηση νερού.")

        # Αν δεν αναμένεται βροχή, στέλνουμε Alert
        else:
            print(" 🚨 [STATUS: CRITICAL ALERT - ACTION REQUIRED]")
            print("    ΛΟΓΟΣ   : Το χώμα είναι ξηρό και δεν προβλέπεται βροχή.")
            print("    ΕΝΕΡΓΕΙΑ: ΞΕΚΙΝΗΣΤΕ ΤΟ ΠΟΤΙΣΜΑ ΑΜΕΣΑ!")

    # ΣΕΝΑΡΙΟ 2: Το χώμα έχει αρκετή υγρασία
    else:
        print(" ✅ [STATUS: SYSTEM NOMINAL]")
        print("    ΛΟΓΟΣ   : Η υγρασία του εδάφους είναι σε ιδανικά επίπεδα.")
        print("    ΕΝΕΡΓΕΙΑ: Καμία ενέργεια. Το σύστημα παραμένει σε αναμονή.")

    print("="*50 + "\n")

def main():
    print("🤖 Ο Έξυπνος Εγκέφαλος (Brain) ξεκίνησε τη λειτουργία του...")
    print(f"Κάνει έλεγχο δεδομένων κάθε 60 δευτερόλεπτα.\n")

    while True:
        # 1. Διαβάζει την τελευταία υγρασία από το 'telemetry' που γράφει το Pi
        latest_moisture = get_latest_value("telemetry", "moisture_percent")

        # 2. Διαβάζει την πιθανότητα βροχής από το 'weather_forecast'
        # (Σημείωση: Αν στο δικό σου weather script το ονομάσεις αλλιώς, άλλαξέ το εδώ!)
        latest_rain_prob = get_latest_value("weather_forecast", "rain_probability")

        # 3. Αν υπάρχουν και οι δύο μετρήσεις στη βάση, τρέχει τη λογική
        if latest_moisture is not None and latest_rain_prob is not None:
            make_decision(latest_moisture, latest_rain_prob)
        else:
            print("⏳ Αναμονή για λήψη έγκυρων δεδομένων από την InfluxDB...")

        # Περιμένει 1 λεπτό πριν τον επόμενο έλεγχο
        time.sleep(5)

if __name__ == "__main__":
    main()
