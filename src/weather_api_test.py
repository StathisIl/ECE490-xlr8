import time
import requests
from datetime import datetime
from requests.auth import HTTPBasicAuth

# --- 1. CONFIGURATION ---
TEAM = "edge12"

# InfluxDB Configuration
INFLUXDB_URL = "http://194.177.207.38:8086"
DB_NAME = f"{TEAM}_db"
DB_USERNAME = "edge12"
DB_PASSWORD = "team1@#$"

# How often to fetch weather (in seconds) - e.g., 1800s = 30 minutes
FETCH_INTERVAL = 1800

# Volos Coordinates
LATITUDE = 39.36
LONGITUDE = 22.94

# --- 2. WEATHER FETCH FUNCTION ---
def fetch_weather():
    """Fetches weather data from Open-Meteo and calculates 12-hour forecasts."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "current": "temperature_2m",  # Παίρνουμε την ΑΠΟΛΥΤΑ τρέχουσα θερμοκρασία
        "hourly": "temperature_2m,rain,precipitation_probability",
        "daily": "sunrise,sunset",
        "timezone": "auto",
        "forecast_days": 2  # 2 days ensures we have enough data if we check late at night
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status() # Raise an exception for bad HTTP status codes
        data = response.json()

        # Παίρνουμε την τρέχουσα θερμοκρασία και την ώρα της μέτρησης από το API
        current_temp = data["current"]["temperature_2m"]
        api_time_raw = data["current"]["time"] 
        api_time_clean = api_time_raw.replace("T", " ")

        # Get the current hour (0-23) to use as the starting index for forecasts
        current_hour = datetime.now().hour

        # Extract the hourly data arrays
        hourly_probs = data["hourly"]["precipitation_probability"]
        hourly_rain = data["hourly"]["rain"]

        # Slice the arrays to get only the next 12 hours
        next_12h_probs = hourly_probs[current_hour : current_hour + 12]
        next_12h_rain = hourly_rain[current_hour : current_hour + 12]

        # Calculate final metrics
        max_rain_prob = max(next_12h_probs)
        total_rain_mm = round(sum(next_12h_rain), 2)

        sunrise = data["daily"]["sunrise"][0]
        sunset = data["daily"]["sunset"][0]

        print(f"[WEATHER] Ώρα Μέτρησης (API): {api_time_clean} | Τρέχουσα Θερμοκρασία: {current_temp}°C")
        print(f"[WEATHER] Πρόβλεψη 12h -> Βροχή: {total_rain_mm}mm, Πιθανότητα: {max_rain_prob}%")

        # Format the data into InfluxDB Line Protocol
        # ΔΙΟΡΘΩΣΗ ΕΔΩ: Αλλάξαμε το "temp" σε "temperature" για να το διαβάζει ο Εγκέφαλος!
        line = (
            f"weather_forecast,team={TEAM} "
            f"temperature={current_temp},rain_12h={total_rain_mm},rain_prob_12h={max_rain_prob},"
            f"sunrise=\"{sunrise}\",sunset=\"{sunset}\""
        )
        return line

    except Exception as e:
        print(f"[ERROR] Failed to fetch weather data: {e}")
        return None

# --- 3. INFLUXDB DATABASE FUNCTION ---
def send_to_influxdb(line_protocol: str):
    """Sends the formatted Line Protocol string to InfluxDB via HTTP POST."""
    url = f"{INFLUXDB_URL}/write"
    params = {"db": DB_NAME}
    auth = HTTPBasicAuth(DB_USERNAME, DB_PASSWORD)
    
    try:
        response = requests.post(url, params=params, auth=auth, data=line_protocol, timeout=5)
        if response.status_code == 204:
            print("[DATABASE] Weather data written successfully.")
        else:
            print(f"[ERROR] InfluxDB returned status {response.status_code}: {response.text}")
    except Exception as e:
        print(f"[ERROR] Could not connect to InfluxDB: {e}")

# --- 4. MAIN LOOP ---
if __name__ == "__main__":
    print("[SYSTEM] Starting Weather Fetcher Node...")
    
    while True:
        print(f"\n{'='*50}\n[SYSTEM] Fetching new weather data...")
 
        # 1. Fetch and process weather
        weather_data = fetch_weather()

        # 2. If successful, push to database
        if weather_data:
            send_to_influxdb(weather_data)

        # 3. Sleep until the next cycle
        print(f"[SYSTEM] Sleeping for {FETCH_INTERVAL // 60} minutes...")
        time.sleep(FETCH_INTERVAL)
