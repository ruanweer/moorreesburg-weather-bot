import os
import sys
import requests

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


def wind_emoji(kmh):
    if kmh is None:
        return "🌬"
    if kmh >= 45:
        return "🌪"
    if kmh >= 20:
        return "💨"
    return "🌬"


def get_forecast():
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": LAT,
        "longitude": LON,
        "timezone": "Africa/Johannesburg",
        "forecast_days": 1,
        "hourly": ",".join([
            "temperature_2m",
            "precipitation_probability",
            "precipitation",
            "windspeed_10m",
            "winddirection_10m",
            "uv_index",
        ]),
        "daily": "sunrise,sunset",
    }

    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def build_message(data):
    hourly = data.get("hourly", {})
    daily = data.get("daily", {})

    times = hourly.get("time", [])
    pops = hourly.get("precipitation_probability", [])
    mm = hourly.get("precipitation", [])
    temps = hourly.get("temperature_2m", [])
    winds = hourly
