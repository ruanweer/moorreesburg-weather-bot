import os
import json
import datetime as dt
import requests

# ----- SETTINGS -----
LAT = -33.154
LON = 18.660
TZ = "Africa/Johannesburg"

OUT_FILE = "docs/data.json"

# --------------------

def deg_to_compass(deg):
    if deg is None:
        return "?"
    dirs = ["N","NE","E","SE","S","SW","W","NW"]
    ix = int((deg + 22.5) // 45) % 8
    return dirs[ix]

def now_local():
    return dt.datetime.utcnow()

def fetch_data():
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": LAT,
        "longitude": LON,
        "timezone": TZ,
        "current": "temperature_2m,wind_speed_10m,wind_direction_10m",
        "daily": "temperature_2m_min,temperature_2m_max,precipitation_sum,precipitation_probability_max,uv_index_max,sunrise,sunset,wind_speed_10m_max,wind_direction_10m_dominant",
        "forecast_days": 7
    }

    r = requests.get(url, params=params, timeout=25)
    r.raise_for_status()
    return r.json()

def build_today_message(data):
    d = data["daily"]

    tmin = d["temperature_2m_min"][0]
    tmax = d["temperature_2m_max"][0]
    rain_prob = d["precipitation_probability_max"][0]
    rain_sum = d["precipitation_sum"][0]
    uv = d["uv_index_max"][0]
    wind = d["wind_speed_10m_max"][0]
    wind_dir = deg_to_compass(d["wind_direction_10m_dominant"][0])

    sunrise = d["sunrise"][0][-5:]
    sunset = d["sunset"][0][-5:]

    lines = []
    lines.append("🌤️ Weer vir vandag")
    lines.append("")
    lines.append(f"🌅 Son op: {sunrise}")
    lines.append(f"🌇 Son sak: {sunset}")
    lines.append("")
    lines.append(f"🌡️ Min: {tmin:.1f}°C")
    lines.append(f"🌡️ Max: {tmax:.1f}°C")
    lines.append("")
    lines.append(f"🌧️ Reën kans: {rain_prob:.0f}%")
    lines.append(f"🌧️ Reën totaal: {rain_sum:.1f} mm")
    lines.append("")
    lines.append(f"💨 Wind: {wind:.1f} km/h {wind_dir}")
    lines.append(f"☀️ UV Index: {uv:.2f}")

    return "\n".join(lines)

def write_json(data, message):
    d = data["daily"]
    daily_list = []

    for i in range(len(d["time"])):
        daily_list.append({
            "date": d["time"][i],
            "tmin": d["temperature_2m_min"][i],
            "tmax": d["temperature_2m_max"][i],
            "rain_prob": d["precipitation_probability_max"][i],
            "rain_mm": d["precipitation_sum"][i],
            "uv": d["uv_index_max"][i],
            "sunrise": d["sunrise"][i],
            "sunset": d["sunset"][i],
            "wind_max": d["wind_speed_10m_max"][i],
            "wind_dir": deg_to_compass(d["wind_direction_10m_dominant"][i]),
        })

    out = {
        "updated_at": now_local().strftime("%Y-%m-%d %H:%M UTC"),
        "message": message,
        "daily": daily_list
    }

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

def send_telegram(text):
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("Telegram secrets missing, skipping.")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }

    r = requests.post(url, json=payload, timeout=20)
    r.raise_for_status()

def main():
    data = fetch_data()
    message = build_today_message(data)

    # Update dashboard (elke run = elke 10 min)
    write_json(data, message)

    # Telegram net 2x per dag
    now = now_local()
    if now.hour in [6, 18] and now.minute < 10:
        send_telegram(message)

    print("Update complete.")

if __name__ == "__main__":
    main()
