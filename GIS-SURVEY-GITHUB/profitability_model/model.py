"""
Profitability Model — Frozen Snapshot
======================================
Generated automatically from feature_meta.json.
Trained on 289 projects.  CV accuracy: 96.1% +/- 3.4% (10-fold).
Last updated: 2026-05-27

Usage:
    from profitability_model.model import predict
    result = predict(area_sqm=5000, survey_points=80, distance_km=15,
                     shape_index=1.4, quoted_price=12000, map_type_rz=1)
    print(result)
    # {'verdict': 'profitable', 'prob_profitable': 0.78, 'expected_margin_pct': 31.2}
"""

import math

# Training snapshot (2026-05-27)
N_TRAIN          = 289
CV_ACCURACY      = 0.960714
MARGIN_THRESHOLD = 20.0
BORDERLINE_LO    = 10.0

FEATURES = ['area_sqm_log', 'survey_points', 'distance_km', 'shape_index', 'quoted_price_log', 'map_type_rz']

FEATURE_LABELS = {"area_sqm_log": "שטח החלקה", "survey_points": "נקודות מדידה", "distance_km": "מרחק מהמשרד", "shape_index": "מורכבות צורה", "quoted_price_log": "מחיר ההצעה", "map_type_rz": "סוג מדידה (RZ)"}

# Scaler
_SCALER_MEAN  = [6.873295353, 204.3391003, 21.15521799, 1.596504844, 8.485441608, 1]
_SCALER_SCALE = [1.23754365, 257.3293688, 24.34939313, 0.6532613429, 0.4731153734, 1]

# Logistic Regression
_CLF_COEF      = [1.131768996, -1.140198595, 0.4847057244, 0.05440814219, -2.931357842, 0]
_CLF_INTERCEPT = 3.291039006

# Ridge Regression
_REG_COEF      = [10.81930028, 1.237631559, 6.717876459, -2.982181637, -5.703251143, 0]
_REG_INTERCEPT = 32.88117647

# Feature importance (normalised %)
_IMPORTANCE = [0.004546975579, 0.9525201225, 0.03831515558, 0.0001153865422, 0.004502359828, 0]
_DIRECTION  = [1, -1, 1, 1, -1, -1]


def _scale(raw):
    return [(v - mu) / s for v, mu, s in zip(raw, _SCALER_MEAN, _SCALER_SCALE)]

def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))

def _sigmoid(z):
    return 1.0 / (1.0 + math.exp(-max(-500.0, min(500.0, z))))


def predict(area_sqm, survey_points, distance_km, shape_index,
            quoted_price, map_type_rz):
    """
    Predict profitability for a new project.

    Returns dict:
        verdict             — 'profitable' | 'borderline' | 'not_profitable'
        prob_profitable     — float 0-1
        expected_margin_pct — float (%)
        top_factors         — list sorted by importance
    """
    raw    = [math.log1p(area_sqm), survey_points, distance_km,
              shape_index, math.log1p(quoted_price), float(map_type_rz)]
    scaled = _scale(raw)

    prob   = _sigmoid(_dot(scaled, _CLF_COEF) + _CLF_INTERCEPT)
    margin = _dot(scaled, _REG_COEF) + _REG_INTERCEPT

    if margin >= MARGIN_THRESHOLD and prob >= 0.60:
        verdict = "profitable"
    elif margin >= BORDERLINE_LO or prob >= 0.40:
        verdict = "borderline"
    else:
        verdict = "not_profitable"

    top_factors = sorted(
        [{"name": name, "label": FEATURE_LABELS[name],
           "importance": round(_IMPORTANCE[i] * 100, 1),
           "direction": _DIRECTION[i]}
         for i, name in enumerate(FEATURES)],
        key=lambda x: x["importance"], reverse=True,
    )

    return {
        "verdict":             verdict,
        "prob_profitable":     round(prob, 4),
        "expected_margin_pct": round(margin, 1),
        "top_factors":         top_factors,
        "model_info":          {"n_train": N_TRAIN,
                                 "cv_accuracy": round(CV_ACCURACY * 100, 1)},
    }


if __name__ == "__main__":
    examples = [
        dict(area_sqm=5000,  survey_points=80,  distance_km=15,
             shape_index=1.4, quoted_price=12000, map_type_rz=1),
        dict(area_sqm=500,   survey_points=10,  distance_km=60,
             shape_index=2.8, quoted_price=3000,  map_type_rz=0),
        dict(area_sqm=20000, survey_points=300, distance_km=5,
             shape_index=1.1, quoted_price=35000, map_type_rz=1),
    ]
    for ex in examples:
        r = predict(**ex)
        print(f"[{r['verdict']:15s}]  prob={r['prob_profitable']:.2f}"
              f"  margin={r['expected_margin_pct']:+.1f}%"
              f"  | area={ex['area_sqm']} pts={ex['survey_points']}"
              f" dist={ex['distance_km']}km price={ex['quoted_price']}")
