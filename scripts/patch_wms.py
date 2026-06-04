"""
Replace the file-based imperviousness approach with EEA ImageServer REST API.

Changes:
  ~ Cell imd_download_code [37]: WMS connectivity test (no file download)
  ~ Cell imd_sample_code   [39]: query_imperviousness_wms() via /identify
  ~ Cell mc_predict        [82]: exportImage in-memory tile for city grid

Training path:  111 unique stations × 0.2 s sleep ≈ 22 s
City-grid path: 1 exportImage request per city (in-memory rasterio) ≈ 3 s/city
"""

import json, pathlib, sys
sys.stdout.reconfigure(encoding='utf-8')

NB_PATH = pathlib.Path(
    r'c:\Users\wamy\Desktop\urban-heat-ai\notebooks\heat_monitoring_intelligence.ipynb'
)
nb = json.loads(NB_PATH.read_text(encoding='utf-8'))
cells = nb['cells']


def find_cell(cell_id):
    for i, c in enumerate(cells):
        if c.get('id') == cell_id:
            return i
    raise ValueError(f'Cell id={cell_id!r} not found')


def src(text):
    lines = text.lstrip('\n').splitlines(keepends=True)
    if lines and lines[-1].endswith('\n'):
        lines[-1] = lines[-1].rstrip('\n')
    return lines


# ─────────────────────────────────────────────────────────────────────────────
# Cell [37] imd_download_code  →  WMS setup + connectivity test
# ─────────────────────────────────────────────────────────────────────────────

IMD_SETUP = """\
# ── EEA ImageServer — no file download required ───────────────────────────────
# Uses the Copernicus WMS REST API to sample imperviousness at query time.
# Two endpoints are used:
#   /identify      → single-point pixel query  (training station coordinates)
#   /exportImage   → bounding-box raster tile  (city prediction grid)

import requests as _req_imd
import time as _time_imd

_IMD_BASE = (
    'https://image.discomap.eea.europa.eu/arcgis/rest/services/'
    'GioLandPublic/HRL_ImperviousnessDensity_2018/ImageServer'
)
_IMD_IDENTIFY_URL = _IMD_BASE + '/identify'
_IMD_EXPORT_URL   = _IMD_BASE + '/exportImage'


def _test_imd_endpoint():
    \"\"\"Quick liveness check — query a single known point (Leuven city centre).\"\"\"
    try:
        r = _req_imd.get(_IMD_IDENTIFY_URL, params={
            'geometry':     '4.7005,50.8798',
            'geometryType': 'esriGeometryPoint',
            'returnGeometry': 'false',
            'f':            'json',
        }, timeout=10)
        r.raise_for_status()
        v = r.json().get('value')
        print(f'EEA ImageServer reachable.')
        print(f'  Test pixel: Leuven city centre \\u2192 imperviousness = {v} %')
        return True
    except Exception as _e:
        print(f'WARNING: EEA ImageServer unreachable: {_e}')
        print('IMPERVIOUSNESS will be set to 50 (midpoint placeholder) for all rows.')
        return False


_imd_online = _test_imd_endpoint()\
"""

# ─────────────────────────────────────────────────────────────────────────────
# Cell [39] imd_sample_code  →  query_imperviousness_wms() + add to merged
# ─────────────────────────────────────────────────────────────────────────────

