import os
import time
import requests
from datetime import datetime
from requests.auth import HTTPBasicAuth

# --- ΕΠΙΒΟΛΗ ΕΛΛΗΝΙΚΗΣ ΩΡΑΣ (ΠΑΡΑΚΑΜΨΗ ΤΟΥ ΛΕΙΤΟΥΡΓΙΚΟΥ) ---
os.environ['TZ'] = 'Europe/Athens'
time.tzset()

# --- CONFIGURATION ΔΙΚΤΥΟΥ ---
INFLUXDB_URL = "http://194.177.207.38:8086"
DB_NAME = "edge12_db"
DB_USERNAME = "edge12"
DB_PASSWORD = "team1@#$"
TEAM = "edge12" # Η σωστή ομάδα!

# --- ΟΙ 6 ΧΡΥΣΟΙ ΚΑΝΟΝΕΣ ΠΟΤΙΣΜΑΤΟΣ (THRESHOLDS) ---
COOLDOWN_MINUTES = 10             # Κανόνας 1: Αναμονή μετά το πότισμα (Λεπτά)
CRITICAL_MOISTURE = 30.0          # Κανόνας 2: Όριο επαρκούς υγρασίας (%)
RAIN_PROBABILITY_THRESHOLD = 60.0 # Κανόνας 3: Όριο πιθανότητας βροχής (%)
RAIN_VOLUME_THRESHOLD = 2.0       # Κανόνας 4: Αναμενόμενος όγκος βροχής (mm)
HEATWAVE_THRESHOLD = 32.0         # Κανόνας 5: Όριο καύσωνα (°C)

# --- ΣΥΝΑΡΤΗΣΕΙΣ ΒΑΣΗΣ ΔΕΔΟΜΕΝΩΝ ---

def get_latest_value(measurement: str, field: str, as_string: bool = False):
    """Κάνει query στην InfluxDB για την τελευταία τιμή."""
    url = f"{INFLUXDB_URL}/query"
    query = f'SELECT last("{field}") FROM "{measurement}" WHERE "team"=\'{TEAM}\''
    params = {"db": DB_NAME, "q": query}
    auth = HTTPBasicAuth(DB_USERNAME, DB_PASSWORD)

    try:
        response = requests.get(url, params=params, auth=auth, timeout=5)
        response.raise_for_status()
        data = response.json()
        if "results" in data and len(data["results"]) > 0:
            result = data["results"][0]
            if "series" in result and len(result["series"]) > 0:
                val = result["series"][0]["values"][0][1]
                return str(val) if as_string else float(val)
        return None
    except Exception as e:
        print(f"❌ [Σφάλμα Βάσης] Αποτυχία ανάγνωσης του {field}: {e}")
        return None

def check_recent_watering(minutes: int) -> float:
    """Ρωτάει την InfluxDB πόσα λίτρα νερού έπεσαν τα τελευταία X λεπτά (Cooldown)."""
    url = f"{INFLUXDB_URL}/query"
    query = f'SELECT sum("water_liters") FROM "telemetry" WHERE "team"=\'{TEAM}\' AND time >= now() - {minutes}m'
    params = {"db": DB_NAME, "q": query}
    auth = HTTPBasicAuth(DB_USERNAME, DB_PASSWORD)

    try:
        response = requests.get(url, params=params, auth=auth, timeout=5)
        response.raise_for_status()
        data = response.json()
        if "results" in data and len(data["results"]) > 0:
            result = data["results"][0]
            if "series" in result and len(result["series"]) > 0:
                return float(result["series"][0]["values"][0][1])
        return 0.0 # 0 λίτρα αν δεν βρει δεδομένα
    except Exception:
        return 0.0

# --- ΣΥΝΑΡΤΗΣΕΙΣ ΛΟΓΙΚΗΣ ---

