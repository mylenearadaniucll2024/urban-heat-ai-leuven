import json, pathlib, sys
sys.stdout.reconfigure(encoding='utf-8')
nb = json.loads(pathlib.Path(r'c:\Users\wamy\Desktop\urban-heat-ai\notebooks\heat_monitoring_intelligence.ipynb').read_text(encoding='utf-8'))
cells = nb['cells']

# Check mc_predict for imperv_grid and gX 8-column stack
mc = cells[82]
src = ''.join(mc.get('source', []))
# Find the imperv_grid section
start = src.find('# Feature 8')
print('=== mc_predict: imperv_grid section ===')
print(src[start:start+600])

print()
# Check cell sequence around insertions
print('=== Cell sequence [35-44] ===')
for i in range(35, 45):
    c = cells[i]
    s = ''.join(c.get('source', []))[:70].replace('\n', ' ')
    print(f'  [{i:02d}] id={c.get("id","?"):22s} type={c["cell_type"]:8s} | {s}')

print()
print('=== Cell sequence [68-76] ===')
for i in range(68, 77):
    c = cells[i]
    s = ''.join(c.get('source', []))[:70].replace('\n', ' ')
    print(f'  [{i:02d}] id={c.get("id","?"):22s} type={c["cell_type"]:8s} | {s}')

print()
print('=== Cell sequence [80-89] ===')
for i in range(80, 90):
    c = cells[i]
    s = ''.join(c.get('source', []))[:70].replace('\n', ' ')
    print(f'  [{i:02d}] id={c.get("id","?"):22s} type={c["cell_type"]:8s} | {s}')
