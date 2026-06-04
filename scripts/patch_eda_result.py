import json, pathlib, sys
sys.stdout.reconfigure(encoding='utf-8')

NB_PATH = pathlib.Path(
    r'c:\Users\wamy\Desktop\urban-heat-ai\notebooks\heat_monitoring_intelligence.ipynb'
)
nb = json.loads(NB_PATH.read_text(encoding='utf-8'))
cells = nb['cells']

idx = next(i for i, c in enumerate(cells) if c.get('id') == 'eda_result_md')

new_src = (
    "**Results — Feature Distribution & Correlation:**\n"
    "\n"
    "**Descriptive statistics (5,575 rows):**\n"
    "\n"
    "| Feature | Mean | Std | Min | Median | Max |\n"
    "|---|---|---|---|---|---|\n"
    "| NDVI | 0.361 | 0.153 | −0.002 | 0.391 | 0.601 |\n"
    "| NDBI | −0.097 | 0.106 | −0.338 | −0.107 | 0.174 |\n"
    "| B11 | 0.295 | 0.034 | 0.185 | 0.292 | 0.415 |\n"
    "| HUMIDITY (%) | 76.6 | 9.6 | 35.2 | 76.9 | 99.0 |\n"
    "| ALTITUDE (m) | 33.2 | 14.4 | 11 | 31 | 92 |\n"
    "| wind_ms | 0.225 | 0.304 | 0.000 | 0.119 | 3.140 |\n"
    "| SOLARRADIATION | 103.6 | 52.7 | 0 | 98.3 | 667 |\n"
    "| IMPERVIOUSNESS (%) | 40.6 | 32.7 | 0 | 35 | 100 |\n"
    "| **temp_anomaly (°C)** | **0.034** | **0.735** | **−4.40** | **−0.018** | **+7.78** |\n"
    "\n"
    "Notable observations:\n"
    "- `IMPERVIOUSNESS` spans the full 0–100% range with std = 32.7 — stations genuinely cover urban core, suburban and semi-rural settings.\n"
    "- `ALTITUDE` std = 14.4 m reflects Leuven’s valley-to-hillside topography (11–92 m range).\n"
    "- `wind_ms` mean = 0.22 m/s is low — citizen-science sensors are typically sited in sheltered spots (gardens, balconies), so wind readings systematically underestimate open-air values.\n"
    "- `temp_anomaly` is nearly zero-centred (mean = 0.034°C, median = −0.018°C) by construction. The extremes (−4.40°C to +7.78°C) are real outlier days; the model RMSE of 0.416°C is 57% of the 0.735°C std, confirming meaningful predictive skill beyond the mean.\n"
    "\n"
    "**Correlation with `temp_anomaly` (see heatmap):**\n"
    "- `IMPERVIOUSNESS` has the strongest positive correlation with the anomaly target — sealed surfaces suppress evaporative cooling directly. Consistent with its #1 SHAP rank.\n"
    "- `HUMIDITY` is negatively correlated — evaporative cooling effect across vegetated and shaded surfaces.\n"
    "- `NDVI` and `IMPERVIOUSNESS` are strongly negatively correlated with each other — low vegetation is a near-direct marker of sealed ground. This cross-feature correlation explains why NDVI was the second-ranked driver in the 7-feature model (it was proxying imperviousness) and why its SHAP importance collapsed 80% once IMPERVIOUSNESS was added directly.\n"
    "- `NDBI` and `IMPERVIOUSNESS` are positively correlated — both capture built-up density, but NDBI is a normalised spectral ratio while IMPERVIOUSNESS is an absolute sealed-surface fraction.\n"
    "- `B11` correlates positively with the target and with `IMPERVIOUSNESS` — raw SWIR reflectance is higher over dense impervious surfaces.\n"
    "\n"
    "**Box plots:**\n"
    "- *Left (anomaly by imperviousness quartile):* Median heat anomaly increases monotonically from Q1 (least sealed) to Q4 (most sealed), confirming the direct structural relationship SHAP identifies as the dominant predictive signal.\n"
    "- *Right (z-score distributions):* `SOLARRADIATION` and `temp_anomaly` show the widest spread and longest upper tails. `B11` has the tightest distribution (std = 0.034). No feature is pathologically skewed in a way that would require transformation for tree-based models."
)

lines = new_src.splitlines(keepends=True)
if lines and lines[-1].endswith('\n'):
    lines[-1] = lines[-1].rstrip('\n')
cells[idx]['source'] = lines

nb['cells'] = cells
NB_PATH.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding='utf-8')
print(f'OK [{idx:02d}] eda_result_md updated with actual numbers')
