"""
Update SHAP cells after v2 retrain — IMPERVIOUSNESS is now the dominant driver.

Changes:
  [67] shap_md        — HUMIDITY → IMPERVIOUSNESS as dominant; keep NDVI caveat
  [72] imd_shap_v2_md — update intro to reflect actual finding + v1/v2 comparison intro
  [73] imd_shap_v2_code — add 7-feature RF comparison (same split, no IMPERVIOUSNESS)
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


def set_source(cell_id, new_source, label):
    idx, c = find(cell_id)
    lines = new_source.splitlines(keepends=True)
    if lines and lines[-1].endswith('\n'):
        lines[-1] = lines[-1].rstrip('\n')
    c['source'] = lines
    print(f'  OK   [{idx:02d}] {label}')


# ── [67] shap_md ──────────────────────────────────────────────────────────────
set_source('shap_md', """\
### 8a. SHAP Feature Importance (Explainability)

SHAP (SHapley Additive exPlanations) shows **which features drive each prediction** — not just global importance, but the per-sample contribution of each input. Red dots push the prediction higher (hotter anomaly), blue dots lower (cooler).

**Reading the results (8-feature model):**
- **IMPERVIOUSNESS** is the dominant driver. The EU HRL 2018 sealed-surface fraction consistently pushes anomaly predictions positive — permanently sealed surfaces suppress evaporative cooling and retain daytime heat, directly linking land-cover structure to the measured temperature anomaly.
- **HUMIDITY** is the second-strongest driver. High-humidity days amplify the urban heat island effect because moisture suppresses radiative cooling differently across land cover types — a physically meaningful result.
- **NDVI direction caveat:** High NDVI values appear to correlate with *positive* anomalies in this training set, which is counter-intuitive (more vegetation should cool). This is a known confounding effect in small-sample spatial regression: our Sentinel-2 scenes are all late July–August (peak greenness), and suburban stations with higher NDVI tend to sit at lower altitudes with higher solar exposure. The model picks up this spatial correlation rather than the true causal relationship. More training scenes across seasons and cities would be needed for the NDVI cooling signal to emerge cleanly.
- **NDBI** correctly pushes anomalies positive (more built-up surface = warmer), consistent with physical expectations.
""", 'shap_md: HUMIDITY → IMPERVIOUSNESS as dominant')

# ── [72] imd_shap_v2_md ───────────────────────────────────────────────────────
set_source('imd_shap_v2_md', """\
### 8c. SHAP Feature Importance — v1 (7 features) vs v2 (8 features)

The cell below compares SHAP beeswarms before and after adding IMPERVIOUSNESS. A quick 7-feature RF is retrained on the same 80/20 split for the v1 baseline — keeping the comparison fair (same data, same hyperparameters, only the feature set differs).

**Key finding:** IMPERVIOUSNESS becomes the **#1 ranked feature** in the 8-feature model, ranking above HUMIDITY and NDVI. This confirms that the sealed-surface fraction carries structural signal about urban heat that spectral indices do not fully capture — NDBI measures the proportion of built-up surface but not the absolute imperviousness fraction, which is more directly linked to evaporative suppression and thermal mass.
""", 'imd_shap_v2_md: update with actual finding + comparison intro')

# ── [73] imd_shap_v2_code ────────────────────────────────────────────────────
set_source('imd_shap_v2_code', """\
# ── SHAP comparison: v1 (7 features) vs v2 (8 features) ─────────────────────
import shap as _shap
from sklearn.ensemble import RandomForestRegressor as _RF7
from sklearn.preprocessing import StandardScaler as _SS7

# v2: current 8-feature RF
_explainer_v2 = _shap.TreeExplainer(rf)
_shap_vals_v2 = _explainer_v2.shap_values(X_test)

plt.figure(figsize=(10, 6))
_shap.summary_plot(_shap_vals_v2, X_test, feature_names=FEATURES, show=False)
plt.title('SHAP — RF v2 (8 features incl. IMPERVIOUSNESS)', fontsize=13)
plt.tight_layout()
plt.savefig('shap_rf_v2_summary.png', dpi=150, bbox_inches='tight')
plt.show()

# v1: quick 7-feature RF — same 80/20 split, same n_estimators, no IMPERVIOUSNESS
_feat7 = FEATURES[:7]
_sc7   = _SS7().fit(X_train[:, :7])
_Xtr7, _Xte7 = _sc7.transform(X_train[:, :7]), _sc7.transform(X_test[:, :7])
_rf7   = _RF7(n_estimators=100, random_state=42)
_rf7.fit(_Xtr7, y_train)

_explainer7   = _shap.TreeExplainer(_rf7)
_shap_vals_v1 = _explainer7.shap_values(_Xte7)

plt.figure(figsize=(10, 6))
_shap.summary_plot(_shap_vals_v1, _Xte7, feature_names=_feat7, show=False)
plt.title('SHAP — RF v1 (7 features, no IMPERVIOUSNESS)', fontsize=13)
plt.tight_layout()
plt.savefig('shap_rf_v1_summary.png', dpi=150, bbox_inches='tight')
plt.show()

# Ranked mean |SHAP| — side-by-side table
_rank_v2 = sorted(zip(FEATURES, np.abs(_shap_vals_v2).mean(0)), key=lambda x: -x[1])
_rank_v1 = dict(zip(_feat7, np.abs(_shap_vals_v1).mean(0)))

print(f'{"Rank":>4}  {"Feature":<22}  {"v2 |SHAP|":>9}  {"v1 |SHAP|":>9}')
print('-' * 52)
for _r, (_f, _v2val) in enumerate(_rank_v2, 1):
    _v1val = _rank_v1.get(_f, float('nan'))
    _v1s   = f'{_v1val:.4f}' if _f in _rank_v1 else '   —   '
    _tag   = '  ◄ NEW' if _f == 'IMPERVIOUSNESS' else ''
    print(f'{_r:>4}  {_f:<22}  {_v2val:>9.4f}  {_v1s:>9}{_tag}')

_imd_r  = next(_r for _r, (_f, _) in enumerate(_rank_v2, 1) if _f == 'IMPERVIOUSNESS')
_ndbi_r = next(_r for _r, (_f, _) in enumerate(_rank_v2, 1) if _f == 'NDBI')
print(f'\nIMPERVIOUSNESS rank: {_imd_r}  |  NDBI rank: {_ndbi_r}')
if _imd_r < _ndbi_r:
    print('→ IMPERVIOUSNESS ranks ABOVE NDBI — adds structural signal beyond spectral indices.')
else:
    print('→ IMPERVIOUSNESS ranks below NDBI — spectral indices capture most built-up signal.')
print('shap_rf_v1_summary.png and shap_rf_v2_summary.png saved.')
""", 'imd_shap_v2_code: add 7-feature RF comparison')

# ── Write ──────────────────────────────────────────────────────────────────────
nb['cells'] = cells
NB_PATH.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding='utf-8')
print('\nSHAP comparison patches written.')