def is_daytime(sunrise_str: str, sunset_str: str) -> bool:
    """Υπολογίζει αν αυτή τη στιγμή είναι μέρα (ανάμεσα σε ανατολή και δύση)."""
    try:
        # Το API στέλνει την ώρα ως "2024-06-06T06:05". Αφαιρούμε τα εισαγωγικά αν υπάρχουν.
        sunrise_str = sunrise_str.replace('"', '')
        sunset_str = sunset_str.replace('"', '')
        
        sunrise_dt = datetime.strptime(sunrise_str, "%Y-%m-%dT%H:%M")
        sunset_dt = datetime.strptime(sunset_str, "%Y-%m-%dT%H:%M")
        now = datetime.now()
        
        # --- ΓΡΑΜΜΕΣ DEBUG: Για να βλέπουμε την ώρα ---
        print(f"    [DEBUG] ΩΡΑ ΠΟΥ ΝΟΜΙΖΕΙ ΤΟ PI (now)  : {now}")
        print(f"    [DEBUG] ΑΝΑΤΟΛΗ ΠΟΥ ΔΙΑΒΑΣΕ (sunrise): {sunrise_dt}")
        print(f"    [DEBUG] ΔΥΣΗ ΠΟΥ ΔΙΑΒΑΣΕ (sunset)    : {sunset_dt}")
        # -----------------------------------------------------------------------
        
        return sunrise_dt <= now <= sunset_dt
    except Exception as e:
        print(f"    [DEBUG ERROR] Κάτι έσκασε στον υπολογισμό ώρας: {e}")
        # Fallback ασφαλείας: Αν χαλάσει το parsing, θεωρούμε "μέρα" από 07:00 έως 20:00
        current_hour = datetime.now().hour
        return 7 <= current_hour <= 20

def make_decision(moisture, rain_prob, rain_vol, temp, recent_water, sunrise_str, sunset_str):
    """
    Ο Απόλυτος Εγκέφαλος: Ελέγχει και τους 6 κανόνες με αυστηρή ιεραρχία προστασίας.
    """
    print("\n" + "="*55)
    print(" 🧠 SMART IRRIGATION: DECISION ENGINE (6 RULES)")
    print("="*55)
    print(f" 📊 Υγρασία Εδάφους: {moisture:.1f}%")
    print(f" 🌡️ Θερμοκρασία    : {temp:.1f} °C")
    print(f" ☁️ Βροχή (12h)    : Πιθανότητα {rain_prob:.1f}% | Όγκος {rain_vol} mm")
    print(f" 💧 Νερό (τελ.{COOLDOWN_MINUTES}m) : {recent_water:.2f} Λίτρα")
    
    daytime = is_daytime(sunrise_str, sunset_str)
    print(f" ☀️ Φάση Ημέρας    : {'ΜΕΡΑ (Κίνδυνος Εξάτμισης)' if daytime else 'ΝΥΧΤΑ (Ιδανικό)'}\n")
    
    # --- ΙΕΡΑΡΧΙΑ ΚΑΝΟΝΩΝ ---
    
    # ΚΑΝΟΝΑΣ 1: Cooldown (Προστασία από πλημμύρα)
    if recent_water > 0.1:
        print(" 🛑 [STATUS: RULE 1 - COOLDOWN ACTIVE]")
        print(f"    ΛΟΓΟΣ: Το σύστημα πότισε {recent_water:.2f}L τα τελευταία {COOLDOWN_MINUTES} λεπτά.")
        print("    ΕΝΕΡΓΕΙΑ: Ακύρωση. Προστασία από υπερχείλιση.")
        
    # ΚΑΝΟΝΑΣ 5: Καύσωνας (Προστασία από εγκαύματα ριζών)
    elif temp >= HEATWAVE_THRESHOLD:
        print(" 🔥 [STATUS: RULE 5 - HEATWAVE PROTECTION]")
        print(f"    ΛΟΓΟΣ: Η θερμοκρασία ({temp}°C) είναι πολύ υψηλή.")
        print("    ΕΝΕΡΓΕΙΑ: Ακύρωση. Κίνδυνος θερμικού σοκ στα φυτά.")

    # ΚΑΝΟΝΑΣ 6: Ώρα της Ημέρας (Αποφυγή εξάτμισης)
    elif daytime:
        print(" ☀️ [STATUS: RULE 6 - DAYTIME EVAPORATION PREVENTION]")
        print("    ΛΟΓΟΣ: Ο ήλιος είναι ψηλά. Το νερό θα εξατμιστεί άσκοπα.")
        print("    ΕΝΕΡΓΕΙΑ: Ακύρωση. Αναμονή για τη νύχτα.")

    # ΚΑΝΟΝΑΣ 2: Επαρκής Υγρασία
    elif moisture >= CRITICAL_MOISTURE:
        print(" ✅ [STATUS: RULE 2 - MOISTURE SUFFICIENT]")
        print(f"    ΛΟΓΟΣ: Το χώμα είναι ήδη αρκετά υγρό ({moisture}%).")
        print("    ΕΝΕΡΓΕΙΑ: Καμία δράση. Το σύστημα παραμένει σε αναμονή.")

    # ΚΑΝΟΝΑΣ 4: Επερχόμενη Καταιγίδα (Μεγάλος Όγκος)
    elif rain_vol >= RAIN_VOLUME_THRESHOLD:
        print(" ⛈️ [STATUS: RULE 4 - STORM INCOMING]")
        print(f"    ΛΟΓΟΣ: Αναμένονται {rain_vol} mm βροχής (Μπόρα).")
        print("    ΕΝΕΡΓΕΙΑ: Αναβολή ποτίσματος.")

    # ΚΑΝΟΝΑΣ 3: Πιθανότητα Βροχής (Οικονομία Νερού)
    elif rain_prob >= RAIN_PROBABILITY_THRESHOLD:
        print(" ⏳ [STATUS: RULE 3 - RAIN DELAY POLICY]")
        print(f"    ΛΟΓΟΣ: Υψηλή πιθανότητα βροχής ({rain_prob}%).")
        print("    ΕΝΕΡΓΕΙΑ: Αναβολή ποτίσματος. Αφήνουμε τη φύση να δουλέψει.")

    # ΑΝ ΠΕΡΑΣΕ ΟΛΟΥΣ ΤΟΥΣ ΕΛΕΓΧΟΥΣ -> ΠΟΤΙΖΟΥΜΕ!
    else:
        print(" 🚨 [STATUS: CONDITIONS PERFECT - ACTION REQUIRED]")
        print("    ΛΟΓΟΣ: Ξηρό έδαφος, νύχτα, δροσιά, χωρίς βροχή.")
        print("    ΕΝΕΡΓΕΙΑ: ΞΕΚΙΝΗΣΤΕ ΤΟ ΠΟΤΙΣΜΑ ΑΜΕΣΑ!")

    print("="*55 + "\n")

