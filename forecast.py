import os
import requests
from datetime import datetime

TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "8510087366")

# Moorreesburg
LAT = -33.15388
LON = 18.66031
TIMEZONE = "Africa/Johannesburg"

HOUR_FROM = 6
HOUR_TO = 18

def send(msg: str):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    r = requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=20)
    r.raise_for_status()

def build_message():
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": LAT,
        "longitude": LON,
        "timezone": TIMEZONE,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum,windspeed_10m_max",
        "hourly": "precipitation_probability,precipitation",
        "forecast_days": 1
    }
    data = requests.get(url, params=params, timeout=20).json()

    d = data["daily"]
    date = d["time"][0]
    tmax = d["temperature_2m_max"][0]
    tmin = d["temperature_2m_min"][0]
    popmax = d["precipitation_probability_max"][0]
    rainsum = d["precipitation_sum"][0]
    windmax = d["windspeed_10m_max"][0]

    h = data["hourly"]
    lines =