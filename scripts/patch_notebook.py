"""
Final audit fixes:
  [31] e8198008  — Full Feature Table missing B11 + IMPERVIOUSNESS; "Why only 6?" heading stale
  [36] imd_download_md — stale WCS download warning (WMS works; no download needed)
"""

import json, pathlib, sys
sys.stdout.reconfigure(encoding='utf-8')

NB_PATH = pathlib.Path(
    r'c:\Users\wamy\Desktop\urban-heat-ai\notebooks\heat_monitoring_intelligence.ipynb'
)
nb = json.loads(NB_PATH.read_text(encoding='utf-8'))
cells = nb['cells']


def find(cell_id):
    for i, c in enumerate(cells):
        if c.get('id') == cell_id:
            return i, c
    raise ValueError(f'{cell_id!r} not found')


def patch_md(cell_id, old, new, label):
    idx, c = find(cell_id)
    src = ''.join(c['source'])
    if old not in src:
        print(f'  SKIP [{idx:02d}] {label}: pattern not found')
        return
    src = src.replace(old, new, 1)
    lines = src.splitlines(keepends=True)
    if lines and lines[-1].endswith('\n'):
        lines[-1] = lines[-1].rstrip('\n')
    c['source'] = lines
    print(f'  OK   [{idx:02d}] {label}')


# ── [31] Full Feature Table: add B11 and IMPERVIOUSNESS rows ──────────────────
patch_md(
    'e8198008',
    """| Feature | Source | Temporal | Spatial | Why included |
|---|---|---|---|---|
| `NDVI` | Sentinel-2 B04/B08 | Per scene | Per grid point | Vegetation density — primary cooling driver |
| `NDBI` | Sentinel-2 B08/B11 | Per scene | Per grid point | Built-up intensity — primary warming driver |
| `HUMIDITY` | Leuven.cool | Daily mean | Per station | Affects heat exchange efficiency; high humidity suppresses radiative cooling |
| `ALTITUDE` | STATIONS.csv | Static | Per station | Topographic effect; higher elevation = cooler |
| `wind_ms` | Leuven.cool | Daily mean | Per station | Ventilation disperses heat island; low wind = more accumulation |
| `SOLARRADIATION` | Leuven.cool | Daily mean | Per station | Direct energy input; drives surface heating |

### Why only 6 features?
Features were limited to avoid overfitting on the small dataset (5,575 rows). Including additional correlated features (WINDGUSTMPH is strongly correlated with wind_ms; UV is strongly correlated with SOLARRADIATION) would increase model complexity without adding independent predictive information. The 6 features selected capture the four key UHI drivers: land cover, topography, ventilation, and solar forcing.""",
    """| Feature | Source | Temporal | Spatial | Why included |
|---|---|---|---|---|
| `NDVI` | Sentinel-2 B04/B08 | Per scene | Per grid point | Vegetation density — primary cooling driver |
| `NDBI` | Sentinel-2 B08/B11 | Per scene | Per grid point | Built-up intensity — primary warming driver |
| `B11` | Sentinel-2 B11 (raw) | Per scene | Per grid point | Absolute SWIR emission; captures thermal inertia that NDBI (a ratio) normalises away |
| `HUMIDITY` | Leuven.cool | Daily mean | Per station | Affects heat exchange efficiency; high humidity suppresses radiative cooling |
| `ALTITUDE` | STATIONS.csv | Static | Per station | Topographic effect; higher elevation = cooler |
| `wind_ms` | Leuven.cool | Daily mean | Per station | Ventilation disperses heat island; low wind = more accumulation |
| `SOLARRADIATION` | Leuven.cool | Daily mean | Per station | Direct energy input; drives surface heating |
| `IMPERVIOUSNESS` | EU HRL 2018 (EEA WMS) | Static (2018) | Per grid point | Permanent sealed-surface fraction (0–100 %); separates structural urban form from transient spectral effects |

### Why 8 features?
Features are selected to avoid overfitting on the small dataset (5,575 rows) while covering the four key UHI drivers: **land cover** (NDVI, NDBI, B11, IMPERVIOUSNESS), **topography** (ALTITUDE), **ventilation** (wind_ms), and **solar forcing** (SOLARRADIATION, HUMIDITY). Correlated redundant features are excluded (WINDGUSTMPH ≈ wind_ms; UV ≈ SOLARRADIATION). IMPERVIOUSNESS is added as a static structural feature that complements the scene-date spectral indices with a land-use signal independent of atmospheric conditions.""",
    'Feature table: add B11 + IMPERVIOUSNESS; update Why-N-features section'
)

