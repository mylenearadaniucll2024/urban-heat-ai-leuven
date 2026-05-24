"""
Fetch Netatmo citizen-science temperature readings for Belgian cities.

Registration (free):
  1. Go to https://dev.netatmo.com/  →  Sign up / Log in
  2. Create an app  →  copy CLIENT_ID and CLIENT_SECRET
  3. Add to .env:
       NETATMO_CLIENT_ID=your_id
       NETATMO_CLIENT_SECRET=your_secret

Usage:
    python scripts/fetch_netatmo.py

Output:
    data/raw/netatmo/<city>/sensors_<YYYY-MM-DD>.csv
    Columns: station_id, latitude, longitude, temperature_c, humidity, timestamp

Notes:
  - getpublicdata returns the *latest* readings from all public stations in a bbox.
  - Run once per day (or per Sentinel-2 scene date) to build up a time series.
  - Netatmo data is noisy (unvalidated citizen sensors) — filter outliers.
"""

import os, json, time
from pathlib import Path
from datetime import datetime
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

CLIENT_ID     = os.getenv("NETATMO_CLIENT_ID",     "YOUR_CLIENT_ID")
CLIENT_SECRET = os.getenv("NETATMO_CLIENT_SECRET", "YOUR_CLIENT_SECRET")

TOKEN_URL    = "https://api.netatmo.com/oauth2/token"
PUBLIC_URL   = "https://api.netatmo.com/api/getpublicdata"

OUT_BASE = Path("data/raw/netatmo")

CITIES = {
    "Leuven":   {"lat_ne": 50.94, "lon_ne": 4.78, "lat_sw": 50.84, "lon_sw": 4.63},
    "Liège":    {"lat_ne": 50.71, "lon_ne": 5.68, "lat_sw": 50.59, "lon_sw": 5.46},
    "Brussels": {"lat_ne": 50.91, "lon_ne": 4.47, "lat_sw": 50.79, "lon_sw": 4.27},
    "Ghent":    {"lat_ne": 51.11, "lon_ne": 3.81, "lat_sw": 50.99, "lon_sw": 3.61},
    "Antwerp":  {"lat_ne": 51.28, "lon_ne": 4.52, "lat_sw": 51.16, "lon_sw": 4.32},
}

TEMP_MIN, TEMP_MAX = -10, 50   # plausibility range °C
HUMIDITY_MAX       = 100


def get_token():
    r = requests.post(TOKEN_URL, data={
        "grant_type":    "client_credentials",
        "client_id":     CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope":         "read_station",
    })
    r.raise_for_status()
    return r.json()["access_token"]


def fetch_city(city_name: str, bbox: dict, token: str) -> pd.DataFrame:
    params = {
        "lat_ne": bbox["lat_ne"],
        "lon_ne": bbox["lon_ne"],
        "lat_sw": bbox["lat_sw"],
        "lon_sw": bbox["lon_sw"],
        "filter": True,   # only return stations with recent data
    }
    r = requests.get(
        PUBLIC_URL,
        params=params,
        headers={"Authorization": f"Bearer {token}"},
    )
    r.raise_for_status()
    stations = r.json().get("body", [])

    rows = []
    for st in stations:
        place = st.get("place", {})
        lat   = place.get("location", [None, None])[1]
        lon   = place.get("location", [None, None])[0]
        if lat is None or lon is None:
            continue

        for module in st.get("measures", {}).values():
            types = module.get("type", [])
            res   = module.get("res", {})
            if not res:
                continue
            # res is {timestamp_str: [val, val, ...]}
            for ts_str, vals in res.items():
                for field, val in zip(types, vals):
                    if field == "temperature":
                        if TEMP_MIN <= val <= TEMP_MAX:
                            rows.append({
                                "station_id":    st.get("_id", ""),
                                "latitude":      lat,
                                "longitude":     lon,
                                "temperature_c": val,
                                "timestamp":     int(ts_str),
                            })
                    elif field == "humidity":
                        if 0 <= val <= HUMIDITY_MAX:
                            # attach humidity to the last row if same station
                            if rows and rows[-1]["station_id"] == st.get("_id", ""):
                                rows[-1]["humidity"] = val

    return pd.DataFrame(rows)


def main():
    if CLIENT_ID == "YOUR_CLIENT_ID":
        print("ERROR: set NETATMO_CLIENT_ID and NETATMO_CLIENT_SECRET in .env")
        print("  Register at https://dev.netatmo.com/  →  Create app")
        return

    today = datetime.utcnow().strftime("%Y-%m-%d")
    print(f"Fetching Netatmo data for {today}...")
    token = get_token()
    print("Token OK.\n")

    for city, bbox in CITIES.items():
        print(f"  {city}...")
        df = fetch_city(city, bbox, token)
        if df.empty:
            print(f"    No data returned for {city}")
            continue

        out_dir = OUT_BASE / city.lower().replace("è", "e")
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"sensors_{today}.csv"
        df.to_csv(out_path, index=False)
        print(f"    {len(df)} readings → {out_path}")

        time.sleep(1)   # be polite to the API

    print("\nDone. Load in notebook with:")
    print("  pd.read_csv('data/raw/netatmo/<city>/sensors_<date>.csv')")


if __name__ == "__main__":
    main()
