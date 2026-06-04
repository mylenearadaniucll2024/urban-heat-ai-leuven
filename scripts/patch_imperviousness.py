"""
Patch heat_monitoring_intelligence.ipynb to add EU Urban Atlas Imperviousness
Density 2018 as feature 8 (IMPERVIOUSNESS).

Changes:
  + 4 cells after daily_agg [60408876]: download md/code, sample md/code
  ~ FEATURES cell [40395ef7]: append 'IMPERVIOUSNESS'
  + 4 cells after bar chart [d0c0baee]: retrain-compare md/code, SHAP-v2 md/code
  ~ mc_predict [mc_predict]: add imperv_grid to gX (8th column)
  + 2 cells after mc_plot [mc_plot]: mc_v2 md/code (export v2 HTML)
"""

import json, pathlib, sys, textwrap
sys.stdout.reconfigure(encoding='utf-8')

NB_PATH = pathlib.Path(r'c:\Users\wamy\Desktop\urban-heat-ai\notebooks\heat_monitoring_intelligence.ipynb')
nb = json.loads(NB_PATH.read_text(encoding='utf-8'))
cells = nb['cells']


def find_cell(cell_id):
    for i, c in enumerate(cells):
        if c.get('id') == cell_id:
            return i
    raise ValueError(f'Cell id={cell_id!r} not found')


def src(text):
    """Convert a multi-line string to notebook source format (list of lines with \\n)."""
    lines = text.lstrip('\n').splitlines(keepends=True)
    # Ensure last line has no trailing newline (notebook convention)
    if lines and lines[-1].endswith('\n'):
        lines[-1] = lines[-1].rstrip('\n')
    return lines


def md_cell(cell_id, text):
    return {"id": cell_id, "cell_type": "markdown", "metadata": {}, "source": src(text)}


def code_cell(cell_id, text):
    return {"id": cell_id, "cell_type": "code", "execution_count": None,
            "metadata": {}, "outputs": [], "source": src(text)}


def insert_after(anchor_id, new_cells):
    idx = find_cell(anchor_id)
    for offset, cell in enumerate(new_cells):
        cells.insert(idx + 1 + offset, cell)


# ─────────────────────────────────────────────────────────────────────────────
# Cell content
# ─────────────────────────────────────────────────────────────────────────────

IMD_DOWNLOAD_MD = """\
### 6b. Feature 8 — EU Urban Atlas Imperviousness Density 2018

Imperviousness (sealed-surface fraction, 0–100 %) measures the proportion of \
each 10 m pixel covered by impervious material — roads, rooftops, car parks. \
Unlike NDBI, which is a spectral ratio that changes with each satellite overpass, \
the Urban Atlas raster is a static land-use product (updated every 6 years) that \
captures permanent infrastructure.

**Why add this feature?** NDBI underestimates imperviousness in mixed pixels \
(e.g. rooftop + vegetation) and is sensitive to atmospheric conditions on the \
scene date. A dedicated imperviousness layer separates permanent urban form from \
transient spectral effects, giving the model a stable structural feature.

**Source:** Copernicus Land Monitoring Service — High Resolution Layer (HRL) \
Imperviousness Density 2018
**Coverage:** Belgium (Flanders, Wallonia, Brussels-Capital)
**Resolution:** 10 m · EPSG:3035 (ETRS89-LAEA Europe)

> ⚠ **MANUAL DOWNLOAD MAY BE REQUIRED** — the cell below attempts an EEA WCS \
auto-download; if that fails, follow the printed instructions.\
"""