# ── [36] imd_download_md: remove stale WCS warning ────────────────────────────
patch_md(
    'imd_download_md',
    '\n\n> ⚠ **MANUAL DOWNLOAD MAY BE REQUIRED** — the cell below attempts an EEA WCS auto-download; if that fails, follow the printed instructions.',
    '\n\n**Access method:** No file download or registration required — the cell below queries the EEA ArcGIS ImageServer REST API (`/identify` per station, `/exportImage` per city grid) at runtime.',
    'imd_download_md: replace stale WCS warning with correct WMS note'
)

nb['cells'] = cells
NB_PATH.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding='utf-8')
print('\nAll patches written.')

mc_intro_idx   = next(i for i,c in enumerate(cells) if c.get('id') == 'mc_intro')
mc_predict_idx = next(i for i,c in enumerate(cells) if c.get('id') == 'mc_predict')
print(f'mc_intro at {mc_intro_idx}, mc_predict at {mc_predict_idx}')

# ── New markdown cell ─────────────────────────────────────────────────────────
md_cell = {
    "id": "omw_weather_md",
    "cell_type": "markdown",
    "metadata": {},
    "source": [
        "### 10a. City-Specific Weather Lookup via Open-Meteo\n",
        "\n",
        "The original `predict_city_grid` used **Leuven's median humidity, altitude, wind, and solar radiation** "
        "as weather features for every city — a rough proxy. Brussels sits at ~25 m, Liège at ~70 m; "
        "their humidity and wind patterns differ too.\n",
        "\n",
        "The cell below fetches **actual midday conditions** (10:00–14:00 local, matching Sentinel-2 overpass "
        "time ≈ 11:30) for each city × scene date from the Open-Meteo archive API (free, no key required). "
        "Results are saved to `data/processed/scene_weather_by_city.csv` and used automatically by "
        "`predict_city_grid` via the `scene_weather` DataFrame."
    ]
}

# ── New code cell ─────────────────────────────────────────────────────────────
code_cell = {
    "id": "omw_weather_code",
    "cell_type": "code",
    "execution_count": None,
    "metadata": {},
    "outputs": [],
    "source": [
        "# ── Open-Meteo scene-date weather lookup ──────────────────────────────────────\n",
        "# Fetches midday conditions for each city × Sentinel-2 scene date (free, no key).\n",
        "# Replaces the Leuven-proxy weather values used when predicting non-Leuven cities.\n",
        "\n",
        "import requests, time as _time\n",
        "\n",
        "_OM_URL = 'https://archive-api.open-meteo.com/v1/archive'\n",
        "\n",
        "_SCENE_DATES = {\n",
        "    'Leuven':   {2023: '2023-08-20', 2024: '2024-07-30', 2025: '2025-08-11'},\n",
        "    'Liège':    {2023: '2023-08-20', 2024: '2024-07-30', 2025: '2025-08-11'},\n",
        "    'Brussels': {2023: '2023-08-10', 2024: '2024-07-30', 2025: '2025-08-12'},\n",
        "    'Ghent':    {2023: '2023-08-10', 2024: '2024-07-30', 2025: '2025-08-12'},\n",
        "    'Antwerp':  {2023: '2023-08-10', 2024: '2024-07-30', 2025: '2025-08-12'},\n",
        "}\n",
        "\n",
        "_CITY_COORDS = {\n",
        "    'Leuven':   (50.8798, 4.7005),\n",
        "    'Liège':    (50.6326, 5.5797),\n",
        "    'Brussels': (50.8503, 4.3517),\n",
        "    'Ghent':    (51.0543, 3.7174),\n",
        "    'Antwerp':  (51.2194, 4.4025),\n",
        "}\n",
        "\n",
        "_rows = []\n",
        "print('Fetching scene-date weather from Open-Meteo archive API...')\n",
        "for city, dates in _SCENE_DATES.items():\n",
        "    lat, lon = _CITY_COORDS[city]\n",
        "    for year, date_str in dates.items():\n",
        "        r = requests.get(_OM_URL, params={\n",
        "            'latitude': lat, 'longitude': lon,\n",
        "            'start_date': date_str, 'end_date': date_str,\n",
        "            'hourly': 'relative_humidity_2m,wind_speed_10m,shortwave_radiation',\n",
        "            'wind_speed_unit': 'ms',\n",
        "            'timezone': 'Europe/Brussels',\n",
        "        }, timeout=15)\n",
        "        r.raise_for_status()\n",
        "        d = r.json()\n",
        "        h = d['hourly']\n",
        "        # Average hours 10-13 local (Sentinel-2 overpass over Belgium approx 11:30 local)\n",
        "        _rows.append({\n",
        "            'city':        city,\n",
        "            'year':        year,\n",
        "            'scene_date':  date_str,\n",
        "            'altitude_m':  d['elevation'],\n",
        "            'humidity_pct': pd.Series(h['relative_humidity_2m'][10:14]).mean(),\n",
        "            'wind_ms':      pd.Series(h['wind_speed_10m'][10:14]).mean(),\n",
        "            'solar_wm2':    pd.Series(h['shortwave_radiation'][10:14]).mean(),\n",
        "        })\n",
        "        wx = _rows[-1]\n",
        "        print(f\"  {city:10s} {year}  alt={wx['altitude_m']:.0f}m  \"\n",
        "              f\"hum={wx['humidity_pct']:.1f}%  wind={wx['wind_ms']:.1f} m/s  \"\n",
        "              f\"solar={wx['solar_wm2']:.0f} W/m2\")\n",
        "        _time.sleep(0.3)\n",
        "\n",
        "scene_weather = pd.DataFrame(_rows).set_index(['city', 'year'])\n",
        "_sw_path = PROCESSED / 'scene_weather_by_city.csv'\n",
        "scene_weather.reset_index().to_csv(_sw_path, index=False)\n",
        "print(f'\\n  scene_weather saved to {_sw_path}')\n",
        "print(scene_weather[['humidity_pct', 'wind_ms', 'solar_wm2', 'altitude_m']].to_string())\n"
    ]
}

