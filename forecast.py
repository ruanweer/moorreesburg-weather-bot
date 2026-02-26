import os
import sys
import requests

LAT = -33.154
LON = 18.660


def die(msg):
    print(msg)
    sys.exit(1)


def get_forecast():
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": LAT,
        "longitude": LON,
        "timezone": "Africa/Johannesburg",
        "hourly": "precipitation_probability,precipitation,temperature_2m,windspeed_10m",
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
    winds = hourly.get("windspeed_10m", [])

    if not times:
        return "Geen data ontvang vir vandag nie."

    max_pop = max(pops) if pops else 0
    total_mm = sum(mm) if mm else 0.0
    tmin = min(temps) if temps else None
    tmax = max(temps) if temps else None
    max_wind = max(winds) if winds else 0

    # Reën vensters: ure waar kans >= 50% of reën >= 0.2mm
    lines = []
    for t, p, r in zip(times, pops, mm):
        hour = int(t.split("T")[1].split(":")[0])
        if p >= 50 or r >= 0.2:
            lines.append(f"{hour:02d}:00  {p:.0f}% | {r:.1f}mm")

    hourly_block = "\n".join(lines) if lines else "Geen groot reën venster vandag."

    msg = "🌦️ Moorreesburg\n"

    if tmin is not None and tmax is not None:
        msg += f"🌡️ Temp: {tmin:.0f}°C – {tmax:.0f}°C\n"

    msg += f"🌧️ Maks kans: {max_pop:.0f}% | Tot reën: {total_mm:.1f}mm\n"
    msg += f"💨 Maks wind: {max_wind:.0f} km/h\n\n"

    msg += "⏱️ Reën vensters:\n"
    msg += hourly_block

    return msg


def send_telegram(text):
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        die("Missing TELEGRAM_TOKEN or TELEGRAM_CHAT_ID")

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }

    r = requests.post(url, data=payload, timeout=30)

    print("Telegram status:", r.status_code)
    print("Telegram body:", r.text)

    try:
        j = r.json()
    except Exception:
        die("Telegram response was not JSON")

    if not j.get("ok"):
        die(f"Telegram error: {j}")


def main():
    print("Starting forecast...")
    data = get_forecast()
    msg = build_message(data)
    send_telegram(msg)
    print("Done.")


if __name__ == "__main__":
    main()