IMD_DOWNLOAD_CODE = """\
# ── EU Urban Atlas Imperviousness Density 2018 — Download helper ──────────────
# Attempts EEA WCS; prints manual instructions if WCS is unavailable.
# Skips download if file already exists.

import urllib.request

_IMD_PATH = DATA_ROOT / 'imperviousness' / 'IMD_2018_010m_Belgium.tif'


def download_imperviousness():
    \"\"\"Download IMD 2018 for Belgium from EEA WCS; fall back to manual guide.\"\"\"
    if _IMD_PATH.exists():
        import rasterio
        with rasterio.open(_IMD_PATH) as _s:
            print(f'Found  : {_IMD_PATH}')
            print(f'  Size : {_IMD_PATH.stat().st_size / 1e6:.1f} MB')
            print(f'  CRS  : {_s.crs}')
            print(f'  Shape: {_s.shape[0]} rows x {_s.shape[1]} cols')
        return True

    _IMD_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Belgium bounding box in EPSG:3035 (approx)
    _WCS = (
        'https://copernicus.discomap.eea.europa.eu/arcgis/services/GioLand/'
        'HRL_ImperviousnessDensity_2018/ImageServer/WCSServer'
        '?SERVICE=WCS&VERSION=1.0.0&REQUEST=GetCoverage'
        '&COVERAGE=HRL_ImperviousnessDensity_2018'
        '&CRS=EPSG:3035&BBOX=3950000,3020000,4280000,3280000'
        '&WIDTH=33000&HEIGHT=26000&FORMAT=GeoTIFF'
    )
    print('Attempting WCS download from EEA DiscoMap (~30 s, ~120 MB) ...')
    try:
        _req = urllib.request.Request(_WCS, headers={'User-Agent': 'UrbanHeatAI/1.0'})
        with urllib.request.urlopen(_req, timeout=120) as _r:
            _data = _r.read()
        _IMD_PATH.write_bytes(_data)
        import rasterio
        with rasterio.open(_IMD_PATH) as _s:
            print(f'  Downloaded OK: {_IMD_PATH.stat().st_size/1e6:.1f} MB  CRS: {_s.crs}')
        return True
    except Exception as _exc:
        if _IMD_PATH.exists():
            _IMD_PATH.unlink()
        print(f'  WCS failed: {_exc}')

    print()
    print('\\u2501' * 65)
    print('  MANUAL DOWNLOAD REQUIRED  (one-time, free Copernicus account)')
    print('\\u2501' * 65)
    print('  1. Open:')
    print('     https://land.copernicus.eu/en/products/imperviousness/')
    print('     high-resolution-imperviousness-density-2018')
    print('  2. Sign in -> Download by area -> Country: Belgium')
    print('     Year: 2018 | Resolution: 10m | Format: GeoTIFF | CRS: EPSG:3035')
    print(f'  3. Save the .tif to:')
    print(f'       {_IMD_PATH}')
    print('  4. Re-run this cell to verify.')
    print('\\u2501' * 65)
    return False


_imd_ready = download_imperviousness()
if not _imd_ready:
    print()
    print('NOTE: IMPERVIOUSNESS will be set to 50 (midpoint placeholder) for all rows.')
    print('Download the raster and re-run from this cell to use real values.')\
"""

IMD_SAMPLE_MD = """\
### 6c. Sample Imperviousness at Station Coordinates

`sample_imperviousness()` opens the 10 m GeoTIFF, reprojects each station's \
WGS84 coordinates to EPSG:3035 using `pyproj.Transformer(always_xy=True)`, \
and samples the raster with `rasterio.DatasetReader.sample()`. No spatial \
aggregation — one pixel per station, matching the Sentinel-2 band-sampling approach.

Nodata and out-of-range values become NaN and are filled with the dataset median \
before the ML feature matrix is constructed.\
"""

