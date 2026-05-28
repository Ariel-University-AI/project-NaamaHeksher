"""
Profitability Model Trainer
============================
Train a Logistic Regression (classification) + Ridge Regression (margin estimation)
from training_data.json.  Run this script once to produce model artifacts:

    python profitability_model/train.py

Outputs (written next to this file):
    model_clf.pkl      — LogisticRegression: predicts profitable / not
    model_reg.pkl      — Ridge: predicts expected profit_margin_pct
    scaler.pkl         — StandardScaler for both models
    feature_meta.json  — feature names, thresholds, training stats

Pure-numpy implementation — no scikit-learn / scipy dependency required.
"""

import json, math, pickle, sys
from pathlib import Path

import numpy as np

_HERE = Path(__file__).parent
_DB   = _HERE.parent / "training_data.json"

FEATURES = [
    "area_sqm_log",       # log(1 + area_sqm)
    "survey_points",
    "distance_km",
    "shape_index",
    "quoted_price_log",   # log(1 + quoted_price)
    "map_type_rz",        # 1=RZ, 0=other
]

FEATURE_LABELS_HE = {
    "area_sqm_log":      "שטח החלקה",
    "survey_points":     "נקודות מדידה",
    "distance_km":       "מרחק מהמשרד",
    "shape_index":       "מורכבות צורה",
    "quoted_price_log":  "מחיר ההצעה",
    "map_type_rz":       "סוג מדידה (RZ)",
}

MARGIN_THRESHOLD = 20.0
BORDERLINE_LO    = 10.0


# ── Pure-numpy model classes (pickle-compatible, same API as sklearn) ──────

class _NumpyScaler:
    def __init__(self):
        self.mean_  = None
        self.scale_ = None

    def fit_transform(self, X: np.ndarray) -> np.ndarray:
        self.mean_  = X.mean(axis=0)
        self.scale_ = X.std(axis=0)
        self.scale_[self.scale_ == 0] = 1.0   # avoid division by zero
        return (X - self.mean_) / self.scale_

    def transform(self, X) -> np.ndarray:
        X = np.array(X, dtype=float)
        return (X - self.mean_) / self.scale_


class _NumpyLogisticRegression:
    """Binary logistic regression with L2 regularisation, trained by gradient descent."""

    def __init__(self, C=1.0, max_iter=1000, tol=1e-5, class_weight="balanced"):
        self.C            = C
        self.max_iter     = max_iter
        self.tol          = tol
        self.class_weight = class_weight
        self.coef_        = None   # shape (1, n_features)
        self.intercept_   = None   # shape (1,)

    @staticmethod
    def _sigmoid(z):
        return 1.0 / (1.0 + np.exp(-np.clip(z, -500, 500)))

    def fit(self, X: np.ndarray, y: np.ndarray):
        n, p = X.shape
        lam  = 1.0 / (self.C * n)

        # sample weights for class balance
        if self.class_weight == "balanced":
            n_pos = y.sum()
            n_neg = n - n_pos
            w_pos = (n / (2 * n_pos)) if n_pos > 0 else 1.0
            w_neg = (n / (2 * n_neg)) if n_neg > 0 else 1.0
            sw = np.where(y == 1, w_pos, w_neg)
        else:
            sw = np.ones(n)

        w = np.zeros(p)
        b = 0.0
        lr = 0.5

        for _ in range(self.max_iter):
            z     = X @ w + b
            sigma = self._sigmoid(z)
            diff  = sigma - y

            grad_w = (X.T @ (sw * diff)) / n + lam * w
            grad_b = (sw * diff).mean()

            w -= lr * grad_w
            b -= lr * grad_b

            if np.linalg.norm(grad_w) < self.tol:
                break

        self.coef_      = w.reshape(1, -1)
        self.intercept_ = np.array([b])
        return self

    def predict_proba(self, X) -> np.ndarray:
        X  = np.array(X, dtype=float)
        z  = X @ self.coef_.T + self.intercept_
        p1 = self._sigmoid(z).flatten()
        return np.column_stack([1 - p1, p1])

    def predict(self, X) -> np.ndarray:
        return (self.predict_proba(X)[:, 1] >= 0.5).astype(int)


class _NumpyRidge:
    """Ridge regression trained via the analytical normal equation."""

    def __init__(self, alpha=1.0):
        self.alpha     = alpha
        self.coef_     = None
        self.intercept_ = None

    def fit(self, X: np.ndarray, y: np.ndarray):
        n, p = X.shape
        Xa = np.hstack([X, np.ones((n, 1))])
        reg = self.alpha * np.eye(p + 1)
        reg[-1, -1] = 0   # don't regularise the bias term
        A  = Xa.T @ Xa + reg
        b  = Xa.T @ y
        coef = np.linalg.solve(A, b)
        self.coef_      = coef[:p]
        self.intercept_ = coef[p]
        return self

    def predict(self, X) -> np.ndarray:
        X = np.array(X, dtype=float)
        return X @ self.coef_ + self.intercept_


