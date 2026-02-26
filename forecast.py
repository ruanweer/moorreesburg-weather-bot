import os
import sys
import math
import requests

# Moorreesburg approx coords
LAT = -33.154
LON = 18.660


def die(msg):
    print(msg, flush=True)
    sys.exit(1)


def deg_to_compass(deg):
    # 0=N, 90=E, 180=S, 270=W
    if deg is None:
        return "?"
    dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    ix = int((deg + 22.5) // 45) % 8
    return dirs[ix]


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
    winds = hourly.get("windspeed_10m", [])
    wind_dirs = hourly.get("winddirection_10m", [])
    uvs = hourly.get("uv_index", [])

    if not times:
        return None, "Geen data ontvang vir vandag nie."

    # Summaries
    max_pop = max(pops) if pops else 0
    total_mm = sum(mm) if mm else 0.0
    tmin = min(temps) if temps else None
    tmax = max(temps) if temps else None
    max_wind = max(winds) if winds else 0
    max_uv = max(uvs) if uvs else 0

    # Wind direction at strongest wind hour
    wind_dir_text = "?"
    if winds and wind_dirs and len(winds) == len(wind_dirs):
        idx = max(range(len(winds)), key=lambda i: winds[i] if winds[i] is not None else -1)
        wind_dir_text = deg_to_compass(wind_dirs[idx])

    # Rain windows (hours)
    lines = []
    for t, p, r in zip(times, pops, mm):
        hour = int(t.split("T")[1].split(":")[0])
        if (p is not None and p >= 50) or (r is not None and r >= 0.2):
            lines.append(f"{hour:02d}:00  {p:>3.0f}% | {r:>4.1f}mm")

    rain_block = "\n".join(lines) if lines else "Geen groot reën venster vandag."

    msg = "🌦️ *Moorreesburg* (vandag)\n"
    if tmin is not None and tmax is not None:
        msg += f"🌡️ Temp: *{tmin:.0f}°C – {tmax:.0f}°C*\n"
    msg += f"🌧️ Reën: maks kans *{max_pop:.0f}%* | totaal *{total_mm:.1f}mm*\n"
    msg += f"💨 Wind: maks *{max_wind:.0f} km/h* ({wind_dir_text})\n"
    msg += f"🧴 UV: maks *{max_uv:.1f}*\n\n"
    msg += "⏱️ *Reën vensters:*\n"
    msg += rain_block

    summary = {
        "total_mm": float(total_mm),
        "max_pop": float(max_pop),
        "max_wind": float(max_wind),
        "max_uv": float(max_uv),
    }
    return summary, msg


def should_send(summary):
    """
    Boss mode:
      - If ALERT_ONLY=1 -> only send when total rain >= RAIN_ALERT_MM
      - Otherwise always send.
    """
    alert_only = os.getenv("ALERT_ONLY", "0").strip() == "1"
    if not alert_only:
        return True

    try:
        rain_alert_mm = float(os.getenv("RAIN_ALERT_MM", "2.0"))
    except Exception:
        rain_alert_mm = 2.0

    return summary["total_mm"] >= rain_alert_mm


def send_telegram(text):
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        die("Missing TELEGRAM_TOKEN or TELEGRAM_CHAT_ID")

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }

    r = requests.post(url, data=payload, timeout=30)
    print("Telegram status:", r.status_code, flush=True)
    print("Telegram body:", r.text, flush=True)

    try:
        j = r.json()
    except Exception:
        die("Telegram response was not JSON")

    if not j.get("ok"):
        die(f"Telegram error: {j}")


def main():
    print("Starting forecast...", flush=True)
    data = get_forecast()
    summary, msg = build_message(data)

    if summary is None:
        die(msg)

    if should_send(summary):
        send_telegram(msg)
        print("Sent ✅", flush=True)
    else:
        print("No alert needed (ALERT_ONLY=1 and rain below threshold).", flush=True)

    print("Done.", flush=True)


if __name__ == "__main__":
    main()
