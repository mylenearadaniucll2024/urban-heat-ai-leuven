import json, pathlib, sys
sys.stdout.reconfigure(encoding='utf-8')
nb = json.loads(pathlib.Path(r'c:\Users\wamy\Desktop\urban-heat-ai\notebooks\heat_monitoring_intelligence.ipynb').read_text(encoding='utf-8'))
cells = nb['cells']
print(f'Total cells: {len(cells)}')
checks = [(42,'FEATURES'), (39,'imd_sample_code'), (82,'mc_predict'), (85,'mc_v2_code')]
for idx, label in checks:
    c = cells[idx]
    src = ''.join(c.get('source', []))
    cid = c.get('id','?')
    print(f'\n=== [{idx}] id={cid} ({label}) first 650 chars ===')
    print(src[:650])
    if len(src) > 650:
        print('...')
