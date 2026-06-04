import json, pathlib, sys
sys.stdout.reconfigure(encoding='utf-8')
nb = json.loads(pathlib.Path(r'c:\Users\wamy\Desktop\urban-heat-ai\notebooks\heat_monitoring_intelligence.ipynb').read_text(encoding='utf-8'))
cells = nb['cells']
src = ''.join(cells[82].get('source', []))
start = src.find('gX = np.column_stack')
print('=== mc_predict gX column_stack ===')
print(src[start:start+350])