def main():
    print("🤖 Ο 6-Core Έξυπνος Εγκέφαλος ξεκίνησε τη λειτουργία του...")
    print("Κάνει έλεγχο δεδομένων κάθε 5 δευτερόλεπτα (Λειτουργία Test)...\n")
    
    while True:
        # Τράβηγμα των τηλεμετριών (Από το pi_node.py)
        latest_moisture = get_latest_value("telemetry", "moisture_percent")
        recent_water = check_recent_watering(COOLDOWN_MINUTES)
        
        # Τράβηγμα των καιρικών δεδομένων (Από το weather_api.py)
        latest_temp = get_latest_value("weather_forecast", "temperature")
        latest_rain_prob = get_latest_value("weather_forecast", "rain_prob_12h")
        latest_rain_vol = get_latest_value("weather_forecast", "rain_12h")
        sunrise = get_latest_value("weather_forecast", "sunrise", as_string=True)
        sunset = get_latest_value("weather_forecast", "sunset", as_string=True)
        
        # Έλεγχος ότι έχουμε όλα τα δεδομένα πριν τρέξουμε τη λογική
        if None not in (latest_moisture, latest_temp, latest_rain_prob, latest_rain_vol, sunrise, sunset):
            make_decision(latest_moisture, latest_rain_prob, latest_rain_vol, latest_temp, recent_water, sunrise, sunset)
        else:
            print("⏳ Αναμονή... Λείπουν δεδομένα από τη βάση (περιμένουμε το weather_api ή το pi_node να στείλουν).")
            
        time.sleep(5) 

if __name__ == "__main__":
    main()