IMD_SAMPLE_CODE = """\
# ── sample_imperviousness() + add IMPERVIOUSNESS to merged ────────────────────
import rasterio
from pyproj import Transformer

_IMD_PATH = DATA_ROOT / 'imperviousness' / 'IMD_2018_010m_Belgium.tif'


def sample_imperviousness(lats, lons, raster_path=None):
    \"\"\"
    Sample Imperviousness Density (0-100%) at WGS84 lat/lon coordinates.

    Parameters
    ----------
    lats, lons : array-like  (WGS84 decimal degrees)
    raster_path : Path | str | None  (defaults to IMD_2018_010m_Belgium.tif)

    Returns
    -------
    numpy float64 array, nodata/out-of-range replaced with NaN
    \"\"\"
    if raster_path is None:
        raster_path = DATA_ROOT / 'imperviousness' / 'IMD_2018_010m_Belgium.tif'

    lats = np.asarray(lats, dtype=np.float64)
    lons = np.asarray(lons, dtype=np.float64)

    with rasterio.open(raster_path) as src:
        nodata      = src.nodata
        rast_crs    = src.crs
        transformer = Transformer.from_crs('EPSG:4326', rast_crs, always_xy=True)
        xs, ys      = transformer.transform(lons, lats)   # always_xy: lon->x, lat->y
        coords      = list(zip(xs, ys))
        vals        = np.array([v[0] for v in src.sample(coords)], dtype=np.float64)

    if nodata is not None:
        vals = np.where(vals == nodata, np.nan, vals)
    vals = np.where(vals < 0,   np.nan, vals)   # negative sentinel values
    vals = np.where(vals > 100, np.nan, vals)   # above valid range
    return vals


# ── Apply to training dataframe ───────────────────────────────────────────────
if _IMD_PATH.exists():
    _imperv  = sample_imperviousness(merged['LATITUDE'].values,
                                      merged['LONGITUDE'].values,
                                      _IMD_PATH)
    _n_nan   = int(np.isnan(_imperv).sum())
    _med_imp = float(np.nanmedian(_imperv)) if not np.all(np.isnan(_imperv)) else 50.0
    _imperv  = np.where(np.isnan(_imperv), _med_imp, _imperv)
    merged['IMPERVIOUSNESS'] = _imperv
    print(f'IMPERVIOUSNESS added to merged DataFrame')
    print(f'  Valid rows : {int((~np.isnan(merged["IMPERVIOUSNESS"])).sum()):,} / {len(merged):,}')
    print(f'  NaNs filled: {_n_nan} with median {_med_imp:.1f} %')
    print(f'  min={merged["IMPERVIOUSNESS"].min():.1f}  '
          f'max={merged["IMPERVIOUSNESS"].max():.1f}  '
          f'mean={merged["IMPERVIOUSNESS"].mean():.2f}')
    print(merged['IMPERVIOUSNESS'].describe().to_string())
else:
    merged['IMPERVIOUSNESS'] = 50.0   # midpoint so dropna() keeps all rows
    print('WARNING: Raster not found. IMPERVIOUSNESS set to 50 (midpoint placeholder).')
    print(f'Expected path: {_IMD_PATH}')
    print('Download the raster, then re-run this cell and all cells below.')\
"""

# ── retrain comparison ─────────────────────────────────────────────────────────

IMD_RETRAIN_MD = """\
### 8b. Feature Impact — IMPERVIOUSNESS vs 7-Feature Baseline

The cells below compare model performance before and after adding Imperviousness \
as feature 8. The v1 baseline metrics are hardcoded from the Phase 7 results table \
above (7 features). The v2 metrics are read from `rf`, `best_xgb`, and \
`best_model_obj` — already retrained with the updated 8-feature matrix when the \
FEATURES cell and all training cells were re-run.\
"""