# ── Data loading ────────────────────────────────────────────────────────────

def _load_data():
    if not _DB.exists():
        print(f"[!] training_data.json לא נמצא ב: {_DB}")
        return [], [], []

    rows = json.loads(_DB.read_text("utf-8"))
    X, y_clf, y_reg = [], [], []
    skipped = 0

    for r in rows:
        try:
            area   = float(r.get("area_sqm") or 0)
            pts    = float(r.get("survey_points") or 0)
            dist   = float(r.get("distance_km") or 0)
            si     = float(r.get("shape_index") or 1)
            qp     = float(r.get("quoted_price") or 0)
            margin = r.get("profit_margin_pct")

            if area <= 0 or qp <= 0 or margin in (None, "", "null"):
                skipped += 1
                continue

            margin = float(margin)
            mt_rz  = 1 if str(r.get("map_type", "")).upper() == "RZ" else 0

            X.append([math.log1p(area), pts, dist, si, math.log1p(qp), mt_rz])
            y_clf.append(1 if margin >= MARGIN_THRESHOLD else 0)
            y_reg.append(margin)

        except (ValueError, TypeError):
            skipped += 1

    print(f"[i] נטענו {len(X)} רשומות תקינות ({skipped} דולגו)")
    return X, y_clf, y_reg


# ── Cross-validation (k-fold accuracy) ─────────────────────────────────────

def _cross_val_accuracy(X: np.ndarray, y: np.ndarray, k: int) -> np.ndarray:
    n = len(X)
    indices = np.arange(n)
    fold_size = n // k
    scores = []

    for i in range(k):
        test_idx  = indices[i * fold_size: (i + 1) * fold_size]
        train_idx = np.concatenate([indices[:i * fold_size],
                                    indices[(i + 1) * fold_size:]])
        X_tr, y_tr = X[train_idx], y[train_idx]
        X_te, y_te = X[test_idx],  y[test_idx]

        sc = _NumpyScaler()
        X_tr_sc = sc.fit_transform(X_tr)
        X_te_sc = sc.transform(X_te)

        clf = _NumpyLogisticRegression(C=1.0, max_iter=1000, class_weight="balanced")
        clf.fit(X_tr_sc, y_tr)

        preds  = clf.predict(X_te_sc)
        scores.append((preds == y_te).mean())

    return np.array(scores)


# ── Main training function ──────────────────────────────────────────────────

def train(save=True):
    X_raw, y_clf, y_reg = _load_data()

    if len(X_raw) < 5:
        print(f"[!] אין מספיק נתונים לאימון (נמצאו {len(X_raw)}, דרושים לפחות 5).")
        print("    מלא שדות quoted_price + actual_hours + hourly_cost בפאנל 'נתוני אימון'.")
        sys.exit(1)

    X  = np.array(X_raw, dtype=float)
    yc = np.array(y_clf, dtype=int)
    yr = np.array(y_reg, dtype=float)

    scaler = _NumpyScaler()
    X_sc   = scaler.fit_transform(X)

    clf = _NumpyLogisticRegression(C=1.0, max_iter=1000, class_weight="balanced")
    clf.fit(X_sc, yc)

    reg = _NumpyRidge(alpha=1.0)
    reg.fit(X_sc, yr)

    # cross-validation
    cv = min(len(X), 10)
    cv_scores = _cross_val_accuracy(X, yc, k=cv)
    print(f"\n[OK] Logistic Regression - CV accuracy ({cv}-fold): "
          f"{cv_scores.mean():.2f} +/- {cv_scores.std():.2f}")
    print(f"    n_profitable={int(yc.sum())}  n_not_profitable={int((yc==0).sum())}")

    # feature importance
    feat_std   = X.std(axis=0)
    coef       = clf.coef_[0]
    importance = np.abs(coef * feat_std)
    importance = importance / (importance.sum() + 1e-12)

    feat_meta = {
        "feature_names":    FEATURES,
        "feature_labels":   FEATURE_LABELS_HE,
        "coef":             coef.tolist(),
        "clf_intercept":    float(clf.intercept_[0]),
        "importance":       importance.tolist(),
        "coef_direction":   [1 if c > 0 else -1 for c in coef],
        "margin_threshold": MARGIN_THRESHOLD,
        "borderline_lo":    BORDERLINE_LO,
        "n_train":          len(X),
        "class_balance":    {"profitable": int(yc.sum()),
                             "not_profitable": int((yc == 0).sum())},
        "cv_accuracy_mean": float(cv_scores.mean()),
        "cv_accuracy_std":  float(cv_scores.std()),
        "reg_coef":         reg.coef_.tolist(),
        "reg_intercept":    float(reg.intercept_),
        "scaler_mean":      scaler.mean_.tolist(),
        "scaler_scale":     scaler.scale_.tolist(),
    }

    if save:
        with open(_HERE / "model_clf.pkl",  "wb") as f: pickle.dump(clf,    f)
        with open(_HERE / "model_reg.pkl",  "wb") as f: pickle.dump(reg,    f)
        with open(_HERE / "scaler.pkl",     "wb") as f: pickle.dump(scaler, f)
        (_HERE / "feature_meta.json").write_text(
            json.dumps(feat_meta, ensure_ascii=False, indent=2), "utf-8"
        )
        _write_model_py(feat_meta)
        print(f"\n[OK] model saved: {_HERE}")
        print(f"    model_clf.pkl + model_reg.pkl + scaler.pkl + feature_meta.json + model.py")

    return clf, reg, scaler, feat_meta


