"""
Fix cell [75] id=1f682815 (predict_anomaly_grid / Leuven single-city grid):
The scaler was retrained on 8 features but gX only has 7.
Add IMPERVIOUSNESS as 8th column — sampled via exportImage for the Leuven bbox,
consistent with how mc_predict does it for the multi-city cell.
"""

import json, pathlib, sys
sys.stdout.reconfigure(encoding='utf-8')

NB_PATH = pathlib.Path(
    r'c:\Users\wamy\Desktop\urban-heat-ai\notebooks\heat_monitoring_intelligence.ipynb'
)
nb = json.loads(NB_PATH.read_text(encoding='utf-8'))
cells = nb['cells']

CELL_ID = '1f682815'
idx = next(i for i, c in enumerate(cells) if c.get('id') == CELL_ID)

OLD = (
    "    yr_df = df[df['year']==year]\n"
    "    gX = np.column_stack([ndvi, ndbi,\n"
    "                          bands['B11'],\n"
    "                          np.full(n_grid, yr_df['HUMIDITY'].median()),       # fixed\n"
    "                          np.full(n_grid, yr_df['ALTITUDE'].median()),       # fixed\n"
    "                          np.full(n_grid, yr_df['wind_ms'].median()),        # fixed\n"
    "                          np.full(n_grid, yr_df['SOLARRADIATION'].median())]) # fixed"
)

NEW = (
    "    yr_df = df[df['year']==year]\n"
    "    # Sample imperviousness for Leuven bbox via EEA exportImage\n"
    "    try:\n"
    "        import requests as _req_lg\n"
    "        from rasterio.io import MemoryFile as _MemFil\n"
    "        _resp = _req_lg.get(\n"
    "            'https://image.discomap.eea.europa.eu/arcgis/rest/services/'\n"
    "            'GioLandPublic/HRL_ImperviousnessDensity_2018/ImageServer/exportImage',\n"
    "            params={\n"
    "                'bbox':      f'{LON_MIN},{LAT_MIN},{LON_MAX},{LAT_MAX}',\n"
    "                'bboxSR':    '4326',\n"
    "                'imageSR':   '4326',\n"
    "                'size':      '300,300',\n"
    "                'format':    'tiff',\n"
    "                'pixelType': 'U8',\n"
    "                'noData':    '255',\n"
    "                'f':         'image',\n"
    "            }, timeout=60)\n"
    "        _resp.raise_for_status()\n"
    "        with _MemFil(_resp.content) as _mf:\n"
    "            with _mf.open() as _ds:\n"
    "                _nd   = _ds.nodata if _ds.nodata is not None else 255\n"
    "                _samp = np.array([v[0] for v in _ds.sample(\n"
    "                    zip(grid_lons.tolist(), grid_lats.tolist()))], dtype=np.float64)\n"
    "        _samp = np.where((_samp == _nd) | (_samp < 0) | (_samp > 100), np.nan, _samp)\n"
    "        _im_med = float(np.nanmedian(_samp)) if not np.all(np.isnan(_samp)) else 50.0\n"
    "        imperv_g = np.where(np.isnan(_samp), _im_med, _samp)\n"
    "    except Exception:\n"
    "        imperv_g = np.full(n_grid,\n"
    "            float(merged['IMPERVIOUSNESS'].median())\n"
    "            if 'IMPERVIOUSNESS' in merged.columns else 50.0)\n"
    "    gX = np.column_stack([ndvi, ndbi,\n"
    "                          bands['B11'],\n"
    "                          np.full(n_grid, yr_df['HUMIDITY'].median()),       # fixed\n"
    "                          np.full(n_grid, yr_df['ALTITUDE'].median()),       # fixed\n"
    "                          np.full(n_grid, yr_df['wind_ms'].median()),        # fixed\n"
    "                          np.full(n_grid, yr_df['SOLARRADIATION'].median()), # fixed\n"
    "                          imperv_g])                                          # feature 8"
)

src = ''.join(cells[idx]['source'])
if OLD not in src:
    print('ERROR: pattern not found — first 600 chars of cell source:')
    print(src[:600])
    sys.exit(1)

src = src.replace(OLD, NEW, 1)
lines = src.splitlines(keepends=True)
if lines and lines[-1].endswith('\n'):
    lines[-1] = lines[-1].rstrip('\n')
cells[idx]['source'] = lines

nb['cells'] = cells
NB_PATH.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding='utf-8')
print(f'[{idx:02d}] id={CELL_ID}: imperviousness (feature 8) added to predict_anomaly_grid')
