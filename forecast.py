import os
import json
import math
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

# ====== STEL JOU PLEK HIER ======
LAT = -33.154
LON = 18.660
TZ = "Africa/Johannesburg"  # SA tyd

OUT_PATH = "docs/data.json"


def deg_to_compass(deg):
    if deg is None or (isinstance(deg, float) and math.isnan(deg)):
        return "?"
    dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    ix = int((deg + 22.5) // 45) % 8
    return dirs[ix]


def fmt_time_iso_to_hm(iso_str):
    # Open-Meteo gee bv "2026-02-26T06:31"
    if not iso_str:
        return "--:--"
    try:
        return iso_str.split("T")[1][:5]
    except Exception:
        return "--:--"


def safe_get(d, *keys, default=None):
    cur = d
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur


def telegram_send(text: str):
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID".replace("_", ""))  # just in case
    # In jou workflow gebruik jy TELEGRAM_CHAT_ID, so dis reg.
    if not token or not chat_id:
        print("Telegram secrets nie gestel nie - skip.")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    r = requests.post(url, json={"chat_id": chat_id, "text": text})
    print("Telegram status:", r.status_code)
    if r.status_code >= 300:
        print(r.text)


def main():
    # --- Open-Meteo: daily + minutely_15 (vir volgende 30 min) ---
    params = {
        "latitude": LAT,
        "longitude": LON,
        "timezone": TZ,

        # 7 dae daily
        "daily": ",".join([
            "temperature_2m_min",
            "temperature_2m_max",
            "precipitation_probability_max",
            "precipitation_sum",
            "windspeed_10m_max",
            "winddirection_10m_dominant",
            "uv_index_max",
            "sunrise",
            "sunset",
        ]),
        "forecast_days": 7,

        # minutely_15: vir reën kans in volgende 30 min (2 x 15min blokke)
        "minutely_15": ",".join([
            "precipitation_probability",
            "precipitation",
        ]),
        "forecast_minutes": 60,  # genoeg vir volgende 30min + buffer
    }

    url = "https://api.open-meteo.com/v1/forecast"
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()

    now = datetime.now(ZoneInfo(TZ))
    updated_at = now.strftime("%Y-%m-%d %H:%M")  # SA tyd

    # --- Vandag (dag 0) ---
    daily = data.get("daily", {})
    day0_min = safe_get(daily, "temperature_2m_min", default=[None])[0]
    day0_max = safe_get(daily, "temperature_2m_max", default=[None])[0]
    day0_rain_prob = safe_get(daily, "precipitation_probability_max", default=[None])[0]
    day0_rain_sum = safe_get(daily, "precipitation_sum", default=[None])[0]
    day0_wind = safe_get(daily, "windspeed_10m_max", default=[None])[0]
    day0_wdir = safe_get(daily, "winddirection_10m_dominant", default=[None])[0]
    day0_uv = safe_get(daily, "uv_index_max", default=[None])[0]
    sunrise0 = safe_get(daily, "sunrise", default=[""])[0]
    sunset0 = safe_get(daily, "sunset", default=[""])[0]

    # --- Volgende 30 minute reën kans ---
    # Neem eerste 2 intervals van minutely_15 precipitation_probability (2x15min = 30min)
    min15 = data.get("minutely_15", {})
    probs = min15.get("precipitation_probability", []) or []
    precs = min15.get("precipitation", []) or []

    next30_prob = None
    next30_mm = None
    if len(probs) >= 2:
        # veiligste: vat die MAX kans in die volgende 30 min
        next30_prob = max([p for p in probs[:2] if p is not None])
    elif len(probs) == 1:
        next30_prob = probs[0]

    if len(precs) >= 2:
        # mm in volgende 30min: som eerste 2 15min blokke
        vals = [x for x in precs[:2] if x is not None]
        next30_mm = round(sum(vals), 2) if vals else 0.0
    elif len(precs) == 1:
        next30_mm = round(precs[0] or 0.0, 2)

    # --- 7 dae bou ---
    dates = daily.get("time", []) or []
    tmin = daily.get("temperature_2m_min", []) or []
    tmax = daily.get("temperature_2m_max", []) or []
    pmax = daily.get("precipitation_probability_max", []) or []
    psum = daily.get("precipitation_sum", []) or []
    wmax = daily.get("windspeed_10m_max", []) or []
    wdir = daily.get("winddirection_10m_dominant", []) or []
    uvmax = daily.get("uv_index_max", []) or []
    sunr = daily.get("sunrise", []) or []
    suns = daily.get("sunset", []) or []

    week = []
    for i in range(min(7, len(dates))):
        week.append({
            "date": dates[i],
            "min": tmin[i] if i < len(tmin) else None,
            "max": tmax[i] if i < len(tmax) else None,
            "rain_prob": pmax[i] if i < len(pmax) else None,
            "rain_mm": psum[i] if i < len(psum) else None,
            "wind_kmh": wmax[i] if i < len(wmax) else None,
            "wind_dir": deg_to_compass(wdir[i]) if i < len(wdir) else "?",
            "uv": uvmax[i] if i < len(uvmax) else None,
            "sunrise": fmt_time_iso_to_hm(sunr[i]) if i < len(sunr) else "--:--",
            "sunset": fmt_time_iso_to_hm(suns[i]) if i < len(suns) else "--:--",
        })

    # --- Dashboard message (vandag) ---
    sunrise_hm = fmt_time_iso_to_hm(sunrise0)
    sunset_hm = fmt_time_iso_to_hm(sunset0)
    wind_dir = deg_to_compass(day0_wdir)

    lines = []
    lines.append("🌤️ Weer vir vandag")
    lines.append("")
    lines.append(f"🌅 Son op: {sunrise_hm}")
    lines.append(f"🌇 Son sak: {sunset_hm}")
    lines.append("")
    lines.append(f"🌡️ Min: {day0_min:.1f}°C" if day0_min is not None else "🌡️ Min: -")
    lines.append(f"🌡️ Max: {day0_max:.1f}°C" if day0_max is not None else "🌡️ Max: -")
    lines.append("")
    lines.append(f"🌧️ Reën kans: {day0_rain_prob:.0f}%" if day0_rain_prob is not None else "🌧️ Reën kans: -")
    lines.append(f"🌧️ Reën totaal: {day0_rain_sum:.1f} mm" if day0_rain_sum is not None else "🌧️ Reën totaal: -")

    # 👉 volgende 30 min reën kans
    if next30_prob is not None:
        extra = f"⏱️ Reën kans volgende 30 min: {next30_prob:.0f}%"
        if next30_mm is not None:
            extra += f" ({next30_mm:.2f} mm)"
        lines.append("")
        lines.append(extra)

    lines.append("")
    lines.append(f"💨 Wind: {day0_wind:.1f} km/h {wind_dir}" if day0_wind is not None else "💨 Wind: -")
    lines.append(f"☀️ UV Index: {day0_uv:.2f}" if day0_uv is not None else "☀️ UV Index: -")

    message = "\n".join(lines)

    payload = {
        "updated_at": updated_at,
        "message": message,
        "next30_rain_prob": next30_prob,
        "next30_rain_mm": next30_mm,
        "week": week,
    }

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print("Wrote", OUT_PATH)

    # Telegram (optional)
    # Jy kan later filter op “net 2x per dag” – vir nou stuur hy elke run as secrets daar is.
    telegram_send(f"Ruan Weer Stasie\nLaas opgedateer: {updated_at}\n\n{message}")


if __name__ == "__main__":
    main()
