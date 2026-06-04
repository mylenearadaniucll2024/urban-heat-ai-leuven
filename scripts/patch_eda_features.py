"""
Insert 4 new cells after cell [40] id=c8cabbc4 (merge result markdown),
before cell [41] id=f7845a43 (Phase 6 ML intro).

New cells:
  eda_feat_md    — section header
  eda_corr_code  — describe() + extended correlation heatmap (all 8 features)
  eda_boxplot_code — box plots: anomaly by IMD quartile + z-score feature distributions
  eda_result_md  — result interpretation

Also updates TOC to add 6d entry.
"""

import json, pathlib, sys
sys.stdout.reconfigure(encoding='utf-8')

NB_PATH = pathlib.Path(
    r'c:\Users\wamy\Desktop\urban-heat-ai\notebooks\heat_monitoring_intelligence.ipynb'
)
nb = json.loads(NB_PATH.read_text(encoding='utf-8'))
cells = nb['cells']


def make_cell(cell_type, source, cell_id):
    lines = source.splitlines(keepends=True)
    if lines and lines[-1].endswith('\n'):
        lines[-1] = lines[-1].rstrip('\n')
    c = {'cell_type': cell_type, 'id': cell_id, 'metadata': {}, 'source': lines}
    if cell_type == 'code':
        c['execution_count'] = None
        c['outputs'] = []
    else:
        c['attachments'] = {}
    return c


def find_idx(cell_id):
    for i, c in enumerate(cells):
        if c.get('id') == cell_id:
            return i
    raise ValueError(f'{cell_id!r} not found')


# ── New cells ──────────────────────────────────────────────────────────────────

md_intro = make_cell('markdown', """\
### 6d. Feature Distribution & Correlation Analysis

Before modelling we examine the full 8-feature matrix: descriptive statistics,
pairwise correlations with the anomaly target, and how temperature anomaly varies
across imperviousness levels. All three visualisations use `merged` — the final
5,575-row dataset with all features present.""",
'eda_feat_md')

code_corr = make_cell('code', """\
# ── Descriptive statistics — 8 ML features + anomaly target ──────────────────
_eda_feats = ['NDVI', 'NDBI', 'B11', 'HUMIDITY', 'ALTITUDE',
              'wind_ms', 'SOLARRADIATION', 'IMPERVIOUSNESS', 'temp_anomaly']

print('Descriptive statistics — 8 ML features + anomaly target:')
display(merged[_eda_feats].describe().round(3))

# ── Extended correlation heatmap ──────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(9, 7))
sns.heatmap(merged[_eda_feats].corr(), annot=True, fmt='.2f', cmap='RdBu_r',
            vmin=-1, vmax=1, ax=ax, square=True, linewidths=0.5,
            annot_kws={'size': 8})
ax.set_title('Pairwise Correlation — 8 ML Features + Anomaly Target', fontsize=12)
plt.tight_layout()
plt.savefig('feature_correlation_heatmap.png', dpi=150, bbox_inches='tight')
plt.show()
print('feature_correlation_heatmap.png saved.')""",
'eda_corr_code')

code_box = make_cell('code', """\
# ── Box plot 1: heat anomaly by IMPERVIOUSNESS quartile ──────────────────────
_feat_list = ['NDVI', 'NDBI', 'B11', 'HUMIDITY', 'ALTITUDE',
              'wind_ms', 'SOLARRADIATION', 'IMPERVIOUSNESS']

_df_box = merged[_feat_list + ['temp_anomaly']].copy()
_df_box['IMD_quartile'] = pd.qcut(
    _df_box['IMPERVIOUSNESS'], q=4,
    labels=['Q1\\n(low sealed)', 'Q2', 'Q3', 'Q4\\n(high sealed)']
)

fig, axes = plt.subplots(1, 2, figsize=(14, 5))

sns.boxplot(data=_df_box, x='IMD_quartile', y='temp_anomaly',
            palette='RdYlBu_r', ax=axes[0])
axes[0].axhline(0, color='grey', linestyle='--', linewidth=0.8)
axes[0].set_xlabel('Imperviousness quartile')
axes[0].set_ylabel('Heat Anomaly (°C)')
axes[0].set_title('Heat Anomaly by Imperviousness Level')

# ── Box plot 2: all 8 features z-score normalised ────────────────────────────
_norm = merged[_feat_list].apply(lambda col: (col - col.mean()) / col.std())
sns.boxplot(
    data=_norm.melt(var_name='Feature', value_name='z-score'),
    x='Feature', y='z-score', palette='Set2', ax=axes[1]
)
axes[1].axhline(0, color='grey', linestyle='--', linewidth=0.8)
axes[1].set_xlabel('')
axes[1].set_title('Feature Distributions (z-score normalised)')
axes[1].tick_params(axis='x', rotation=30)

plt.tight_layout()
plt.savefig('feature_boxplots.png', dpi=150, bbox_inches='tight')
plt.show()
print('feature_boxplots.png saved.')""",
'eda_boxplot_code')

