import os
import json
import sys
import time
import datetime as dt
import requests

LAT = -33.154
LON = 18.660
TZ = "Africa/Johannesburg"

OUT_JSON = "docs/data.json"

def die(msg):
    print(msg, flush=True)
    sys.exit(1)

def deg_to_compass(deg):
    if deg is None:
        return "?"
    dirs = ["N","NE","E","SE","S","SW","W","NW"]
    ix = int((deg + 22.5) // 45) % 8
    return dirs[ix]

def safe_get(url, params=None, tries=4, timeout=20):
    last = None
    for i in range(tries):
        try:
            r = requests.get(url, params=params, timeout=timeout, headers={"User-Agent":"ruanweer-bot/1.0"})
            r.raise_for_status()
            return r
        except requests.exceptions.SSLError as e:
            # Soms gooi Open-Meteo/GitHub runner 'UNEXPECTED_EOF' — retry help gewoonlik
            last = e
            time.sleep(2 + i*2)
        except Exception as e:
            last = e
            time.sleep(2 + i*2)
    raise last

def send_telegram(token, chat_id, text):
    if not token or not chat_id:
        print("Telegram secrets missing (TELEGRAM_TOKEN / TELEGRAM_CHAT_ID). Skipping Telegram.")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }

    try:
        r = safe_get(url, params=payload, tries=3, timeout=20)
        # Telegram sendMessage is GET/POST; GET works with params, but we used GET helper.
        # If you prefer POST, can switch. This works fine.
        j = r.json()
        ok = bool(j.get("ok"))
        print("Telegram response ok:", ok)
        if not ok:
            print("Telegram error:", j)
        return ok
    except Exception as e:
        print("Telegram send failed:", repr(e))
        return False

def main():
    now_local = dt.datetime.now(dt.timezone.utc).astimezone(dt.timezone(dt.timedelta(hours=2)))
    updated_at = now_local.strftime("%Y-%m-%d %H:%M")

    # Open-Meteo daily forecast (today)
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": LAT,
        "longitude": LON,
        "timezone": TZ,
        "forecast_days": 1,
        "daily": ",".join([
            "temperature_2m_min",
            "temperature_2m_max",
            "precipitation_sum",
            "precipitation_probability_max",
            "windspeed_10m_max",
            "winddirection_10m_dominant",
            "uv_index_max"
        ])
    }

    r = safe_get(url, params=params, tries=5, timeout=25)
    data = r.json()

    daily = data.get("daily", {})
    def dget(key, default=None):
        arr = daily.get(key)
        if isinstance(arr, list) and arr:
            return arr[0]
        return default

    tmin = dget("temperature_2m_min")
    tmax = dget("temperature_2m_max")
    rain_mm = dget("precipitation_sum", 0.0)
    rain_p = dget("precipitation_probability_max", 0)
    wind_kmh = dget("windspeed_10m_max")
    wind_deg = dget("winddirection_10m_dominant")
    uv = dget("uv_index_max")

    wind_dir = deg_to_compass(wind_deg)

    # Message block for site + telegram
    lines = []
    lines.append("🌤️ Weer vir vandag:\n")
    if tmin is not None and tmax is not None:
        lines.append(f"🌡️  Min: {tmin:.1f}°C")
        lines.append(f"🌡️  Max: {tmax:.1f}°C\n")
    if rain_p is not None:
        lines.append(f"🌧️  Reën kans: {int(rain_p)}%")
    if rain_mm is not None:
        lines.append(f"🌧️  Reën totaal: {float(rain_mm):.1f} mm\n")
    if wind_kmh is not None:
        lines.append(f"💨 Wind: {float(wind_kmh):.1f} km/h {wind_dir}")
    if uv is not None:
        lines.append(f"🔆 UV Index: {float(uv):.2f}")

    msg = "\n".join(lines).strip() + "\n"

    out = {
        "updated_at": updated_at,
        "message": msg
    }

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print("Wrote:", OUT_JSON)

    # Telegram
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    # Debug (help as dit nie stuur nie)
    print("TOKEN set:", bool(token))
    print("CHAT_ID set:", bool(chat_id))

    # Net om mooi te format in Telegram:
    tele_text = (
        f"<b>Ruan Weer Stasie</b>\n"
        f"<i>Laas opgedateer:</i> {updated_at}\n\n"
        + msg
    )

    send_telegram(token, chat_id, tele_text)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        die(f"ERROR: {repr(e)}")