IMD_WMS_SAMPLE = """\
# ── query_imperviousness_wms() + add IMPERVIOUSNESS to merged ────────────────
# Uses /identify endpoint. Deduplicates to unique station positions before
# querying (111 unique stations, not 5,575 rows) to keep runtime ~22 s.

import numpy as _np_imd

# Re-declare in case this cell runs without the setup cell above
try:
    _IMD_IDENTIFY_URL
    _imd_online
except NameError:
    import requests as _req_imd, time as _time_imd
    _IMD_IDENTIFY_URL = (
        'https://image.discomap.eea.europa.eu/arcgis/rest/services/'
        'GioLandPublic/HRL_ImperviousnessDensity_2018/ImageServer/identify'
    )
    _imd_online = True   # attempt anyway; errors are caught per-request


def query_imperviousness_wms(lats, lons, sleep=0.2, progress_every=10):
    \"\"\"
    Query EU HRL Imperviousness Density 2018 at WGS84 coordinates.

    Sends one GET /identify request per coordinate.
    Returns float64 array; HTTP errors / nodata \\u2192 NaN.

    Parameters
    ----------
    lats, lons       : array-like (WGS84 decimal degrees)
    sleep            : seconds between requests (default 0.2 for rate-limiting)
    progress_every   : print progress every N requests
    \"\"\"
    lats = np.asarray(lats, dtype=np.float64)
    lons = np.asarray(lons, dtype=np.float64)
    n    = len(lats)
    vals = np.full(n, np.nan)

    for i, (lat, lon) in enumerate(zip(lats, lons)):
        if i > 0 and i % progress_every == 0:
            _n_ok = int(np.sum(~np.isnan(vals[:i])))
            print(f'  {i}/{n} queried ({_n_ok} valid)...')
        try:
            _r = _req_imd.get(_IMD_IDENTIFY_URL, params={
                'geometry':       f'{lon},{lat}',
                'geometryType':   'esriGeometryPoint',
                'returnGeometry': 'false',
                'f':              'json',
            }, timeout=10)
            _r.raise_for_status()
            _raw = _r.json().get('value')
            if _raw is not None and str(_raw).lower() not in ('nodata', 'null', ''):
                _fv = float(_raw)
                if 0.0 <= _fv <= 100.0:
                    vals[i] = _fv
        except Exception:
            pass
        _time_imd.sleep(sleep)

    _n_valid = int(np.sum(~np.isnan(vals)))
    print(f'  Done. {_n_valid}/{n} valid values returned.')
    return vals


# ── Add IMPERVIOUSNESS to training dataframe ──────────────────────────────────
if _imd_online:
    # Deduplicate: query only unique (lat, lon) pairs
    _uniq = merged[['LATITUDE', 'LONGITUDE']].drop_duplicates().reset_index(drop=True)
    print(f'Querying EEA ImageServer for {len(_uniq)} unique station positions ...')

    _imperv_uniq = query_imperviousness_wms(
        _uniq['LATITUDE'].values, _uniq['LONGITUDE'].values
    )

    # Map unique values back to all 5,575 rows
    _coord_map = {(lat, lon): v
                  for (lat, lon), v in zip(
                      zip(_uniq['LATITUDE'], _uniq['LONGITUDE']),
                      _imperv_uniq)}
    merged['IMPERVIOUSNESS'] = [
        _coord_map.get((lat, lon), np.nan)
        for lat, lon in zip(merged['LATITUDE'], merged['LONGITUDE'])
    ]

    _n_nan  = int(merged['IMPERVIOUSNESS'].isna().sum())
    _med_im = float(merged['IMPERVIOUSNESS'].median()) \
              if _n_nan < len(merged) else 50.0
    if _n_nan > 0:
        merged['IMPERVIOUSNESS'] = merged['IMPERVIOUSNESS'].fillna(_med_im)

    print(f'\\nIMPERVIOUSNESS added to merged DataFrame:')
    print(f'  Unique stations queried : {len(_uniq):,}')
    print(f'  Valid station values    : {int(np.sum(~np.isnan(_imperv_uniq))):,} / {len(_uniq):,}')
    print(f'  NaNs filled with median : {_n_nan} rows \\u2192 {_med_im:.1f} %')
    print(f'  min={merged["IMPERVIOUSNESS"].min():.1f}  '
          f'max={merged["IMPERVIOUSNESS"].max():.1f}  '
          f'mean={merged["IMPERVIOUSNESS"].mean():.2f}')
    print(merged['IMPERVIOUSNESS'].describe().to_string())
else:
    merged['IMPERVIOUSNESS'] = 50.0
    print('IMPERVIOUSNESS set to 50 (placeholder \\u2014 EEA endpoint unreachable).')\
"""

