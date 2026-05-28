"""
Model Evaluation on Holdout Set (19%)
======================================
Reads the validation CSV, runs predictions WITHOUT using profit columns,
then compares against the known actual profit_margin_pct.

Usage:
    python profitability_model/evaluate.py
    python profitability_model/evaluate.py --csv "DATA/training_data - VALID.csv"
"""

import csv, json, math, sys
from pathlib import Path

_HERE = Path(__file__).parent
_ROOT = _HERE.parent

DEFAULT_CSV = _ROOT / "DATA" / "training_data - VALID.csv"

MARGIN_THRESHOLD = 20.0
BORDERLINE_LO    = 10.0


# ── Load model artifacts ─────────────────────────────────────────────────────

def _load_model():
    meta_path = _HERE / "feature_meta.json"
    if not meta_path.exists():
        sys.exit("[!] feature_meta.json לא נמצא. הרץ תחילה את train.py")
    meta = json.loads(meta_path.read_text("utf-8"))
    return meta


def _scale(raw, mean, scale):
    return [(v - mu) / s for v, mu, s in zip(raw, mean, scale)]


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _sigmoid(z):
    return 1.0 / (1.0 + math.exp(-max(-500.0, min(500.0, z))))


def predict_row(meta, area_sqm, survey_points, distance_km,
                shape_index, quoted_price, map_type_rz):
    raw    = [math.log1p(area_sqm), survey_points, distance_km,
              shape_index, math.log1p(quoted_price), float(map_type_rz)]
    scaled = _scale(raw, meta["scaler_mean"], meta["scaler_scale"])

    prob   = _sigmoid(_dot(scaled, meta["coef"]) + meta["clf_intercept"])
    margin = _dot(scaled, meta["reg_coef"]) + meta["reg_intercept"]

    if margin >= MARGIN_THRESHOLD and prob >= 0.60:
        verdict = "profitable"
    elif margin >= BORDERLINE_LO or prob >= 0.40:
        verdict = "borderline"
    else:
        verdict = "not_profitable"

    return {"verdict": verdict, "prob": round(prob, 4), "pred_margin": round(margin, 1)}


# ── Load & predict ───────────────────────────────────────────────────────────

def run(csv_path: Path):
    if not csv_path.exists():
        sys.exit(f"[!] קובץ לא נמצא: {csv_path}")

    meta = _load_model()

    rows = []
    with open(csv_path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append(r)

    results = []
    skipped = 0

    for r in rows:
        try:
            area   = float(r.get("area_sqm") or 0)
            pts    = float(r.get("survey_points") or 0)
            dist   = float(r.get("distance_km") or 0)
            si     = float(r.get("shape_index") or 1)
            qp     = float(r.get("quoted_price") or 0)
            actual = float(r.get("profit_margin_pct") or "nan")
            mt_rz  = 1 if str(r.get("map_type", "")).upper() == "RZ" else 0

            if area <= 0 or qp <= 0 or math.isnan(actual):
                skipped += 1
                continue

            pred = predict_row(meta, area, pts, dist, si, qp, mt_rz)

            actual_verdict = (
                "profitable"     if actual >= MARGIN_THRESHOLD else
                "borderline"     if actual >= BORDERLINE_LO    else
                "not_profitable"
            )
            correct = (pred["verdict"] == actual_verdict)
            margin_err = pred["pred_margin"] - actual

            results.append({
                "project":        r.get("project_name", ""),
                "map_type":       r.get("map_type", ""),
                "actual_margin":  round(actual, 1),
                "actual_verdict": actual_verdict,
                "pred_margin":    pred["pred_margin"],
                "pred_verdict":   pred["verdict"],
                "prob":           pred["prob"],
                "correct":        correct,
                "margin_err":     round(margin_err, 1),
            })

        except (ValueError, TypeError):
            skipped += 1

    return results, skipped


# ── Report ───────────────────────────────────────────────────────────────────

def report(results, skipped):
    n = len(results)
    if n == 0:
        print("[!] אין רשומות תקינות לניתוח.")
        return

    correct    = sum(1 for r in results if r["correct"])
    accuracy   = correct / n * 100
    errors     = [r["margin_err"] for r in results]
    mae        = sum(abs(e) for e in errors) / n
    signed_avg = sum(errors) / n

    print(f"\n{'='*65}")
    print(f"  הערכת מודל — {n} פרויקטים (דולגו: {skipped})")
    print(f"{'='*65}")
    print(f"  דיוק סיווג (profitable/borderline/not):  {accuracy:.1f}%  ({correct}/{n})")
    print(f"  שגיאת margin ממוצעת (MAE):               {mae:.1f}%")
    print(f"  הטיה ממוצעת (חיובי=מודל אופטימי מדי):   {signed_avg:+.1f}%")

    # confusion by verdict
    verdicts = ["profitable", "borderline", "not_profitable"]
    print(f"\n  {'':20s}  {'חזוי ->':>35s}")
    print(f"  {'אמיתי v':20s}  {'profitable':>12s}  {'borderline':>12s}  {'not_prof':>10s}")
    print(f"  {'-'*60}")
    for av in verdicts:
        row_results = [r for r in results if r["actual_verdict"] == av]
        counts = [sum(1 for r in row_results if r["pred_verdict"] == pv) for pv in verdicts]
        label = {"profitable": "profitable", "borderline": "borderline",
                 "not_profitable": "not profitable"}[av]
        print(f"  {label:20s}  {counts[0]:>12d}  {counts[1]:>12d}  {counts[2]:>10d}")

    # per-project table
    print(f"\n  {'פרויקט':18s}  {'סוג':4s}  {'אמיתי':>8s}  {'חזוי':>8s}  {'שגיאה':>7s}  {'prob':>5s}  {'תוצאה'}")
    print(f"  {'-'*72}")
    for r in sorted(results, key=lambda x: abs(x["margin_err"]), reverse=True):
        ok  = "OK" if r["correct"] else "XX"
        avl = r["actual_verdict"][:4]
        pvl = r["pred_verdict"][:4]
        print(f"  {r['project']:18s}  {r['map_type']:4s}  "
              f"{r['actual_margin']:>7.1f}%  {r['pred_margin']:>7.1f}%  "
              f"{r['margin_err']:>+6.1f}%  {r['prob']:>5.2f}  {ok} {pvl}")

    # worst errors
    worst = sorted(results, key=lambda x: abs(x["margin_err"]), reverse=True)[:5]
    print(f"\n  5 השגיאות הגדולות ביותר:")
    for r in worst:
        print(f"    {r['project']:18s}  אמיתי={r['actual_margin']:+.1f}%  "
              f"חזוי={r['pred_margin']:+.1f}%  שגיאה={r['margin_err']:+.1f}%")

    print(f"\n{'='*65}\n")


# ── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    csv_path = Path(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[1] == "--csv" \
               else DEFAULT_CSV
    if not csv_path.is_absolute():
        csv_path = _ROOT / csv_path

    results, skipped = run(csv_path)
    report(results, skipped)
