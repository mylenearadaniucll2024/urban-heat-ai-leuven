"""
Download Sentinel-2 L2A B04, B08, B11 bands for tile T31UES
from Copernicus Data Space using the OData API.

Usage:
    python scripts/download_t31ues.py

Steps:
  1. Register free account at https://dataspace.copernicus.eu/
  2. Set COPERNICUS_USER and COPERNICUS_PASSWORD below (or as env vars)
  3. Run — the script finds the lowest-cloud-cover scene within ±5 days of
     each target date, downloads B04/B08/B11, and saves to:
       data/raw/sentinel2/T31UES/<date>/B04.jp2  etc.
"""

import os, sys, json, time, zipfile, shutil, io
from pathlib import Path
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv

# Load credentials from .env in project root (one level above scripts/)
load_dotenv(Path(__file__).parent.parent / ".env")

# ── Credentials ────────────────────────────────────────────────────────────────
USER     = os.getenv("COPERNICUS_USER",     "YOUR_EMAIL")
PASSWORD = os.getenv("COPERNICUS_PASSWORD", "YOUR_PASSWORD")

# ── Config ─────────────────────────────────────────────────────────────────────
TILE          = "31UES"   # Copernicus catalogue stores tileId without the leading T
BANDS         = ["B04", "B08", "B11"]
WINDOW_DAYS   = 5          # search ±5 days around each target date
MAX_CLOUD     = 20         # skip scenes with >20% cloud cover
OUT_BASE      = Path("data/raw/sentinel2/T31UES")
TOKEN_URL     = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
SEARCH_URL    = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
DOWNLOAD_URL  = "https://zipper.dataspace.copernicus.eu/odata/v1/Products"

TARGET_DATES = [
    "2023-08-10", "2023-08-20", "2023-08-23",
    "2024-07-30",
    "2025-07-02", "2025-08-11", "2025-08-12",
]


def get_token():
    r = requests.post(TOKEN_URL, data={
        "grant_type":    "password",
        "username":      USER,
        "password":      PASSWORD,
        "client_id":     "cdse-public",
    })
    r.raise_for_status()
    return r.json()["access_token"]


def search_scenes(target_date: str, token: str):
    d = datetime.strptime(target_date, "%Y-%m-%d")
    d_from = (d - timedelta(days=WINDOW_DAYS)).strftime("%Y-%m-%d")
    d_to   = (d + timedelta(days=WINDOW_DAYS)).strftime("%Y-%m-%d")

    # Build URL manually — requests.get(params=…) encodes $filter → %24filter,
    # which the OData API rejects as 400.  $orderby with any() is also invalid
    # in OData; sort by cloudCover client-side instead.
    filt = (
        f"Collection/Name eq 'SENTINEL-2'"
        f" and Attributes/OData.CSC.StringAttribute/any(att:"
        f"att/Name eq 'tileId' and att/OData.CSC.StringAttribute/Value eq '{TILE}')"
        f" and Attributes/OData.CSC.StringAttribute/any(att:"
        f"att/Name eq 'productType' and att/OData.CSC.StringAttribute/Value eq 'S2MSI2A')"
        f" and ContentDate/Start gt {d_from}T00:00:00.000Z"
        f" and ContentDate/Start lt {d_to}T23:59:59.000Z"
    )
    url = (
        f"{SEARCH_URL}"
        f"?$filter={requests.utils.quote(filt, safe='')}"
        f"&$top=20"
        f"&$expand=Attributes"
    )
    r = requests.get(url, headers={"Authorization": f"Bearer {token}"})
    r.raise_for_status()
    scenes = r.json().get("value", [])
    # Sort ascending by cloudCover (client-side — OData any() is invalid in $orderby)
    def _cloud(s):
        return next(
            (a["Value"] for a in s.get("Attributes", []) if a.get("Name") == "cloudCover"),
            999
        )
    return sorted(scenes, key=_cloud)


def pick_best(scenes, target_date):
    for s in scenes:
        cloud = next(
            (a["Value"] for a in s.get("Attributes", [])
             if a.get("Name") == "cloudCover"),
            999
        )
        acq = s["ContentDate"]["Start"][:10]
        if cloud <= MAX_CLOUD:
            return s["Id"], acq, cloud
    return None, None, None


def download_bands(product_id: str, acq_date: str, token: str):
    out_dir = OUT_BASE / acq_date
    out_dir.mkdir(parents=True, exist_ok=True)

    # Check if already downloaded
    if all((out_dir / f"{b}.jp2").exists() for b in BANDS):
        print(f"  Already downloaded: {acq_date}")
        return

    # Download full product as zip (Copernicus zips on the fly)
    url  = f"{DOWNLOAD_URL}({product_id})/$value"
    head = {"Authorization": f"Bearer {token}"}

    print(f"  Downloading {acq_date} (product {product_id[:8]}...)...")
    r = requests.get(url, headers=head, stream=True)
    r.raise_for_status()

    data = io.BytesIO()
    total = 0
    for chunk in r.iter_content(chunk_size=1024 * 1024):
        data.write(chunk)
        total += len(chunk)
        print(f"    {total / 1e6:.0f} MB received...", end="\r")
    print()

    # Extract only B04, B08, B11 from the zip
    data.seek(0)
    with zipfile.ZipFile(data) as zf:
        for name in zf.namelist():
            for band in BANDS:
                # Sentinel-2 L2A band files match pattern like:
                # .../GRANULE/.../IMG_DATA/R10m/T31UES_..._B04_10m.jp2
                # .../GRANULE/.../IMG_DATA/R20m/T31UES_..._B11_20m.jp2
                if f"_{band}_" in name and name.endswith(".jp2"):
                    dest = out_dir / f"{band}.jp2"
                    if not dest.exists():
                        print(f"  Extracting {name.split('/')[-1]} -> {band}.jp2")
                        dest.write_bytes(zf.read(name))

    extracted = [b for b in BANDS if (out_dir / f"{b}.jp2").exists()]
    print(f"  Done: {acq_date} — {len(extracted)}/{len(BANDS)} bands saved")


def main():
    if USER == "YOUR_EMAIL":
        print("ERROR: set COPERNICUS_USER and COPERNICUS_PASSWORD environment variables")
        print("  Windows PowerShell:  $env:COPERNICUS_USER='you@email.com'")
        print("                       $env:COPERNICUS_PASSWORD='yourpassword'")
        sys.exit(1)

    print(f"Authenticating as {USER}...")
    token = get_token()
    print("Token OK.\n")

    for target in TARGET_DATES:
        out_dir = OUT_BASE / target
        if out_dir.exists() and all((out_dir / f"{b}.jp2").exists() for b in BANDS):
            print(f"[{target}] Already complete — skipping")
            continue

        print(f"[{target}] Searching T31UES scenes...")
        scenes = search_scenes(target, token)
        if not scenes:
            print(f"  WARNING: no scenes found within ±{WINDOW_DAYS} days of {target}")
            continue

        product_id, acq_date, cloud = pick_best(scenes, target)
        if product_id is None:
            print(f"  WARNING: all scenes have >{MAX_CLOUD}% cloud for {target}")
            continue

        print(f"  Best scene: acquired {acq_date}, cloud cover {cloud:.1f}%")
        download_bands(product_id, acq_date, token)

        # Refresh token every 2 scenes (tokens expire after ~10 min)
        token = get_token()
        time.sleep(2)

    print("\nAll done. Check data/raw/sentinel2/T31UES/")


if __name__ == "__main__":
    main()
