import time
from datetime import datetime

import requests
from requests.auth import HTTPBasicAuth

# --- CONFIGURATION ---
TEAM = "edge12"

INFLUXDB_URL = "http://194.177.207.38:8086"
DB_NAME = f"{TEAM}_db"
DB_USERNAME = "edge12"
DB_PASSWORD = "team1@#$"

FETCH_INTERVAL = 1800  # 30 minutes

# Volos, Greece
LATITUDE = 39.36
LONGITUDE = 22.94


def parse_open_meteo_datetime(value: str) -> datetime:
    """Parse Open-Meteo ISO timestamps safely, including optional UTC suffixes."""
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def escape_influx_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def fetch_weather():
    """Fetch weather data and return it in InfluxDB line-protocol format."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "current": "temperature_2m",
        "hourly": "temperature_2m,rain,precipitation_probability",
        "daily": "sunrise,sunset",
        "timezone": "auto",
        "past_days": 1,
        "forecast_days": 2,
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        current_temp = float(data["current"]["temperature_2m"])
        current_time = parse_open_meteo_datetime(data["current"]["time"])

        hourly_times = [
            parse_open_meteo_datetime(timestamp)
            for timestamp in data["hourly"]["time"]
        ]

        # Match the API current time to the nearest hourly forecast timestamp.
        # This avoids fragile string slicing and handles valid ISO-8601 variations.
        current_hour_index = min(
            range(len(hourly_times)),
            key=lambda index: abs(
                (hourly_times[index] - current_time).total_seconds()
            ),
        )

        hourly_probs = data["hourly"]["precipitation_probability"]
        hourly_rain = data["hourly"]["rain"]

        next_12h_probs = hourly_probs[current_hour_index: current_hour_index + 12]
        next_12h_rain = hourly_rain[current_hour_index: current_hour_index + 12]

        if not next_12h_probs or not next_12h_rain:
            raise ValueError("Open-Meteo returned insufficient future hourly data.")

        start_past_index = max(0, current_hour_index - 6)
        past_6h_rain = hourly_rain[start_past_index:current_hour_index]

        max_rain_prob = float(max(next_12h_probs))
        total_rain_mm = round(sum(next_12h_rain), 2)
        actual_rain_6h = round(sum(past_6h_rain), 2)

        current_date = current_time.date().isoformat()
        daily_dates = [
            parse_open_meteo_datetime(timestamp).date().isoformat()
            for timestamp in data["daily"]["sunrise"]
        ]

        try:
            daily_index = daily_dates.index(current_date)
        except ValueError:
            daily_index = 0

        sunrise = data["daily"]["sunrise"][daily_index]
        sunset = data["daily"]["sunset"][daily_index]

        print(
            f"[WEATHER] API time: {current_time.isoformat()} | "
            f"Temperature: {current_temp:.1f} C"
        )
        print(f"[WEATHER] Past 6h rain: {actual_rain_6h:.2f} mm")
        print(
            f"[WEATHER] Next 12h rain: {total_rain_mm:.2f} mm | "
            f"Probability: {max_rain_prob:.1f}%"
        )

        return (
            f"weather_forecast,team={TEAM} "
            f"temperature={current_temp},"
            f"rain_12h={total_rain_mm},"
            f"rain_prob_12h={max_rain_prob},"
            f"actual_rain_6h={actual_rain_6h},"
            f"sunrise=\"{escape_influx_string(sunrise)}\","
            f"sunset=\"{escape_influx_string(sunset)}\""
        )

    except (requests.RequestException, KeyError, TypeError, ValueError) as exc:
        print(f"[ERROR] Failed to fetch/process weather data: {exc}")
        return None


def send_to_influxdb(line_protocol: str):
    """Write weather data to local/VPS InfluxDB via HTTP."""
    response = requests.post(
        f"{INFLUXDB_URL}/write",
        params={"db": DB_NAME},
        auth=HTTPBasicAuth(DB_USERNAME, DB_PASSWORD),
        data=line_protocol,
        timeout=5,
    )

    if response.status_code == 204:
        print("[DATABASE] Weather data written successfully.")
    else:
        print(f"[DATABASE] InfluxDB error {response.status_code}: {response.text}")


def main():
    print("[SYSTEM] Starting Weather Fetcher Node...")

    while True:
        print("\n[SYSTEM] Fetching weather data...")

        weather_data = fetch_weather()
        if weather_data:
            try:
                send_to_influxdb(weather_data)
            except requests.RequestException as exc:
                print(f"[DATABASE] Could not connect to InfluxDB: {exc}")

        print("[SYSTEM] Sleeping for 30 minutes...")
        time.sleep(FETCH_INTERVAL)


if __name__ == "__main__":
    main()
