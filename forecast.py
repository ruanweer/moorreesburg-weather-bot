import os
import json
import datetime as dt
import requests

# --- Stel jou plek ---
LAT = -32.808   # Paternoster (verander as jy wil)
LON = 17.893

TZ = "Africa/Johannesburg"

OUT_FILE = "docs/data.json"

def deg_to_compass(deg):
    if deg is None:
        return "?"
    dirs = ["N","NE","E","SE","S","SW","W","NW"]
    ix = int((deg + 22.5) // 45) % 8
    return dirs[ix]

def now_local_iso():
    # GitHub runner is UTC; ons skryf net 'n netjiese string
    return dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

def fetch_open_meteo():
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": LAT,
        "longitude": LON,
        "timezone": TZ,
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m",
        "daily": "temperature_2m_min,temperature_2m_max,precipitation_sum,precipitation_probability_max,uv_index_max,sunrise,sunset,wind_speed_10m_max,wind_direction_10m_dominant",
        "forecast_days": 7
    }
    # kort timeout help teen hang
    r = requests.get(url, params=params, timeout=25)
    r.raise_for_status()
    return r.json()

def build_message(j):
    d = j.get("daily", {})
    # vandag = index 0
    tmin = d["temperature_2m_min"][0]
    tmax = d["temperature_2m_max"][0]
    rain_p = d["precipitation_probability_max"][0]
    rain_mm = d["precipitation_sum"][0]
    uv = d["uv_index_max"][0]
    w = d["wind_speed_10m_max"][0]
    wdir = deg_to_compass(d["wind_direction_10m_dominant"][0])
    sunrise = d["sunrise"][0][-5:]  # "HH:MM"
    sunset = d["sunset"][0][-5:]

    lines = []
    lines.append("⛅ Weer vir vandag:")
    lines.append(f"🌅 Son op: {sunrise}   🌇 Son sak: {sunset}")
    lines.append("")
    lines.append(f"🌡️ Min: {tmin:.1f}°C")
    lines.append(f"🌡️ Max: {tmax:.1f}°C")
    lines.append("")
    lines.append(f"🌧️ Reën kans: {rain_p:.0f}%")
    lines.append(f"🌧️ Reën totaal: {rain_mm:.1f} mm")
    lines.append("")
    lines.append(f"💨 Wind: {w:.1f} km/h {wdir}")
    lines.append(f"🕶️ UV Index: {uv:.2f}")

    return "\n".join(lines)

def write_dashboard_json(j, message):
    d = j.get("daily", {})
    daily_list = []
    for i in range(len(d["time"])):
        date = d["time"][i]
        daily_list.append({
            "date": date,
            "tmin": float(d["temperature_2m_min"][i]),
            "tmax": float(d["temperature_2m_max"][i]),
            "rain_prob": float(d["precipitation_probability_max"][i]),
            "rain_mm": float(d["precipitation_sum"][i]),
            "uv": float(d["uv_index_max"][i]),
            "sunrise": d["sunrise"][i],
            "sunset": d["sunset"][i],
            "wind_max": float(d["wind_speed_10m_max"][i]),
            "wind_dir": deg_to_compass(d["wind_direction_10m_dominant"][i]),
        })

    out = {
        "updated_at": now_local_iso(),
        "message": message,
        "place": {"lat": LAT, "lon": LON, "tz": TZ},
        "daily": daily_list
    }

    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

def send_telegram(text):
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    # As jy nog nie secrets gesit het nie, moenie crash nie
    if not token or not chat_id:
        print("Telegram secrets missing; skipping Telegram send.")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    r = requests.post(url, json=payload, timeout=20)
    r.raise_for_status()

def main():
    j = fetch_open_meteo()
    msg = build_message(j)
    write_dashboard_json(j, msg)

    # Telegram: jy wil 2x 'n dag stuur — ons beheer dit in YAML met die schedule
    send_telegram(msg)
    print("Done.")

if __name__ == "__main__":
    main()
