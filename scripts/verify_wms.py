import json, pathlib, sys
sys.stdout.reconfigure(encoding='utf-8')
nb = json.loads(pathlib.Path(r'c:\Users\wamy\Desktop\urban-heat-ai\notebooks\heat_monitoring_intelligence.ipynb').read_text(encoding='utf-8'))
cells = nb['cells']

for cid, label, start_kw, chars in [
    ('imd_download_code', 'WMS setup',   '_IMD_IDENTIFY_URL', 500),
    ('imd_sample_code',   'WMS sample',  'def query_imperv',  700),
    ('mc_predict',        'mc_predict',  'exportImage',       600),
]:
    c = cells[next(i for i,c in enumerate(cells) if c.get('id')==cid)]
    src = ''.join(c.get('source', []))
    pos = src.find(start_kw)
    print(f'=== [{cid}] {label} (searching for {repr(start_kw)}) ===')
    if pos >= 0:
        print(src[pos:pos+chars])
    else:
        print('KEYWORD NOT FOUND — first 400 chars:')
        print(src[:400])
    print()
