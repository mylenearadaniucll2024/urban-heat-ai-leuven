"""
Audit & fix all stale markdown after IMPERVIOUSNESS feature addition.

Fixes applied (no model rerun needed):
  [03] TOC          — add 6b, 6c, 8b, 8c entries
  [38] imd_sample_md — replace stale GeoTIFF/pyproj description with WMS API truth
  [41] Phase6-intro  — "Tabular (6 features)" → "Tabular (8 features)" × 2
  [49] Result-RF     — "only 6 features" → "8 features"
  [52] Result-XGB    — "only 6 features and 5,575 rows" → "8 features"
  [60] Result-XGBtun — remove "imperviousness fraction" future-work suggestion
  [64] Phase7-intro  — fix table row "6 features only … no imperviousness layer"
  [74] Phase8-intro  — fix "only NDVI and NDBI vary" to include IMPERVIOUSNESS
  [76] Result-grid   — fix "only NDVI, NDBI and B11 vary" to include IMPERVIOUSNESS
  [79] Phase9-intro  — fix "two spatially-varying features" to three
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


# ── [03] Table of Contents ─────────────────────────────────────────────────────
patch_md(
    '1f9d6388',
    """6. [Phase 5 — Feature Engineering](#6)
   - NDVI / NDBI derivation and rationale
   - WorldCover validation
   - Full feature table
7. [Phase 6 — ML Modeling](#7)
   - Why three models
   - Train / Test / Retrain strategy
   - 7a. 80/20 Split + 5-Fold CV + LOSOCV
   - 7b. Random Forest
   - 7c. XGBoost
   - 7d. CNN — architecture + underfit explanation
   - 7e. Hyperparameter Tuning
8. [Phase 7 — Evaluation & Model Comparison](#8)
   - Why R² is moderate — explained
   - Standard CV vs LOSOCV
   - RMI Belgian city findings""",
    """6. [Phase 5 — Feature Engineering](#6)
   - NDVI / NDBI derivation and rationale
   - WorldCover validation
   - Full feature table
   - 6b. EU Urban Atlas Imperviousness Density 2018 (WMS)
   - 6c. Sampling imperviousness at station coordinates via EEA ImageServer
7. [Phase 6 — ML Modeling](#7)
   - Why three models
   - Train / Test / Retrain strategy
   - 7a. 80/20 Split + 5-Fold CV + LOSOCV
   - 7b. Random Forest
   - 7c. XGBoost
   - 7d. CNN — architecture + underfit explanation
   - 7e. Hyperparameter Tuning
   - 7f. Stacked Ensemble (RF + XGBoost meta-learner)
8. [Phase 7 — Evaluation & Model Comparison](#8)
   - Why R² is moderate — explained
   - Standard CV vs LOSOCV
   - 8b. Feature impact — v1 (7-feature) vs v2 (8-feature) comparison
   - 8c. SHAP feature importance — 8-feature model
   - RMI Belgian city findings""",
    'TOC — add 6b/6c/7f/8b/8c entries'
)

# ── [38] imd_sample_md — replace stale GeoTIFF/pyproj description ─────────────
patch_md(
    'imd_sample_md',
    """`sample_imperviousness()` opens the 10 m GeoTIFF, reprojects each station's WGS84 coordinates to EPSG:3035 using `pyproj.Transformer(always_xy=True)`, and samples the raster with `rasterio.DatasetReader.sample()`. No spatial aggregation — one pixel per station, matching the Sentinel-2 band-sampling approach.

Nodata and out-of-range values become NaN and are filled with the dataset median before the ML feature matrix is constructed.""",
    """`query_imperviousness_wms()` queries the EEA ArcGIS ImageServer REST `/identify` endpoint for each unique station position. Coordinates are passed as `{"x": lon, "y": lat, "spatialReference": {"wkid": 4326}}` JSON — the explicit spatial reference is required because the server's native CRS is EPSG:3035 (metres), so raw decimal-degree values would otherwise be misinterpreted. No file download required — each call returns the single pixel value directly.

Station positions are deduplicated before querying (111 unique positions from 5,575 rows) to reduce network calls to ≈22 s. NoData and out-of-range values become NaN and are filled with the dataset median before the ML feature matrix is constructed.""",
    'imd_sample_md — update to WMS API reality'
)

# ── [41] Phase 6 ML intro — "Tabular (6 features)" × 2 ───────────────────────
patch_md(
    'f7845a43',
    '| **Random Forest** | Tabular (6 features) |',
    '| **Random Forest** | Tabular (8 features) |',
    'Phase6-intro RF row'
)
patch_md(
    'f7845a43',
    '| **XGBoost** | Tabular (6 features) |',
    '| **XGBoost** | Tabular (8 features) |',
    'Phase6-intro XGB row'
)

# ── [49] Result-RF — "using only 6 features" ──────────────────────────────────
patch_md(
    '8365e1c4',
    'using only 6 features and 5,575 rows',
    'using 8 features and 5,575 rows',
    'Result-RF: 6→8 features'
)

# ── [52] Result-XGB — "with only 6 features" ──────────────────────────────────
patch_md(
    '31c5c1f5',
    'but with only 6 features and 5,575 rows',
    'but with 8 features and 5,575 rows',
    'Result-XGB: 6→8 features'
)

# ── [60] Result-XGBtuned — remove stale "imperviousness fraction" suggestion ──
patch_md(
    '9b3fca19',
    'Further performance improvements would require richer features (e.g., land surface temperature, NDWI, imperviousness fraction) rather than additional hyperparameter search.',
    'Further performance improvements would require richer features (e.g., land surface temperature, NDWI, additional temporal scenes) or a larger sensor network rather than additional hyperparameter search.',
    'Result-XGBtuned: remove stale imperviousness suggestion'
)

# ── [64] Phase 7 eval intro — fix "6 features only, no imperviousness" ─────────
patch_md(
    '04e04c3f',
    '| **6 features only** | NDVI, NDBI, HUMIDITY, ALTITUDE, wind_ms, SOLARRADIATION — no LST, no NDWI, no imperviousness layer |',
    '| **8 features** | NDVI, NDBI, B11, HUMIDITY, ALTITUDE, wind_ms, SOLARRADIATION, IMPERVIOUSNESS — no LST, no NDWI |',
    'Phase7-evalintro: 6→8 features table row'
)
# Also update the header range (will be refreshed after retrain, but remove stale "6" framing)
patch_md(
    '04e04c3f',
    '### Why R² values are moderate (0.526–0.552)',
    '### Why R² values are moderate',
    'Phase7-evalintro: remove stale R² range from header'
)

# ── [74] Phase 8 map intro — "only NDVI and NDBI vary" ────────────────────────
patch_md(
    '773c223e',
    'When predicting on the spatial grid, HUMIDITY, ALTITUDE, wind_ms and SOLARRADIATION are held fixed at their Q3 medians — only NDVI and NDBI vary across grid cells. If the model assigns significant weight to the meteorological features (which carry real predictive power for sensor anomalies but are constant on the grid), the spatial variation is suppressed.',
    'When predicting on the spatial grid, HUMIDITY, ALTITUDE, wind_ms and SOLARRADIATION are held fixed at their Q3 medians — only NDVI, NDBI and IMPERVIOUSNESS vary across grid cells (the latter sampled via a single EEA exportImage request for the Leuven bounding box). If the model assigns significant weight to the meteorological features (which carry real predictive power for sensor anomalies but are constant on the grid), the spatial variation is suppressed.',
    'Phase8-mapintro: NDVI+NDBI → NDVI+NDBI+IMPERVIOUSNESS'
)

# ── [76] Result-gridpred — "only NDVI, NDBI and B11 vary" ─────────────────────
patch_md(
    '724035ac',
    'only NDVI, NDBI and B11 (raw SWIR reflectance) vary spatially',
    'only NDVI, NDBI, B11 and IMPERVIOUSNESS vary spatially',
    'Result-gridpred: add IMPERVIOUSNESS to spatially-varying list'
)

# ── [79] Phase 9 intro — "two spatially-varying features (NDVI, NDBI)" ─────────
patch_md(
    'mc_intro',
    "because its two spatially-varying features (NDVI, NDBI) are physically grounded:\n\n- **NDVI** measures vegetation density — universally linked to evaporative cooling\n- **NDBI** measures built-up surface density — universally linked to heat absorption",
    "because its spatially-varying features (NDVI, NDBI, IMPERVIOUSNESS) are physically grounded:\n\n- **NDVI** measures vegetation density — universally linked to evaporative cooling\n- **NDBI** measures built-up surface density — universally linked to heat absorption\n- **IMPERVIOUSNESS** (EU HRL 2018, 10 m) captures permanent sealed-surface fraction, sampled per city via a single EEA exportImage request",
    'Phase9-intro: two→three spatially-varying features'
)

# ── Write ──────────────────────────────────────────────────────────────────────
nb['cells'] = cells
NB_PATH.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding='utf-8')
print('\nAll patches written.')
