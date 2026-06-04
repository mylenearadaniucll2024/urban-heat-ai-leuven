"""
Fix: ArcGIS ImageServer /identify was getting 'NoData' because the lon/lat
coordinates were sent without a spatialReference — the server interpreted them
in the raster's native EPSG:3035 (metre units), where 4.7, 50.8 is far outside
the coverage area.

Fix: wrap geometry as JSON with spatialReference: {"wkid": 4326}.
Applies to imd_download_code (liveness test) and imd_sample_code (loop).
"""

import json as _json, pathlib, sys
sys.stdout.reconfigure(encoding='utf-8')

NB_PATH = pathlib.Path(
    r'c:\Users\wamy\Desktop\urban-heat-ai\notebooks\heat_monitoring_intelligence.ipynb'
)
nb = _json.loads(NB_PATH.read_text(encoding='utf-8'))
cells = nb['cells']


def find_cell(cell_id):
    for i, c in enumerate(cells):
        if c.get('id') == cell_id:
            return i
    raise ValueError(f'{cell_id!r} not found')


def fix_source(source_list, old, new):
    text = ''.join(source_list)
    if old not in text:
        raise ValueError(f'Pattern not found:\n  {old!r}')
    text = text.replace(old, new, 1)
    lines = text.splitlines(keepends=True)
    if lines and lines[-1].endswith('\n'):
        lines[-1] = lines[-1].rstrip('\n')
    return lines


# ── Fix 1: liveness test in imd_download_code ─────────────────────────────────
OLD_TEST_GEOM = (
    "            'geometry':     '4.7005,50.8798',\n"
    "            'geometryType': 'esriGeometryPoint',"
)
NEW_TEST_GEOM = (
    "            'geometry':     '{\"x\":4.7005,\"y\":50.8798,\"spatialReference\":{\"wkid\":4326}}',\n"
    "            'geometryType': 'esriGeometryPoint',"
)

idx = find_cell('imd_download_code')
cells[idx]['source'] = fix_source(cells[idx]['source'], OLD_TEST_GEOM, NEW_TEST_GEOM)
print(f'[{idx:02d}] imd_download_code: geometry SR fix applied')

# ── Fix 2: query loop in imd_sample_code ──────────────────────────────────────
# Replace the simple 'lon,lat' string with JSON geometry + spatialReference
OLD_LOOP_GEOM = (
    "            _r = _req_imd.get(_IMD_IDENTIFY_URL, params={\n"
    "                'geometry':       f'{lon},{lat}',\n"
    "                'geometryType':   'esriGeometryPoint',\n"
    "                'returnGeometry': 'false',\n"
    "                'f':              'json',\n"
    "            }, timeout=10)"
)
NEW_LOOP_GEOM = (
    "            _geom = f'{{\"x\":{lon},\"y\":{lat},\"spatialReference\":{{\"wkid\":4326}}}}'\n"
    "            _r = _req_imd.get(_IMD_IDENTIFY_URL, params={\n"
    "                'geometry':       _geom,\n"
    "                'geometryType':   'esriGeometryPoint',\n"
    "                'returnGeometry': 'false',\n"
    "                'f':              'json',\n"
    "            }, timeout=10)"
)

idx = find_cell('imd_sample_code')
cells[idx]['source'] = fix_source(cells[idx]['source'], OLD_LOOP_GEOM, NEW_LOOP_GEOM)
print(f'[{idx:02d}] imd_sample_code: geometry SR fix applied')

nb['cells'] = cells
NB_PATH.write_text(_json.dumps(nb, ensure_ascii=False, indent=1), encoding='utf-8')
print('\nDone. Re-run cell [37] to confirm the test pixel returns a numeric value.')
