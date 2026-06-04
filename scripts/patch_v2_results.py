"""
Update result markdown cells with v2 (8-feature) retrained numbers.

New metrics (80/20 random split, 8 features):
  RF:         RMSE=0.4257  MAE=0.2637  R2=0.5807  CV=0.4972
  XGB:        RMSE=0.4221  MAE=0.2587  R2=0.5878  CV=0.4904
  XGB tuned:  RMSE=0.4220  MAE=0.2576  R2=0.5880  CV=0.4841
  Stack:      RMSE=0.4163  MAE=0.2550  R2=0.5991
  CNN:        RMSE=0.5273  MAE=0.3099  R2=0.3691  (unchanged)

LOSOCV: RF RMSE=0.575 +/- 0.460  (gap +0.078 deg vs standard CV)
"""

import json, pathlib, sys, re
sys.stdout.reconfigure(encoding='utf-8')

NB_PATH = pathlib.Path(
    r'c:\Users\wamy\Desktop\urban-heat-ai\notebooks\heat_monitoring_intelligence.ipynb'
)
nb = json.loads(NB_PATH.read_text(encoding='utf-8'))
cells = nb['cells']

# Narrow no-break space used in these cells
N = ' '


def find(cell_id):
    for i, c in enumerate(cells):
        if c.get('id') == cell_id:
            return i, c
    raise ValueError(f'{cell_id!r} not found')


def patch_md(cell_id, old, new, label):
    idx, c = find(cell_id)
    src = ''.join(c['source'])
    if old not in src:
        print(f'  SKIP [{idx:02d}] {label}: pattern not found')
        return
    src = src.replace(old, new, 1)
    lines = src.splitlines(keepends=True)
    if lines and lines[-1].endswith('\n'):
        lines[-1] = lines[-1].rstrip('\n')
    c['source'] = lines
    print(f'  OK   [{idx:02d}] {label}')


# ── [49] Result-RF ─────────────────────────────────────────────────────────────
patch_md(
    '8365e1c4',
    '**Result:** Random Forest achieves **RMSE = 0.453°C, MAE = 0.274°C, R² = 0.526**. The 5-fold CV RMSE (0.514 ± 0.046) closely tracks the test RMSE, confirming stable generalisation with no overfitting. An R² of 0.526 means the model explains 52.6% of spatial anomaly variance using 8 features and 5,575 rows — consistent with published UHI tabular models on similar sensor networks (Venter et al. 2020: R² = 0.45–0.58). The remaining ∼47% unexplained variance reflects sensor siting quality, sub-pixel land-cover heterogeneity, and temporal mismatches within the ±7-day scene window.',
    '**Result:** Random Forest achieves **RMSE = 0.426°C, MAE = 0.264°C, R² = 0.581**. The 5-fold CV RMSE (0.497) closely tracks the test RMSE, confirming stable generalisation with no overfitting. An R² of 0.581 means the model explains 58.1% of spatial anomaly variance using 8 features and 5,575 rows — consistent with published UHI tabular models on similar sensor networks (Venter et al. 2020: R² = 0.45–0.58). The remaining ∼42% unexplained variance reflects sensor siting quality, sub-pixel land-cover heterogeneity, and temporal mismatches within the ±7-day scene window.',
    'Result-RF: update to v2 numbers'
)

# ── [52] Result-XGB ────────────────────────────────────────────────────────────
patch_md(
    '31c5c1f5',
    '**Result:** XGBoost slightly outperforms Random Forest: **RMSE = 0.445°C, MAE = 0.269°C, R² = 0.541**. The 5-fold CV RMSE (0.508 ± 0.047) is equally stable. The marginal gain over RF (0.015 in R², 0.008°C in RMSE) is expected — gradient boosting corrects residual errors sequentially and handles feature interactions more efficiently, but with 8 features and 5,575 rows both models are near their ceiling with this data. The improvement is algorithmic rather than data-driven.',
    '**Result:** XGBoost slightly outperforms Random Forest: **RMSE = 0.422°C, MAE = 0.259°C, R² = 0.588**. The 5-fold CV RMSE (0.490) is equally stable. The marginal gain over RF (0.007 in R², 0.004°C in RMSE) is expected — gradient boosting corrects residual errors sequentially and handles feature interactions more efficiently, but with 8 features and 5,575 rows both models are near their ceiling with this data. The improvement is algorithmic rather than data-driven.',
    'Result-XGB: update to v2 numbers'
)

