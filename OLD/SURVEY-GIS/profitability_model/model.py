"""
Profitability Model — Frozen Snapshot
======================================
Generated automatically from feature_meta.json.
Trained on 235 projects.  CV accuracy: 91.7% +/- 3.6% (10-fold).
Last updated: 2026-05-26

Usage:
    from profitability_model.model import predict
    result = predict(area_sqm=5000, survey_points=80, distance_km=15,
                     shape_index=1.4, quoted_price=12000, map_type_rz=1)
    print(result)
    # {'verdict': 'profitable', 'prob_profitable': 0.78, 'expected_margin_pct': 31.2}
"""

import math

# Training snapshot (2026-05-26)
N_TRAIN          = 235
CV_ACCURACY      = 0.917391
MARGIN_THRESHOLD = 20.0
BORDERLINE_LO    = 10.0

FEATURES = ['area_sqm_log', 'survey_points', 'distance_km', 'shape_index', 'quoted_price_log', 'map_type_rz']

FEATURE_LABELS = {"area_sqm_log": "שטח החלקה", "survey_points": "נקודות מדידה", "distance_km": "מרחק מהמשרד", "shape_index": "מורכבות צורה", "quoted_price_log": "מחיר ההצעה", "map_type_rz": "סוג מדידה (RZ)"}

# Scaler
_SCALER_MEAN  = [6.765426274, 190.8978723, 21.74525532, 1.559136596, 8.388836181, 0.9957446809]
_SCALER_SCALE = [1.222115181, 251.1468126, 22.60311935, 0.5266197741, 0.5296675316, 0.06509386613]

# Logistic Regression
_CLF_COEF      = [1.408297197, -1.86064324, 0.7081663328, 0.189178125, -2.316383877, -0.2957476094]
_CLF_INTERCEPT = 2.455544366

# Ridge Regression
_REG_COEF      = [-8.269183858, -16.98111513, 4.695398797, -2.742954924, -0.5630487196, 0.6989267279]
_REG_INTERCEPT = 66.68893617

# Feature importance (normalised %)
_IMPORTANCE = [0.003538679355, 0.960783505, 0.03291079796, 0.0002048343733, 0.002522601463, 3.958184807e-05]
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