IMD_RETRAIN_CODE = """\
# ── Feature 8 impact: 7-feature baseline vs 8-feature comparison ─────────────
# v1 baseline — hardcoded from Phase 7 results table (7-feature run)
_v1 = {
    'Random Forest':   {'RMSE': 0.4403, 'MAE': 0.2700, 'R2': 0.5516},
    'XGBoost (tuned)': {'RMSE': 0.4306, 'MAE': 0.2630, 'R2': 0.5711},
    'Stacked RF+XGB':  {'RMSE': 0.4270, 'MAE': 0.2613, 'R2': 0.5782},
}

# v2 — from variables already set by training cells above (8 features)
# xgb_tuned_rmse_v1 / xgb_tuned_r2_v1 are saved in the stacking cell
# before the meta-learner override, so they hold tuned-XGB v2 metrics here.
_v2 = {
    'Random Forest':   {'RMSE': rf_rmse,           'MAE': rf_mae,           'R2': rf_r2},
    'XGBoost (tuned)': {'RMSE': xgb_tuned_rmse_v1, 'MAE': xgb_tuned_mae_v1, 'R2': xgb_tuned_r2_v1},
    'Stacked RF+XGB':  {'RMSE': stack_rmse,        'MAE': stack_mae,        'R2': stack_r2},
}

print(f'{"Model":<18} {"RMSE v1":>8} {"RMSE v2":>8} {"\\u0394RMSE":>7}  {"R\\u00b2 v1":>6} {"R\\u00b2 v2":>6} {"\\u0394R\\u00b2":>7}')
print('\\u2500' * 70)
for _m in _v1:
    _d1, _d2 = _v1[_m], _v2[_m]
    _dr  = _d2['RMSE'] - _d1['RMSE']
    _dr2 = _d2['R2']   - _d1['R2']
    _sym = '\\u2193' if _dr < -0.001 else ('\\u2191' if _dr > 0.001 else '\\u2248')
    print(f'{_m:<18} {_d1["RMSE"]:>8.4f} {_d2["RMSE"]:>8.4f} {_dr:>+7.4f}{_sym} '
          f'{_d1["R2"]:>6.4f} {_d2["R2"]:>6.4f} {_dr2:>+7.4f}')
print()
_best = min(_v2, key=lambda _m: _v2[_m]['RMSE'])
print(f'Best v2 model: {_best}')
print(f'  RMSE = {_v2[_best]["RMSE"]:.4f} \\u00b0C   R\\u00b2 = {_v2[_best]["R2"]:.4f}')\
"""

IMD_SHAP_V2_MD = """\
### 8c. SHAP Feature Importance — 8-Feature Model

Updated SHAP beeswarm for the retrained Random Forest. The key question: does \
IMPERVIOUSNESS rank above or below NDBI? If it ranks higher, it contributes \
structural signal that spectral indices do not fully capture. Ranked mean |SHAP| \
values are printed below the plot.\
"""

IMD_SHAP_V2_CODE = """\
# ── SHAP beeswarm — Random Forest v2 (8 features) ────────────────────────────
import shap as _shap

_explainer_v2 = _shap.TreeExplainer(rf)
_shap_vals_v2 = _explainer_v2.shap_values(X_test)

plt.figure(figsize=(10, 6))
_shap.summary_plot(_shap_vals_v2, X_test, feature_names=FEATURES, show=False)
plt.title('SHAP Summary \\u2014 Random Forest v2 (8 features incl. Imperviousness)', fontsize=13)
plt.tight_layout()
plt.savefig('shap_rf_v2_summary.png', dpi=150, bbox_inches='tight')
plt.show()

_mean_shap_v2  = np.abs(_shap_vals_v2).mean(axis=0)
_shap_rank_v2  = sorted(zip(FEATURES, _mean_shap_v2), key=lambda x: -x[1])

print('Ranked mean |SHAP| values \\u2014 v2 (8 features):')
for _rank, (_feat, _val) in enumerate(_shap_rank_v2, 1):
    _tag = '  \\u25c4 NEW' if _feat == 'IMPERVIOUSNESS' else ''
    print(f'  {_rank}. {_feat:<22s}  {_val:.4f}{_tag}')

_imd_r  = next(_r for _r, (_f, _) in enumerate(_shap_rank_v2, 1) if _f == 'IMPERVIOUSNESS')
_ndbi_r = next(_r for _r, (_f, _) in enumerate(_shap_rank_v2, 1) if _f == 'NDBI')
print(f'\\nIMPERVIOUSNESS rank: {_imd_r}  |  NDBI rank: {_ndbi_r}')
if _imd_r < _ndbi_r:
    print('\\u2192 IMPERVIOUSNESS ranks ABOVE NDBI \\u2014 adds structural signal beyond spectral indices.')
else:
    print('\\u2192 IMPERVIOUSNESS ranks below NDBI \\u2014 spectral indices capture most built-up signal.')
print('shap_rf_v2_summary.png saved.')\
"""

# ── mc_v2 ──────────────────────────────────────────────────────────────────────