# ── Updated mc_predict source ─────────────────────────────────────────────────
updated_mc_predict_source = [
    "# ── City bounding boxes and Sentinel-2 tile routing ─────────────────────\n",
    "CITY_CONFIGS = {\n",
    "    'Leuven':   {'tile': 'T31UFT', 'lat': (50.84, 50.94), 'lon': (4.63, 4.78),\n",
    "                 'scene': {2023: '2023-08-20', 2024: '2024-07-30', 2025: '2025-08-11'}},\n",
    "    'Liège':    {'tile': 'T31UFT', 'lat': (50.59, 50.71), 'lon': (5.46, 5.68),\n",
    "                 'scene': {2023: '2023-08-20', 2024: '2024-07-30', 2025: '2025-08-11'}},\n",
    "    'Brussels': {'tile': 'T31UES', 'lat': (50.79, 50.91), 'lon': (4.27, 4.47),\n",
    "                 'scene': {2023: '2023-08-10', 2024: '2024-07-30', 2025: '2025-08-12'}},\n",
    "    'Ghent':    {'tile': 'T31UES', 'lat': (50.99, 51.11), 'lon': (3.61, 3.81),\n",
    "                 'scene': {2023: '2023-08-10', 2024: '2024-07-30', 2025: '2025-08-12'}},\n",
    "    'Antwerp':  {'tile': 'T31UES', 'lat': (51.16, 51.28), 'lon': (4.32, 4.52),\n",
    "                 'scene': {2023: '2023-08-10', 2024: '2024-07-30', 2025: '2025-08-12'}},\n",
    "}\n",
    "GRID_STEPS_CITY = 60\n",
    "\n",
    "def predict_city_grid(city_name, year):\n",
    "    \"\"\"Apply Leuven-trained model to any Belgian city with available Sentinel-2 data.\"\"\"\n",
    "    cfg = CITY_CONFIGS[city_name]\n",
    "    tile_dir = DATA_ROOT / 'sentinel2' / cfg['tile']\n",
    "    scene_str = cfg['scene'].get(year)\n",
    "    if not scene_str:\n",
    "        return None, None, None, None\n",
    "    sd = tile_dir / scene_str\n",
    "    if not sd.exists():\n",
    "        print(f'  {city_name} {year}: {cfg[\"tile\"]}/{scene_str} not yet downloaded — skipping')\n",
    "        return None, None, None, None\n",
    "\n",
    "    lat_g = np.linspace(*cfg['lat'], GRID_STEPS_CITY)\n",
    "    lon_g = np.linspace(*cfg['lon'], GRID_STEPS_CITY)\n",
    "    LAT_G2, LON_G2 = np.meshgrid(lat_g, lon_g)\n",
    "    g_lats, g_lons = LAT_G2.ravel(), LON_G2.ravel()\n",
    "    n_g = g_lats.size\n",
    "    eps = 1e-6\n",
    "\n",
    "    bands = {}\n",
    "    for b in ['B04', 'B08', 'B11']:\n",
    "        jp2 = sd / f'{b}.jp2'\n",
    "        bands[b] = sample_band_at_coords(jp2, g_lats, g_lons) if jp2.exists() \\\n",
    "                   else np.full(n_g, np.nan)\n",
    "\n",
    "    ndvi = (bands['B08'] - bands['B04']) / (bands['B08'] + bands['B04'] + eps)\n",
    "    ndbi = (bands['B11'] - bands['B08']) / (bands['B11'] + bands['B08'] + eps)\n",
    "\n",
    "    # Use city-specific weather from Open-Meteo lookup; fall back to Leuven medians\n",
    "    yr_df = df[df['year'] == year]\n",
    "    try:\n",
    "        wx    = scene_weather.loc[(city_name, year)]\n",
    "        hum   = wx['humidity_pct']\n",
    "        alt   = wx['altitude_m']\n",
    "        wind  = wx['wind_ms']\n",
    "        solar = wx['solar_wm2']\n",
    "    except (KeyError, NameError):\n",
    "        hum   = yr_df['HUMIDITY'].median()\n",
    "        alt   = yr_df['ALTITUDE'].median()\n",
    "        wind  = yr_df['wind_ms'].median()\n",
    "        solar = yr_df['SOLARRADIATION'].median()\n",
    "\n",
    "    gX = np.column_stack([\n",
    "        ndvi, ndbi,\n",
    "        bands['B11'],\n",
    "        np.full(n_g, hum),\n",
    "        np.full(n_g, alt),\n",
    "        np.full(n_g, wind),\n",
    "        np.full(n_g, solar),\n",
    "    ])\n",
    "    nm = np.any(np.isnan(gX), axis=1)\n",
    "    for col in range(gX.shape[1]):\n",
    "        gX[nm, col] = np.nanmedian(gX[:, col])\n",
    "\n",
    "    scaled_gX = scaler.transform(gX)\n",
    "    if isinstance(best_model_obj, Ridge):\n",
    "        grid_anom = best_model_obj.predict(\n",
    "            np.column_stack([rf.predict(scaled_gX), best_xgb.predict(scaled_gX)])\n",
    "        ).reshape(LAT_G2.shape)\n",
    "    else:\n",
    "        grid_anom = best_model_obj.predict(scaled_gX).reshape(LAT_G2.shape)\n",
    "    return grid_anom, lat_g, lon_g, scene_str\n",
    "\n",
    "print('Predicting 2025 heat anomaly for all 5 Belgian cities...')\n",
    "city_results = {}\n",
    "for city in CITY_CONFIGS:\n",
    "    result = predict_city_grid(city, 2025)\n",
    "    if result[0] is not None:\n",
    "        city_results[city] = result\n",
    "        g, *_, s = result\n",
    "        print(f'  {city:12s} ({s}): anomaly {g.min():.2f} to {g.max():.2f} °C')\n",
    "print(f'\\n{len(city_results)}/{len(CITY_CONFIGS)} cities predicted successfully.')\n"
]

# ── Apply all changes ─────────────────────────────────────────────────────────
# Insert markdown then code after mc_intro (positions 72, 73)
cells.insert(mc_intro_idx + 1, md_cell)
cells.insert(mc_intro_idx + 2, code_cell)

# mc_predict has shifted by 2
cells[mc_predict_idx + 2]['source'] = updated_mc_predict_source

nb['cells'] = cells
nb_path.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding='utf-8')
print(f'Done. Total cells: {len(cells)}')
print(f'  [omw_weather_md]   at index {mc_intro_idx + 1}')
print(f'  [omw_weather_code] at index {mc_intro_idx + 2}')
print(f'  [mc_predict]       updated at index {mc_predict_idx + 2}')
