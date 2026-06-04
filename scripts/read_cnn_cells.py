import json, pathlib, sys
sys.stdout.reconfigure(encoding='utf-8')
nb = json.loads(pathlib.Path(r'c:\Users\wamy\Desktop\urban-heat-ai\notebooks\heat_monitoring_intelligence.ipynb').read_text(encoding='utf-8'))
cells = nb['cells']
for cid in ['8bc3791e', 'f4c0b9e9', 'save_colab_data']:
    idx = next(i for i,c in enumerate(cells) if c.get('id') == cid)
    print(f'=== [{idx}] id={cid} ===')
    print(''.join(cells[idx].get('source', [])))
    print()
