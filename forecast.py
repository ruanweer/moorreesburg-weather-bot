import os
import sys
import json
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import datetime

LAT = -33.154
LON = 18.660


def die(msg):
    print(msg, flush=True)
    sys.exit(1)


def deg_to_compass(deg):
    if deg is None:
        return "?"
    dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    ix = int((deg + 22.5) // 45) % 8
    return dirs[ix]


# ---- Retry Session (fix SSL issues in GitHub) ----
session = requests.Session()
retry = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[500, 502, 503, 504],
)
adapter = HTTPAdapter(max_retries=retry)
session.mount("https://", adapter)


url = (
    "https://api.open-meteo.com/v1/forecast?"
    f"latitude={LAT}&longitude={LON}"
    "&timezone=Africa%2FJohannesburg"
    "&daily=temperature_2m_min,temperature_2m_max,"
    "precipitation_sum,precipitation_probability_max,"
    "windspeed_10m_max,winddirection_10m_dominant,uv_index_max"
    "&forecast_days=1"
)

try:
    r = session.get(url, timeout=20)
    r.raise_for_status()
    data = r.json()
except Exception as e:
    die(f"API error: {e}")


daily = data.get("daily")
if not daily:
    die("No daily data returned")


tmin = daily["temperature_2m_min"][0]
tmax = daily["temperature_2m_max"][0]
rain = daily["precipitation_sum"][0]
rain_prob = daily["precipitation_probability_max"][0]
wind_speed = daily["windspeed_10m_max"][0]
wind_dir = daily["winddirection_10m_dominant"][0]
uv = daily["uv_index_max"][0]

compass = deg_to_compass(wind_dir)

message = (
    f"🌤 Weer vir vandag:\n\n"
    f"🌡 Min: {tmin}°C\n"
    f"🌡 Max: {tmax}°C\n\n"
    f"🌧 Reën kans: {rain_prob}%\n"
    f"🌧 Reën totaal: {rain} mm\n\n"
    f"💨 Wind: {wind_speed} km/h {compass}\n"
    f"☀ UV Index: {uv}"
)

output = {
    "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    "message": message
}

os.makedirs("docs", exist_ok=True)

with open("docs/data.json", "w") as f:
    json.dump(output, f, indent=2)

print("Forecast saved successfully.")