def _write_model_py(m: dict):
    """Generate model.py — a zero-dependency frozen snapshot of the trained model."""
    import datetime

    def _fmt(lst): return "[" + ", ".join(f"{v:.10g}" for v in lst) + "]"

    today   = datetime.date.today().isoformat()
    n       = m["n_train"]
    cv_mean = m["cv_accuracy_mean"]
    cv_std  = m["cv_accuracy_std"]

    lines = f'''\
"""
Profitability Model — Frozen Snapshot
======================================
Generated automatically from feature_meta.json.
Trained on {n} projects.  CV accuracy: {cv_mean*100:.1f}% +/- {cv_std*100:.1f}% (10-fold).
Last updated: {today}

Usage:
    from profitability_model.model import predict
    result = predict(area_sqm=5000, survey_points=80, distance_km=15,
                     shape_index=1.4, quoted_price=12000, map_type_rz=1)
    print(result)
    # {{'verdict': 'profitable', 'prob_profitable': 0.78, 'expected_margin_pct': 31.2}}
"""

import math

# Training snapshot ({today})
N_TRAIN          = {n}
CV_ACCURACY      = {cv_mean:.6f}
MARGIN_THRESHOLD = {m["margin_threshold"]}
BORDERLINE_LO    = {m["borderline_lo"]}

FEATURES = {m["feature_names"]}

FEATURE_LABELS = {json.dumps(m["feature_labels"], ensure_ascii=False)}

# Scaler
_SCALER_MEAN  = {_fmt(m["scaler_mean"])}
_SCALER_SCALE = {_fmt(m["scaler_scale"])}

# Logistic Regression
_CLF_COEF      = {_fmt(m["coef"])}
_CLF_INTERCEPT = {m["clf_intercept"]:.10g}

# Ridge Regression
_REG_COEF      = {_fmt(m["reg_coef"])}
_REG_INTERCEPT = {m["reg_intercept"]:.10g}

# Feature importance (normalised %)
_IMPORTANCE = {_fmt(m["importance"])}
_DIRECTION  = {m["coef_direction"]}


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
        verdict             — \'profitable\' | \'borderline\' | \'not_profitable\'
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
        [{{"name": name, "label": FEATURE_LABELS[name],
           "importance": round(_IMPORTANCE[i] * 100, 1),
           "direction": _DIRECTION[i]}}
         for i, name in enumerate(FEATURES)],
        key=lambda x: x["importance"], reverse=True,
    )

    return {{
        "verdict":             verdict,
        "prob_profitable":     round(prob, 4),
        "expected_margin_pct": round(margin, 1),
        "top_factors":         top_factors,
        "model_info":          {{"n_train": N_TRAIN,
                                 "cv_accuracy": round(CV_ACCURACY * 100, 1)}},
    }}


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
        print(f"[{{r[\'verdict\']:15s}}]  prob={{r[\'prob_profitable\']:.2f}}"
              f"  margin={{r[\'expected_margin_pct\']:+.1f}}%"
              f"  | area={{ex[\'area_sqm\']}} pts={{ex[\'survey_points\']}}"
              f" dist={{ex[\'distance_km\']}}km price={{ex[\'quoted_price\']}}")
'''
    (_HERE / "model.py").write_text(lines, "utf-8")
    print(f"    model.py updated ({today}, n_train={n})")


if __name__ == "__main__":
    train()