# ── [60] Result-XGBtuned ───────────────────────────────────────────────────────
patch_md(
    '9b3fca19',
    'The tuned model achieves **RMSE = 0.440°C, R² = 0.552** — a consistent but modest improvement over default XGBoost (RMSE = 0.445, R² = 0.541). The small gain from tuning suggests the model was already near-optimal for this feature set and dataset size.',
    'The tuned model achieves **RMSE = 0.422°C, R² = 0.588** — a negligible improvement over default XGBoost (RMSE = 0.422, R² = 0.588). The near-zero gain from tuning confirms the model is already at its ceiling for this feature set and dataset size.',
    'Result-XGBtuned: update to v2 numbers'
)

# ── [63] Result-Stack (stack_interp) ──────────────────────────────────────────
# These cells use narrow no-break space (U+202F) around = signs
patch_md(
    'stack_interp',
    f'The stacked model improves R² by +0.007 over the best individual model (XGBoost tuned, R²{N}={N}0.571 → 0.578).',
    f'The stacked model improves R² by +0.011 over the best individual model (XGBoost tuned, R²{N}={N}0.588 → 0.599).',
    'Result-Stack: update R2 improvement'
)

# ── [66] Result-comparison (9d0e5e6b) ─────────────────────────────────────────
patch_md(
    '9d0e5e6b',
    f'The **Stacked RF+XGB ensemble** is the best-performing model: **RMSE{N}={N}0.427°C, MAE{N}={N}0.261°C, R²{N}={N}0.578**. Random Forest (R²{N}={N}0.552) and XGBoost untuned (R²{N}={N}0.573) are within 0.011°C RMSE of each other — practically equivalent for spatial prediction. Hyperparameter tuning of XGBoost yields marginal gains (R²{N}={N}0.571 → 0.578 after stacking). The CNN trails at R²{N}={N}0.369 (100 epochs, Tesla T4 GPU via Google Colab) and is excluded from best-model selection — spatial patch features alone cannot yet match tabular ensemble accuracy on this dataset size. The ∼0.07°C gap between CV RMSE (∼0.50) and test RMSE (∼0.43) across all tabular models indicates mild optimism in the cross-validation estimate, consistent with the spatial autocorrelation leakage quantified by LOSOCV (RMSE{N}={N}0.592 ± 0.460).',
    f'The **Stacked RF+XGB ensemble** is the best-performing model: **RMSE{N}={N}0.416°C, MAE{N}={N}0.255°C, R²{N}={N}0.599**. Random Forest (R²{N}={N}0.581) and XGBoost untuned (R²{N}={N}0.588) are within 0.004°C RMSE of each other — practically equivalent for spatial prediction. Hyperparameter tuning of XGBoost yields negligible gains (R²{N}={N}0.588 → 0.599 after stacking). The CNN trails at R²{N}={N}0.369 (100 epochs, Tesla T4 GPU via Google Colab) and is excluded from best-model selection — spatial patch features alone cannot yet match tabular ensemble accuracy on this dataset size. The ∼0.07°C gap between CV RMSE (∼0.49) and test RMSE (∼0.42) across all tabular models indicates mild optimism in the cross-validation estimate, consistent with the spatial autocorrelation leakage quantified by LOSOCV (RMSE{N}={N}0.575 ± 0.460).',
    'Result-comparison: update all v2 numbers'
)

# ── Write ──────────────────────────────────────────────────────────────────────
nb['cells'] = cells
NB_PATH.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding='utf-8')
print('\nAll v2 result patches written.')