MC_V2_MD = """\
### 10e. Multi-City Predictions — v2 (8-Feature Model)

Re-runs `predict_city_grid` for all five Belgian cities with the \
Imperviousness-augmented model, then exports `belgian_cities_heat_anomaly_v2.html` \
alongside the existing v1 output so the two maps can be compared side-by-side.\
"""

MC_V2_CODE = """\
# ── City predictions v2 (8-feature model) ─────────────────────────────────────
print('Re-running 2025 predictions with 8-feature model (+ Imperviousness)...')
city_results_v2 = {}
for _city in CITY_CONFIGS:
    _res = predict_city_grid(_city, 2025)
    if _res[0] is not None:
        city_results_v2[_city] = _res
        _g, *_, _s = _res
        print(f'  {_city:12s} ({_s}): {_g.min():.2f} to {_g.max():.2f} \\u00b0C')
print(f'{len(city_results_v2)}/{len(CITY_CONFIGS)} cities predicted.')

if city_results_v2:
    _cities_v2 = list(city_results_v2.keys())
    _all_g     = np.concatenate([city_results_v2[c][0].ravel() for c in _cities_v2])
    _sym_all   = max(abs(_all_g.min()), abs(_all_g.max()))

    _fig_v2 = make_subplots(
        rows=1, cols=len(_cities_v2),
        subplot_titles=[f'{c}<br><sup>{city_results_v2[c][3]}</sup>' for c in _cities_v2],
        horizontal_spacing=0.04
    )
    for _idx, _city in enumerate(_cities_v2, 1):
        _g, _lat_g, _lon_g, _scene = city_results_v2[_city]
        _fig_v2.add_trace(go.Heatmap(
            z=_g, x=_lon_g, y=_lat_g,
            colorscale='RdBu_r', zmid=0, zmin=-_sym_all, zmax=_sym_all,
            showscale=(_idx == len(_cities_v2)),
            colorbar=dict(title='Anomaly (\\u00b0C)', x=1.01),
            hovertemplate='Lon:%{x:.4f}<br>Lat:%{y:.4f}<br>Anomaly:%{z:.2f}\\u00b0C<extra></extra>'
        ), row=1, col=_idx)

    _fig_v2.update_layout(
        title=(
            'Belgian City Heat Anomaly \\u2014 Stacked RF+XGB v2 (2025, 8 features)<br>'
            '<sup>Feature 8: EU Urban Atlas Imperviousness Density 2018 (10 m, EPSG:3035). '
            'Shared colour scale.</sup>'
        ),
        height=480, template='plotly_white'
    )
    _fig_v2.show()
    _fig_v2.write_html('belgian_cities_heat_anomaly_v2.html')
    print('Exported: belgian_cities_heat_anomaly_v2.html')
else:
    print('No v2 city results.')\
"""

# ── Updated mc_predict source ──────────────────────────────────────────────────

# Build the updated mc_predict by modifying the imperv section and gX column_stack.
# We keep everything else identical to the current cell.

MC_PREDICT_SOURCE = """\
# ── City bounding boxes and Sentinel-2 tile routing ─────────────────────
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

    # Feature 8: imperviousness from EU HRL 2018 raster
    _imd_raster = DATA_ROOT / 'imperviousness' / 'IMD_2018_010m_Belgium.tif'
    if _imd_raster.exists():
        imperv_grid = sample_imperviousness(g_lats, g_lons, _imd_raster)
        _imp_med    = float(np.nanmedian(imperv_grid)) if not np.all(np.isnan(imperv_grid)) else 50.0
        imperv_grid = np.where(np.isnan(imperv_grid), _imp_med, imperv_grid)
    else:
        _fallback   = float(merged['IMPERVIOUSNESS'].median()) if 'IMPERVIOUSNESS' in merged.columns else 50.0
        imperv_grid = np.full(n_g, _fallback)

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

# ── Updated FEATURES cell source ───────────────────────────────────────────────

FEATURES_SOURCE = """\
FEATURES = ['NDVI','NDBI','B11','HUMIDITY','ALTITUDE','wind_ms','SOLARRADIATION','IMPERVIOUSNESS']
TARGET   = 'temp_anomaly'