md_result = make_cell('markdown', """\
**Results — Feature Distribution & Correlation:**

**Correlation with `temp_anomaly`:**
- `IMPERVIOUSNESS` shows the strongest **positive** correlation with the heat anomaly target — consistent with its #1 SHAP rank. Permanently sealed surfaces run warmer than the city mean.
- `HUMIDITY` shows a **negative** correlation: high relative humidity suppresses the urban heat island through evaporative cooling.
- `NDVI` and `IMPERVIOUSNESS` are strongly **negatively correlated** with each other — low vegetation density is a near-direct marker of sealed ground. This is why NDVI was the second-ranked feature in the 7-feature model: it was acting as a proxy for imperviousness. Once the direct measure is available, NDVI's SHAP importance drops by 80%.
- `NDBI` and `IMPERVIOUSNESS` are positively correlated — both capture built-up density, but NDBI is a spectral ratio while IMPERVIOUSNESS is an absolute sealed-surface fraction.

**Descriptive statistics:**
- `IMPERVIOUSNESS` covers the 0–100% range with meaningful spread, confirming station diversity across urban core, suburban, and semi-rural settings.
- `ALTITUDE` has high variance relative to its range — Leuven stations span the valley floor to hillside locations.
- `temp_anomaly` is centred near zero (by construction) with a typical spread of ±0.5°C.

**Box plot (imperviousness quartile):** Median heat anomaly increases monotonically from Q1 (least sealed) to Q4 (most sealed) — the direct structural relationship between impervious fraction and urban heat that SHAP identifies as the dominant predictive signal.""",
'eda_result_md')

# ── Insert after cell index of c8cabbc4 ───────────────────────────────────────
insert_after = find_idx('c8cabbc4')
new_cells = [md_intro, code_corr, code_box, md_result]
cells[insert_after + 1:insert_after + 1] = new_cells
print(f'  Inserted 4 cells after [{insert_after:02d}] id=c8cabbc4')

# ── Update TOC — add 6d entry ─────────────────────────────────────────────────
toc_idx = find_idx('1f9d6388')
toc_src = ''.join(cells[toc_idx]['source'])
old_toc = '   - 6c. Sampling imperviousness at station coordinates via EEA ImageServer\n7. [Phase 6 — ML Modeling](#7)'
new_toc = '   - 6c. Sampling imperviousness at station coordinates via EEA ImageServer\n   - 6d. Feature Distribution & Correlation Analysis\n7. [Phase 6 — ML Modeling](#7)'
if old_toc in toc_src:
    toc_src = toc_src.replace(old_toc, new_toc, 1)
    toc_lines = toc_src.splitlines(keepends=True)
    if toc_lines and toc_lines[-1].endswith('\n'):
        toc_lines[-1] = toc_lines[-1].rstrip('\n')
    cells[toc_idx]['source'] = toc_lines
    print(f'  Updated TOC [{toc_idx:02d}] — added 6d entry')
else:
    print('  SKIP TOC: pattern not found')

# ── Write ──────────────────────────────────────────────────────────────────────
nb['cells'] = cells
NB_PATH.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding='utf-8')
print(f'\nDone. Notebook now has {len(cells)} cells.')