# ─────────────────────────────────────────────────────────────────────────────
# Cell [82] mc_predict  →  imperv block uses exportImage (in-memory tile)
# ─────────────────────────────────────────────────────────────────────────────

MC_PREDICT_WMS = """\
# ── City bounding boxes and Sentinel-2 tile routing ─────────────────────
import requests as _req_mc
from rasterio.io import MemoryFile as _MemoryFile

_IMD_EXPORT_URL_MC = (
    'https://image.discomap.eea.europa.eu/arcgis/rest/services/'
    'GioLandPublic/HRL_ImperviousnessDensity_2018/ImageServer/exportImage'
)

CITY_CONFIGS = {
    'Leuven':   {'tile': 'T31UFT', 'lat': (50.84, 50.94), 'lon': (4.63, 4.78),
                 'scene': {2023: '2023-08-20', 2024: '2024-07-30', 2025: '2025-08-11'}},
    'Li\\u00e8ge':    {'tile': 'T31UFT', 'lat': (50.59, 50.71), 'lon': (5.46, 5.68),
                 'scene': {2023: '2023-08-20', 2024: '2024-07-30', 2025: '2025-08-11'}},
    'Brussels': {'tile': 'T31UES', 'lat': (50.79, 50.91), 'lon': (4.27, 4.47),
                 'scene': {2023: '2023-08-10', 2024: '2024-07-30', 2025: '2025-08-12'}},
    'Ghent':    {'tile': 'T31UES', 'lat': (50.99, 51.11), 'lon': (3.61, 3.81),
                 'scene': {2023: '2023-08-10', 2024: '2024-07-30', 2025: '2025-08-12'}},
    'Antwerp':  {'tile': 'T31UES', 'lat': (51.16, 51.28), 'lon': (4.32, 4.52),
                 'scene': {2023: '2023-08-10', 2024: '2024-07-30', 2025: '2025-08-12'}},
}
GRID_STEPS_CITY = 60


def predict_city_grid(city_name, year):
    \"\"\"Apply Leuven-trained model to any Belgian city with available Sentinel-2 data.\"\"\"
    cfg = CITY_CONFIGS[city_name]
    tile_dir  = DATA_ROOT / 'sentinel2' / cfg['tile']
    scene_str = cfg['scene'].get(year)
    if not scene_str:
        return None, None, None, None
    sd = tile_dir / scene_str
    if not sd.exists():
        print(f'  {city_name} {year}: {cfg["tile"]}/{scene_str} not yet downloaded \\u2014 skipping')
        return None, None, None, None

    lat_g = np.linspace(*cfg['lat'], GRID_STEPS_CITY)
    lon_g = np.linspace(*cfg['lon'], GRID_STEPS_CITY)
    LAT_G2, LON_G2 = np.meshgrid(lat_g, lon_g)
    g_lats, g_lons = LAT_G2.ravel(), LON_G2.ravel()
    n_g = g_lats.size
    eps = 1e-6

    bands = {}
    for b in ['B04', 'B08', 'B11']:
        jp2 = sd / f'{b}.jp2'
        bands[b] = sample_band_at_coords(jp2, g_lats, g_lons) if jp2.exists() \\
                   else np.full(n_g, np.nan)

    ndvi = (bands['B08'] - bands['B04']) / (bands['B08'] + bands['B04'] + eps)
    ndbi = (bands['B11'] - bands['B08']) / (bands['B11'] + bands['B08'] + eps)

    # Feature 8: imperviousness via EEA exportImage (one HTTP request per city)
    # Downloads a 300x300 in-memory GeoTIFF for the city bbox, sampled with rasterio.
    _pad = 0.005
    try:
        _resp = _req_mc.get(_IMD_EXPORT_URL_MC, params={
            'bbox':      f'{cfg["lon"][0]-_pad},{cfg["lat"][0]-_pad},'
                         f'{cfg["lon"][1]+_pad},{cfg["lat"][1]+_pad}',
            'bboxSR':    '4326',
            'imageSR':   '4326',
            'size':      '300,300',
            'format':    'tiff',
            'pixelType': 'U8',
            'noData':    '255',
            'f':         'image',
        }, timeout=60)
        _resp.raise_for_status()
        with _MemoryFile(_resp.content) as _mf:
            with _mf.open() as _ds:
                _nd   = _ds.nodata if _ds.nodata is not None else 255
                _samp = np.array(
                    [v[0] for v in _ds.sample(zip(g_lons.tolist(), g_lats.tolist()))],
                    dtype=np.float64)
        _samp = np.where((_samp == _nd) | (_samp < 0) | (_samp > 100), np.nan, _samp)
        _imp_med   = float(np.nanmedian(_samp)) if not np.all(np.isnan(_samp)) else 50.0
        imperv_grid = np.where(np.isnan(_samp), _imp_med, _samp)
    except Exception as _exc:
        _fb = (float(merged['IMPERVIOUSNESS'].median())
               if 'IMPERVIOUSNESS' in merged.columns else 50.0)
        imperv_grid = np.full(n_g, _fb)

    # Use city-specific weather from Open-Meteo lookup; fall back to Leuven medians
    yr_df = df[df['year'] == year]
    try:
        wx    = scene_weather.loc[(city_name, year)]
        hum   = wx['humidity_pct']
        alt   = wx['altitude_m']
        wind  = wx['wind_ms']
        solar = wx['solar_wm2']
    except (KeyError, NameError):
        hum   = yr_df['HUMIDITY'].median()
        alt   = yr_df['ALTITUDE'].median()
        wind  = yr_df['wind_ms'].median()
        solar = yr_df['SOLARRADIATION'].median()

    gX = np.column_stack([
        ndvi, ndbi,
        bands['B11'],
        np.full(n_g, hum),
        np.full(n_g, alt),
        np.full(n_g, wind),
        np.full(n_g, solar),
        imperv_grid,
    ])
    nm = np.any(np.isnan(gX), axis=1)
    for col in range(gX.shape[1]):
        gX[nm, col] = np.nanmedian(gX[:, col])

    scaled_gX = scaler.transform(gX)
    if isinstance(best_model_obj, Ridge):
        grid_anom = best_model_obj.predict(
            np.column_stack([rf.predict(scaled_gX), best_xgb.predict(scaled_gX)])
        ).reshape(LAT_G2.shape)
    else:
        grid_anom = best_model_obj.predict(scaled_gX).reshape(LAT_G2.shape)
    return grid_anom, lat_g, lon_g, scene_str


print('Predicting 2025 heat anomaly for all 5 Belgian cities...')
city_results = {}
for city in CITY_CONFIGS:
    result = predict_city_grid(city, 2025)
    if result[0] is not None:
        city_results[city] = result
        g, *_, s = result
        print(f'  {city:12s} ({s}): anomaly {g.min():.2f} to {g.max():.2f} \\u00b0C')
print(f'\\n{len(city_results)}/{len(CITY_CONFIGS)} cities predicted successfully.')\
"""


# ─────────────────────────────────────────────────────────────────────────────
# Apply: replace source in existing cells (no insertion needed)
# ─────────────────────────────────────────────────────────────────────────────

cells[find_cell('imd_download_code')]['source'] = src(IMD_SETUP)
cells[find_cell('imd_sample_code')]['source']   = src(IMD_WMS_SAMPLE)
cells[find_cell('mc_predict')]['source']        = src(MC_PREDICT_WMS)

nb['cells'] = cells
NB_PATH.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding='utf-8')

print('WMS patch applied.')
print()
for cid, desc in [
    ('imd_download_code', 'WMS setup + liveness test (Leuven pixel)'),
    ('imd_sample_code',   'query_imperviousness_wms() via /identify + merged update'),
    ('mc_predict',        'exportImage in-memory tile per city'),
]:
    idx = find_cell(cid)
    print(f'  [{idx:02d}] {cid:22s}  {desc}')