# B11 (raw SWIR reflectance) is added alongside NDBI: the ratio NDBI normalises away the
# absolute magnitude of SWIR emission, which carries thermal-inertia information for dense
# vs sparse impervious surfaces at the same NDBI value.
# IMPERVIOUSNESS (EU HRL 2018, 10 m) captures permanent sealed-surface fraction,
# complementing the scene-date spectral indices with a static structural feature.

ml_df = merged[FEATURES + [TARGET, 'year', 'ID']].dropna()

# Store UNSCALED features \\u2014 scaler is fit only on the training split below.
# Fitting on the full dataset before splitting is a data-leakage bug.
X_raw       = ml_df[FEATURES].values
y           = ml_df[TARGET].values
year_labels = ml_df['year'].values

print(f'ML dataset: {len(ml_df):,} rows  |  target range: {y.min():.2f} to {y.max():.2f} \\u00b0C')
print(f'Unique stations in dataset: {ml_df["ID"].nunique()}')
print(f'Features ({len(FEATURES)}): {FEATURES}')\
"""


# ─────────────────────────────────────────────────────────────────────────────
# Apply changes (back-to-front so earlier insertions don't shift later indices)
# ─────────────────────────────────────────────────────────────────────────────

# Step 5: Insert 2 cells after mc_plot  (highest position first)
insert_after('mc_plot', [
    md_cell('mc_v2_md',   MC_V2_MD),
    code_cell('mc_v2_code', MC_V2_CODE),
])

# Step 3: Insert 4 cells after bar chart [d0c0baee]
insert_after('d0c0baee', [
    md_cell('imd_retrain_md',    IMD_RETRAIN_MD),
    code_cell('imd_retrain_code',  IMD_RETRAIN_CODE),
    md_cell('imd_shap_v2_md',    IMD_SHAP_V2_MD),
    code_cell('imd_shap_v2_code',  IMD_SHAP_V2_CODE),
])

# Step 1: Insert 4 cells after daily_agg [60408876]
insert_after('60408876', [
    md_cell('imd_download_md',   IMD_DOWNLOAD_MD),
    code_cell('imd_download_code', IMD_DOWNLOAD_CODE),
    md_cell('imd_sample_md',     IMD_SAMPLE_MD),
    code_cell('imd_sample_code',   IMD_SAMPLE_CODE),
])

# Step 2: Update FEATURES cell
cells[find_cell('40395ef7')]['source'] = src(FEATURES_SOURCE)

# Step 4: Update mc_predict cell
cells[find_cell('mc_predict')]['source'] = src(MC_PREDICT_SOURCE)

# ─────────────────────────────────────────────────────────────────────────────
# Save
# ─────────────────────────────────────────────────────────────────────────────
nb['cells'] = cells
NB_PATH.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding='utf-8')

print(f'Patch applied. Total cells: {len(cells)}')
print()
print('New / modified cells:')
for cid, label in [
    ('imd_download_md',   'Phase 6b markdown — imperviousness intro'),
    ('imd_download_code', 'Phase 6b code    — download_imperviousness()'),
    ('imd_sample_md',     'Phase 6c markdown — sampling explanation'),
    ('imd_sample_code',   'Phase 6c code    — sample_imperviousness() + add to df'),
    ('40395ef7',          'FEATURES cell    — updated to 8 features'),
    ('imd_retrain_md',    'Phase 8b markdown — retrain comparison intro'),
    ('imd_retrain_code',  'Phase 8b code    — v1 vs v2 comparison table'),
    ('imd_shap_v2_md',    'Phase 8c markdown — SHAP v2 intro'),
    ('imd_shap_v2_code',  'Phase 8c code    — SHAP beeswarm 8 features'),
    ('mc_predict',        'mc_predict cell  — imperv_grid added to gX'),
    ('mc_v2_md',          'Phase 10e markdown — v2 city prediction intro'),
    ('mc_v2_code',        'Phase 10e code   — export belgian_cities_v2.html'),
]:
    idx = find_cell(cid)
    print(f'  [{idx:02d}] {cid:22s}  {label}')
