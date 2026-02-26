import os
import sys
import json
import requests
from datetime import datetime

# Moorreesburg approx coords
LAT = -33.154
LON = 18.660

def die(msg: str, code: int = 1):
    print(msg)
    sys.exit(code)

def get_forecast():
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": LAT,
        "longitude": LON,
        "timezone": "Africa/Johannesburg",
        "hourly": "precipitation_probability,precipitation,temperature_2m",
        "forecast_days": 1,
    }
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()

def build_message(data):
    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    pops = hourly.get("precipitation_probability", [])
    mm = hourly.get("precipitation", [])
    temps = hourly.get("temperature_2m", [])

    if not times:
        return "Geen data ontvang vir vandag nie."

    # Simple summary
    max_pop = max(pops) if pops else 0
    total_mm = sum(mm) if mm else 0.0
    tmin = min(temps) if temps else None
    tmax = max(temps) if temps else None

    # Pick rain windows: show hours where pop>=50% OR mm>=0.2
    lines = []
    for t, p, r in zip(times, pops, mm):
        # t format "YYYY-MM-DDTHH:MM"
        hour = int(t.split("T")[1].split(":")[0])
        if p >= 50 or r >= 0.2:
            lines.append(f"{hour:02d}:00  {p:>3.0f}% | {r:>4.1f}mm")

    hourly_block = "\n".join(lines) if lines else "Geen groot reën venster vandag."

    today = times[0].split("T")[0]
    parts = []
    parts.append(f"🌦️ Moorreesburg • {today}")
    if tmin is not None and tmax is not None:
        parts.append(f"🌡️ Temp: {tmin:.0f}°C – {tmax:.0f}°C")
    parts.append(f"🌧️ Maks kans: {max_pop:.0f}% | Tot reën: {total_mm:.1f}mm")
    parts.append("")
    parts.append("⏱️ Reën vensters:")
    parts.append(hourly_block)

    return "\n".join(parts)

def send_telegram(text: str):
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        die("Missing TELEGRAM_TOKEN or TELEGRAM_CHAT_ID env vars (GitHub Secrets).")

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }
    r = requests.post(url, data=payload, timeout=30)
    # Print Telegram response for debugging
    print("Telegram status:", r.status_code)
    print("Telegram body:", r.text)

    try:
        j = r.json()
    except Exception:
        die("Telegram response was not JSON. See body above.")

    if not j.get("ok"):
        die(f
