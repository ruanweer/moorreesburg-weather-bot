#!/usr/bin/env python3
import os
import json
import math
from datetime import datetime
import requests

TIMEZONE = "Africa/Johannesburg"

PLACES = [
    ("Moorreesburg", -33.152, 18.660),
    ("Malmesbury",   -33.460, 18.730),
    ("Piketberg",    -32.903, 18.757),
    ("Porterville",  -33.010, 19.013),
    ("Darling",      -33.378, 18.381),
]

DASHBOARD_JSON_PATH = "docs/data.json"


def deg_to_compass(deg):
    dirs = ["N","NE","E","SE","S","SW","W","NW"]
    if deg is None:
        return "?"
    ix = int((deg + 22.5) // 45) % 8
    return dirs[ix]


def get_weather(lat, lon):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "timezone": TIMEZONE,
        "daily": ",".join([
            "temperature_2m_min",
            "temperature_2m_max",
            "precipitation_sum",
            "precipitation_probability_max",
            "windspeed_10m_max",
            "winddirection_10m_dominant",
            "uv_index_max",
        ]),
        "forecast_days": 1,
    }
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def build_message(name, data):
    daily = data["daily"]

    tmin = daily["temperature_2m_min"][0]
    tmax = daily["temperature_2m_max"][0]
    rain = daily["precipitation_sum"][0]
    pop = daily["precipitation_probability_max"][0]
    wind = daily["windspeed_10m_max"][0]
    wind_dir = daily["winddirection_10m_dominant"][0]
    uv = daily["uv_index_max"][0]

    wind_txt = deg_to_compass(wind_dir)

    return f"""🌤️ {name}

🌡️ Temp: {tmin:.0f}°C – {tmax:.0f}°C
🌧️ Reën: maks kans {pop:.0f}% | totaal {rain:.1f}mm
💨 Wind: maks {wind:.0f} km/h ({wind_txt})
🧴 UV: maks {uv:.1f}
"""


def main():
    messages = []

    for name, lat, lon in PLACES:
        data = get_weather(lat, lon)
        messages.append(build_message(name, data))

    final_text = "\n".join(messages)

    output = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "message": final_text
    }

    os.makedirs("docs", exist_ok=True)

    with open(DASHBOARD_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("Dashboard updated.")


if __name__ == "__main__":
    main()
