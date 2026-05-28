"""
DWG → DXF → CSV → SHP/KML Pipeline — Local Server v3
Run:  python server.py
Open: http://localhost:7654
"""

import csv as csv_mod
import json, os, threading, time, queue, webbrowser, zipfile, io, gzip
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed

_DIR = Path(__file__).parent
TRAINING_DB = _DIR / "training_data.json"

ITM_PRJ_WKT = (
    'PROJCS["Israel_TM_Grid",'
    'GEOGCS["GCS_GRS_1980_Israel",'
    'DATUM["D_GRS_1980_Israel",'
    'SPHEROID["GRS_1980",6378137.0,298.257222101]],'
    'PRIMEM["Greenwich",0.0],'
    'UNIT["Degree",0.0174532925199433]],'
    'PROJECTION["Transverse_Mercator"],'
    'PARAMETER["False_Easting",219529.584],'
    'PARAMETER["False_Northing",-626907.39],'
    'PARAMETER["Central_Meridian",35.2045169444444],'
    'PARAMETER["Scale_Factor",1.0000067],'
    'PARAMETER["Latitude_Of_Origin",31.7343936111111],'
    'UNIT["Meter",1.0]]'
)

# ── Module loaders ──────────────────────────────────────────────────────────

def _load_converter():
    sibling = _DIR / "dwg_to_shp.py"
    if not sibling.exists():
        raise FileNotFoundError("dwg_to_shp.py not found next to server.py")
    import importlib.util
    spec = importlib.util.spec_from_file_location("dwg_to_shp", sibling)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def _load_csv_converter():
    sibling = _DIR / "dwg_to_csv.py"
    if not sibling.exists():
        raise FileNotFoundError("dwg_to_csv.py not found next to server.py")
    import importlib.util
    spec = importlib.util.spec_from_file_location("dwg_to_csv", sibling)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def _load_kml_converter():
    sibling = _DIR / "csv_to_kml.py"
    if not sibling.exists():
        raise FileNotFoundError("csv_to_kml.py not found next to server.py")
    import importlib.util
    spec = importlib.util.spec_from_file_location("csv_to_kml", sibling)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

# ── Job state ────────────────────────────────────────────────────────────────
_job_queue   = queue.Queue()
_job_lock    = threading.Lock()
_job_running = False
_parsed_cache: dict = {}   # {dxf_stem: [row_dicts]} — populated by step 2
_parsed_layer: str  = ""   # currently loaded layer name
_survey_cache: dict = {}   # {dxf_stem: {count, map_type, block_names}}
_session_name: str  = ""   # name of the currently loaded/saved session
_worker_csv_mod      = None # per-process module cache for ProcessPoolExecutor workers


# ═══════════════════════════════════════════════════════════════════════════
# OUTPUT MODE RESOLVER (legacy batch SHP mode)
# ═══════════════════════════════════════════════════════════════════════════

def resolve_out_dir(dxf_path: Path, input_dir: Path, output_dir: Path, mode: str) -> Path:
    stem = dxf_path.stem
    if mode == "flat":
        return output_dir
    elif mode == "per_map":
        return output_dir / stem
    elif mode == "mirror":
        rel = dxf_path.parent.relative_to(input_dir)
        return output_dir / rel / stem
    else:
        return output_dir / stem


# ═══════════════════════════════════════════════════════════════════════════
# SCAN
# ═══════════════════════════════════════════════════════════════════════════

def do_scan(params: dict) -> dict:
    input_dir = Path(params["input_dir"])
    ext       = params.get("ext", "dxf").lower()
    recursive = params.get("recursive", True)
    only_rz   = params.get("only_rz", False)
    only_tzr  = params.get("only_tzr", False)

    if not input_dir.exists():
        return {"error": f"תיקייה לא קיימת: {input_dir}"}

    glob  = f"**/*.{ext}" if recursive else f"*.{ext}"
    files = sorted(input_dir.glob(glob))

    skipped = 0
    if only_rz:
        before  = len(files)
        files   = [f for f in files if "RZ" in f.stem.upper()]
        skipped = before - len(files)
    elif only_tzr:
        import re as _re
        _tzr_pat = _re.compile(r'^\d+-\d{4}$')
        before  = len(files)
        files   = [f for f in files if _tzr_pat.match(f.stem)]
        skipped = before - len(files)

    result = []
    for f in files:
        try:
            st = f.stat()
            result.append({
                "path":     str(f),
                "name":     f.stem,
                "filename": f.name,
                "rel":      str(f.relative_to(input_dir)),
                "size":     st.st_size,
                "mtime":    st.st_mtime,
            })
        except Exception:
            pass

    return {"files": result, "skipped": skipped, "total": len(result)}


def do_list_output(params: dict) -> dict:
    """List files of a given extension in output_dir."""
    output_dir = Path(params.get("output_dir", ""))
    ext        = params.get("ext", "dxf").lower()

    if not output_dir.exists():
        return {"files": [], "total": 0}

    files = sorted(output_dir.rglob(f"*.{ext}"))
    result = []
    for f in files:
        try:
            st = f.stat()
            result.append({
                "path":     str(f),
                "name":     f.stem,
                "filename": f.name,
                "size":     st.st_size,
            })
        except Exception:
            pass

    return {"files": result, "total": len(result)}


# ═══════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def _get_dxf_layers(dxf_paths: list) -> list:
    """Return sorted unique layer names that have entities across all DXF files."""
    try:
        import ezdxf
    except ImportError:
        return []
    layers = set()
    for p in dxf_paths:
        try:
            doc = ezdxf.readfile(str(p))
            for entity in doc.modelspace():
                try:
                    layers.add(entity.dxf.layer)
                except Exception:
                    pass
        except Exception:
            pass
    return sorted(layers)


def _write_csv_rows(rows: list, path: Path):
    """Write list of row-dicts to a UTF-8 CSV file."""
    if not rows:
        return
    seen: dict = {}
    for row in rows:
        for k in row:
            if k not in seen:
                seen[k] = True
    fieldnames = list(seen.keys())
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv_mod.DictWriter(fh, fieldnames=fieldnames, restval='')
        w.writeheader()
        w.writerows(rows)


def _get_parsed_geojson(filter_map: str = "") -> dict:
    """Build polygon data from in-memory _parsed_cache for map rendering."""
    maps_data: dict = {}
    geom_summary: dict = {}   # {map_name: {GeometryType: count}} — for debugging

    for map_name, rows in _parsed_cache.items():
        if filter_map and map_name != filter_map:
            continue
        features = _group_features(rows)

        # collect geom type counts for debug
        type_counts: dict = {}
        for feat in features:
            gt = feat[0].get("GeometryType", "?")
            type_counts[gt] = type_counts.get(gt, 0) + 1
        geom_summary[map_name] = type_counts

        polys = []
        for feat in features:
            if feat[0].get("GeometryType", "") == "Polygon":
                pts = [[float(r["X"]), float(r["Y"])] for r in feat]
                if len(pts) >= 3:
                    if pts[0] != pts[-1]:
                        pts.append(pts[0])
                    polys.append(pts)
        if polys:
            maps_data[map_name] = polys

    return maps_data, geom_summary


# ═══════════════════════════════════════════════════════════════════════════
# PARALLEL WORKER HELPERS  (top-level → picklable by multiprocessing)
# ═══════════════════════════════════════════════════════════════════════════

def _init_csv_worker():
    """Initializer called once per ProcessPoolExecutor worker process.
    Loads dwg_to_csv.py so every task in the process reuses the cached module."""
    global _worker_csv_mod
    _worker_csv_mod = _load_csv_converter()


def _step2_worker(args: tuple) -> dict:
    """Parse one DXF file to rows + survey data.
    Reads the file exactly once and passes the doc to both parse_dxf and
    count_survey_points — eliminating the duplicate ezdxf.readfile() call."""
    dxf_path_str, file_layer, file_map_type, polygon_only, map_rules_list, geom_types_list, precision = args
    t0 = time.time()
    f  = Path(dxf_path_str)
    mod = _worker_csv_mod

    try:
        try:
            doc = mod.ezdxf.readfile(dxf_path_str)
        except UnicodeDecodeError:
            doc = mod.ezdxf.readfile(dxf_path_str, encoding='cp1255')

        conv = mod.DwgToCsvConverter(precision=precision)
        rows = conv.parse_dxf(
            dxf_path_str,
            [file_layer] if file_layer else None,
            polygon_only=polygon_only,
            map_rules=map_rules_list,
            force_map_type=file_map_type,
            _doc=doc,
        )
        if geom_types_list:
            rows = [r for r in rows if r.get("GeometryType", "") in set(geom_types_list)]

        try:
            survey_data = mod.count_survey_points(doc, map_type=file_map_type)
        except Exception:
            survey_data = {"count": 0, "map_type": file_map_type or "unknown", "block_names": []}

        return {
            "stem": f.stem, "name": f.name,
            "rows": rows, "survey_data": survey_data,
            "status": "ok" if rows else "empty",
            "error": "" if rows else "לא נמצאו נתונים",
            "elapsed": round(time.time() - t0, 3),
        }
    except Exception as e:
        return {
            "stem": f.stem, "name": f.name,
            "rows": [], "survey_data": {"count": 0, "map_type": file_map_type or "unknown", "block_names": []},
            "status": "error", "error": str(e),
            "elapsed": round(time.time() - t0, 3),
        }


# ═══════════════════════════════════════════════════════════════════════════
# STEP 1 — DWG → DXF  (runs in background thread)
# ═══════════════════════════════════════════════════════════════════════════

def _run_step1(params: dict):
    """DWG→DXF in parallel using ThreadPoolExecutor.
    ODA is an external subprocess — subprocess.run releases the GIL, so multiple
    ODA processes run truly concurrently without needing separate Python processes."""
    global _job_running
    try:
        mod      = _load_csv_converter()
        oda_path = params.get("oda_path") or None
        conv     = mod.DwgToCsvConverter(oda_path=oda_path)
    except Exception as e:
        _job_queue.put({"type": "error", "message": str(e)})
        _job_queue.put({"type": "done_thread"})
        _job_running = False
        return

    import shutil

    files      = [Path(p) for p in params["files"]]
    output_dir = Path(params["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    total      = len(files)
    workers_raw = params.get("workers")
    n_workers  = min(os.cpu_count() or 4, int(workers_raw) if workers_raw else 6)

    if total == 0:
        _job_queue.put({"type": "error", "message": "לא נבחרו קבצים"})
        _job_queue.put({"type": "done_thread"})
        _job_running = False
        return

    _job_queue.put({"type": "start", "total": total})

    ok = errors = 0
    output_files = []
    t_start   = time.time()
    processed = 0

    def _convert_one(f: Path) -> dict:
        t0       = time.time()
        dxf_dest = output_dir / (f.stem + ".dxf")
        try:
            dxf_tmp = conv.convert_dwg_to_dxf(str(f))
            if dxf_tmp and Path(dxf_tmp).exists():
                shutil.copy2(dxf_tmp, str(dxf_dest))
                shutil.rmtree(Path(dxf_tmp).parent, ignore_errors=True)
                return {"file": f.name, "status": "ok", "dxf_dest": str(dxf_dest),
                        "error": "", "elapsed": round(time.time() - t0, 3)}
            return {"file": f.name, "status": "error", "dxf_dest": None,
                    "error": "ODA converter לא מצא קובץ DXF בפלט",
                    "elapsed": round(time.time() - t0, 3)}
        except Exception as e:
            return {"file": f.name, "status": "error", "dxf_dest": None,
                    "error": str(e), "elapsed": round(time.time() - t0, 3)}

    with ThreadPoolExecutor(max_workers=n_workers) as pool:
        futures = {pool.submit(_convert_one, f): f for f in files}
        for future in as_completed(futures):
            try:
                res = future.result()
            except Exception as e:
                processed += 1
                errors += 1
                f = futures[future]
                _job_queue.put({
                    "type": "progress",
                    "file": f.name, "status": "error", "count": 0,
                    "error": str(e), "elapsed": 0,
                    "processed": processed, "total": total,
                    "ok": ok, "errors": errors,
                })
                continue

            processed += 1
            if res["status"] == "ok":
                ok += 1
                output_files.append(res["dxf_dest"])
            else:
                errors += 1
            _job_queue.put({
                "type": "progress",
                "file": res["file"], "status": res["status"],
                "count": 1 if res["status"] == "ok" else 0,
                "error": res["error"], "elapsed": res["elapsed"],
                "processed": processed, "total": total,
                "ok": ok, "errors": errors,
            })

    _job_queue.put({
        "type": "done", "total": total,
        "ok": ok, "errors": errors,
        "output_files": output_files,
        "output_dir": str(output_dir),
        "elapsed": round(time.time() - t_start, 2),
    })
    _job_queue.put({"type": "done_thread"})
    _job_running = False


# ═══════════════════════════════════════════════════════════════════════════
# STEP 2 — DXF → memory (runs in background thread, no disk writes)
# ═══════════════════════════════════════════════════════════════════════════

import re as _re
_TZR_PAT = _re.compile(r'^\d+-\d{4}$')

def _auto_layer(stem: str) -> str | None:
    """Return the correct layer for a file based on its name, or None if unknown."""
    if "RZ" in stem.upper():
        return "M1200"
    if _TZR_PAT.match(stem):
        return "C1602_0"
    return None


def _run_step2(params: dict):
    """Parse DXF files to memory in parallel (ProcessPoolExecutor).
    Each worker reads the file once and runs both parse_dxf + count_survey_points
    on the same doc object — eliminating the duplicate ezdxf.readfile() call."""
    global _job_running, _parsed_cache, _parsed_layer, _survey_cache

    files           = [Path(p) for p in params["files"]]
    layer           = params.get("layer") or None
    map_rules       = params.get("map_rules") or []
    polygon_only    = params.get("polygon_only", False)
    geom_types      = params.get("geometry_types")
    geom_types_list = list(geom_types) if geom_types else []
    precision       = params.get("precision", 3)
    total           = len(files)
    workers_raw     = params.get("workers")
    n_workers       = min(os.cpu_count() or 4, int(workers_raw) if workers_raw else 8)

    if total == 0:
        _job_queue.put({"type": "error", "message": "לא נבחרו קבצים"})
        _job_queue.put({"type": "done_thread"})
        _job_running = False
        return

    try:
        _load_csv_converter()  # sanity-check module is reachable before spawning workers
    except Exception as e:
        _job_queue.put({"type": "error", "message": str(e)})
        _job_queue.put({"type": "done_thread"})
        _job_running = False
        return

    _parsed_cache = {}
    _survey_cache = {}
    _parsed_layer = layer or "(אוטומטי)"
    _job_queue.put({"type": "start", "total": total})

    ok = empty = errors = 0
    total_rows = total_features = 0
    t_start   = time.time()
    processed = 0

    def _make_task(f: Path) -> tuple:
        file_layer = layer or _auto_layer(f.stem)
        if file_layer == "M1200":
            file_map_type = "RZ"
        elif file_layer and file_layer.upper().startswith("C1602"):
            file_map_type = "TZR"
        else:
            file_map_type = None
        return (str(f), file_layer, file_map_type, polygon_only, list(map_rules), geom_types_list, precision)

    tasks = [_make_task(f) for f in files]

    with ProcessPoolExecutor(max_workers=n_workers, initializer=_init_csv_worker) as pool:
        futures = {pool.submit(_step2_worker, t): t for t in tasks}
        for future in as_completed(futures):
            try:
                res = future.result()
            except Exception as e:
                processed += 1
                errors += 1
                t = futures[future]
                _job_queue.put({
                    "type": "progress",
                    "file": Path(t[0]).name, "status": "error", "count": 0,
                    "features": 0, "error": str(e), "elapsed": 0,
                    "processed": processed, "total": total,
                    "ok": ok, "empty": empty, "errors": errors,
                    "total_rows": total_rows, "total_features": total_features,
                })
                continue

            processed  += 1
            stem        = res["stem"]
            rows        = res["rows"]
            survey_data = res["survey_data"]
            status      = res["status"]
            error       = res["error"]
            feat_count  = 0

            if status == "ok":
                feat_count = len(_group_features(rows))
                _parsed_cache[stem] = rows
                _survey_cache[stem] = survey_data
                s_count = survey_data.get("count", 0)
                if s_count:
                    for row in _parsed_cache[stem]:
                        row["SURV_PTS"] = str(s_count)
                ok             += 1
                total_rows     += len(rows)
                total_features += feat_count
                count           = len(rows)
            elif status == "empty":
                _survey_cache[stem] = survey_data
                empty += 1
                count  = 0
            else:
                errors += 1
                count   = 0

            _job_queue.put({
                "type": "progress",
                "file": res["name"], "status": status, "count": count,
                "features": feat_count, "error": error,
                "elapsed": res["elapsed"],
                "processed": processed, "total": total,
                "ok": ok, "empty": empty, "errors": errors,
                "total_rows": total_rows, "total_features": total_features,
            })

    # מחיקת קבצי DXF הזמניים — הנתונים כבר בזיכרון
    deleted = 0
    for f in files:
        try:
            f.unlink(missing_ok=True)
            deleted += 1
        except Exception:
            pass
    if deleted:
        print(f"🗑️  נמחקו {deleted} קבצי DXF זמניים")

    _job_queue.put({
        "type": "done", "total": total,
        "ok": ok, "empty": empty, "errors": errors,
        "total_rows": total_rows, "total_features": total_features,
        "map_names": list(_parsed_cache.keys()),
        "layer": _parsed_layer,
        "elapsed": round(time.time() - t_start, 2),
    })
    _job_queue.put({"type": "done_thread"})
    _job_running = False


# ═══════════════════════════════════════════════════════════════════════════
# STEP 1+2 PIPELINE — DWG→DXF→memory with full overlap
# Each DXF is submitted for parsing as soon as its ODA conversion finishes.
# ═══════════════════════════════════════════════════════════════════════════

def _run_step1_2(params: dict):
    """Pipelined DWG→DXF→memory: Step 2 parsing starts as soon as each DXF is
    ready instead of waiting for all ODA conversions to finish.
    Wall-clock time ≈ max(Step1_time, Step2_time) rather than their sum."""
    global _job_running, _parsed_cache, _parsed_layer, _survey_cache

    try:
        mod      = _load_csv_converter()
        oda_path = params.get("oda_path") or None
        conv     = mod.DwgToCsvConverter(oda_path=oda_path)
    except Exception as e:
        _job_queue.put({"type": "error", "message": str(e)})
        _job_queue.put({"type": "done_thread"})
        _job_running = False
        return

    import shutil

    dwg_files       = [Path(p) for p in params["files"]]
    output_dir      = Path(params["output_dir"])
    layer           = params.get("layer") or None
    map_rules       = params.get("map_rules") or []
    polygon_only    = params.get("polygon_only", False)
    geom_types      = params.get("geometry_types")
    geom_types_list = list(geom_types) if geom_types else []
    precision       = params.get("precision", 3)
    total           = len(dwg_files)
    workers_raw     = params.get("workers")
    n_step1 = min(os.cpu_count() or 4, int(workers_raw) if workers_raw else 6)
    n_step2 = min(os.cpu_count() or 4, int(workers_raw) if workers_raw else 8)

    if total == 0:
        _job_queue.put({"type": "error", "message": "לא נבחרו קבצים"})
        _job_queue.put({"type": "done_thread"})
        _job_running = False
        return

    try:
        _load_csv_converter()
    except Exception as e:
        _job_queue.put({"type": "error", "message": str(e)})
        _job_queue.put({"type": "done_thread"})
        _job_running = False
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    _parsed_cache = {}
    _survey_cache = {}
    _parsed_layer = layer or "(אוטומטי)"
    _job_queue.put({"type": "start", "total": total})

    ok1 = errors1 = ok2 = empty2 = errors2 = 0
    total_rows = total_features = 0
    t_start   = time.time()
    proc1 = proc2 = 0

    def _convert_one(f: Path) -> dict:
        t0 = time.time()
        dxf_dest = output_dir / (f.stem + ".dxf")
        try:
            dxf_tmp = conv.convert_dwg_to_dxf(str(f))
            if dxf_tmp and Path(dxf_tmp).exists():
                shutil.copy2(dxf_tmp, str(dxf_dest))
                shutil.rmtree(Path(dxf_tmp).parent, ignore_errors=True)
                return {"file": f.name, "status": "ok", "dxf_dest": str(dxf_dest),
                        "error": "", "elapsed": round(time.time() - t0, 3)}
            return {"file": f.name, "status": "error", "dxf_dest": None,
                    "error": "ODA converter לא מצא קובץ DXF בפלט",
                    "elapsed": round(time.time() - t0, 3)}
        except Exception as e:
            return {"file": f.name, "status": "error", "dxf_dest": None,
                    "error": str(e), "elapsed": round(time.time() - t0, 3)}

    def _make_step2_task(dxf_path: str) -> tuple:
        f = Path(dxf_path)
        file_layer = layer or _auto_layer(f.stem)
        if file_layer == "M1200":
            file_map_type = "RZ"
        elif file_layer and file_layer.upper().startswith("C1602"):
            file_map_type = "TZR"
        else:
            file_map_type = None
        return (dxf_path, file_layer, file_map_type, polygon_only, list(map_rules), geom_types_list, precision)

    step2_futures: dict = {}

    with ThreadPoolExecutor(max_workers=n_step1) as s1_pool, \
         ProcessPoolExecutor(max_workers=n_step2, initializer=_init_csv_worker) as s2_pool:

        s1_futures = {s1_pool.submit(_convert_one, f): f for f in dwg_files}

        for s1_fut in as_completed(s1_futures):
            try:
                res1 = s1_fut.result()
            except Exception as e:
                proc1 += 1; errors1 += 1
                f = s1_futures[s1_fut]
                _job_queue.put({"type": "progress", "step": 1,
                                "file": f.name, "status": "error",
                                "error": str(e), "elapsed": 0,
                                "processed": proc1, "total": total,
                                "ok": ok1, "errors": errors1})
                continue

            proc1 += 1
            if res1["status"] == "ok":
                ok1 += 1
                # Pipeline: immediately dispatch DXF to Step 2
                t2 = _make_step2_task(res1["dxf_dest"])
                s2_f = s2_pool.submit(_step2_worker, t2)
                step2_futures[s2_f] = res1["dxf_dest"]
            else:
                errors1 += 1
            _job_queue.put({"type": "progress", "step": 1,
                            "file": res1["file"], "status": res1["status"],
                            "error": res1["error"], "elapsed": res1["elapsed"],
                            "processed": proc1, "total": total,
                            "ok": ok1, "errors": errors1})

        # Collect Step 2 results (workers have been running throughout Step 1)
        for s2_fut in as_completed(step2_futures):
            try:
                res2 = s2_fut.result()
            except Exception as e:
                proc2 += 1; errors2 += 1
                dxf_p = step2_futures[s2_fut]
                _job_queue.put({"type": "progress", "step": 2,
                                "file": Path(dxf_p).name, "status": "error",
                                "error": str(e), "elapsed": 0,
                                "processed": proc2, "total": ok1,
                                "ok": ok2, "empty": empty2, "errors": errors2,
                                "total_rows": total_rows, "total_features": total_features})
                continue

            proc2 += 1
            stem        = res2["stem"]
            rows        = res2["rows"]
            survey_data = res2["survey_data"]
            status2     = res2["status"]
            feat_count  = 0

            if status2 == "ok":
                feat_count = len(_group_features(rows))
                _parsed_cache[stem] = rows
                _survey_cache[stem] = survey_data
                s_count = survey_data.get("count", 0)
                if s_count:
                    for row in _parsed_cache[stem]:
                        row["SURV_PTS"] = str(s_count)
                ok2 += 1; total_rows += len(rows); total_features += feat_count
                count = len(rows)
            elif status2 == "empty":
                _survey_cache[stem] = survey_data; empty2 += 1; count = 0
            else:
                errors2 += 1; count = 0
            _job_queue.put({"type": "progress", "step": 2,
                            "file": res2["name"], "status": status2,
                            "count": count, "features": feat_count,
                            "error": res2["error"], "elapsed": res2["elapsed"],
                            "processed": proc2, "total": ok1,
                            "ok": ok2, "empty": empty2, "errors": errors2,
                            "total_rows": total_rows, "total_features": total_features})

    # Delete temp DXF files
    deleted = 0
    for dxf_path in step2_futures.values():
        try:
            Path(dxf_path).unlink(missing_ok=True); deleted += 1
        except Exception:
            pass
    if deleted:
        print(f"🗑️  נמחקו {deleted} קבצי DXF זמניים")

    _job_queue.put({
        "type": "done", "total": total,
        "step1": {"ok": ok1, "errors": errors1},
        "step2": {"ok": ok2, "empty": empty2, "errors": errors2,
                  "total_rows": total_rows, "total_features": total_features},
        "map_names": list(_parsed_cache.keys()),
        "layer": _parsed_layer,
        "elapsed": round(time.time() - t_start, 2),
    })
    _job_queue.put({"type": "done_thread"})
    _job_running = False


# ═══════════════════════════════════════════════════════════════════════════
# STEP 3 (legacy) — CSV → SHP / KML  — kept for backward compat
# ═══════════════════════════════════════════════════════════════════════════

def _group_features(rows):
    """Split CSV rows into per-feature groups by VertexIndex sequence."""
    features, current = [], []
    for row in rows:
        try:
            idx = int(row.get("VertexIndex", 0))
        except (ValueError, TypeError):
            idx = 0
        if idx == 0 and current:
            features.append(current)
            current = []
        current.append(row)
    if current:
        features.append(current)
    return features


def _write_prj(path):
    with open(path, "w") as f:
        f.write(ITM_PRJ_WKT)


_STANDARD_CSV_COLS = frozenset({
    "Layer", "EntityType", "GeometryType",
    "VertexIndex", "VertexCount",
    "X", "Y", "Z",
    "CoordinateSystem", "IsClosed",
    "Length_m", "Area_sqm",
    "Radius", "Bulge", "Rotation",
    "Color", "Notes",
})

# קטלוג שמות שדות מטה-דאטה — מעודכן מ-field_catalog.xlsx / field_catalog_TZR.xlsx
# FIELD_ALIASES: שם פנימי (cache) → שם DBF סופי בקובץ SHP
FIELD_ALIASES: dict = {
    # RZ — field_catalog.xlsx
    'Mt_CLIENT':  'CLIENT',
    'Mt_MAP_SUB': 'MAP_SUBJ',
    'Mt_SERIAL':  'SERIAL',
    'Mt_SETTLEM': 'SETTLEM',
    'At_AREA':    'PARC_AREA',
    'At_FILE':    'PLAN',
    'At_GUSH':    'GUSH',
    'At_LEGAL_A': 'MIG_AREA',
    'At_MIGRASH': 'MIGRASH',
    'At_PARCEL':  'PARCEL',
    'F5_FINISH_': 'FINISH_D',
    'F5_SURVEY_': 'SURVEY_D',
    # TZR — field_catalog_TZR.xlsx
    'C40_COUNTY': 'COUNTY',
    'C40_GRID_N': 'GRID_N',
    'C40_GUSH_N': 'GUSH',
    'C40_ORDERE': 'ORDERER',
    'C40_PARCEL': 'PARCEL',
    'C40_REGION': 'REGION',
    'C40_REGIST': 'REGIST',
    'C40_SCALE':  'SCALE',
    'C40_SETTLE': 'SETTLE',
    'C42_PROCES': 'TZR_PROC',
    'C42_SERIAL': 'TZR_SER',
    'C43_FINISH':  'FINISH_D',
    'C43_SRV_NM':  'SURVEYOR',
    'C43_SRV_DT':  'SURVEY_D',
    'C43_SRV_ID':  'SRV_LIC',
}

# שדות שלא ייכנסו לקובץ SHP (סומנו כלא רלוונטי בקטלוגים)
EXCLUDED_META_FIELDS: frozenset = frozenset({
    # RZ
    'At_FULL', 'F5_ACCURAC', 'F5_MAP_TYP', 'F5_SCALE', 'F5_SURVEYO',
    # TZR
    'C40_PROCES', 'C40_GRID_N', 'C43_PLACE', 'C43_SRV_NM', 'C43_SRV_ID',
})

def _meta_fields(feature_list: list) -> list:
    """כל השדות הנוספים (מטא-דאטה) שאינם שדות גיאומטריה סטנדרטיים ואינם מוחרגים."""
    seen = {}
    for feat in feature_list:
        for k in feat[0].keys():
            if k not in _STANDARD_CSV_COLS and k not in seen and k not in EXCLUDED_META_FIELDS:
                seen[k] = True
    return list(seen.keys())


def _csv_to_shp(csv_path_or_rows, out_dir: Path):
    """Convert a CSV (path or pre-loaded rows) to SHP files per geometry category."""
    import shapefile

    if isinstance(csv_path_or_rows, (str, Path)):
        with open(csv_path_or_rows, encoding="utf-8-sig", newline="") as fh:
            rows = list(csv_mod.DictReader(fh))
    else:
        rows = csv_path_or_rows  # already a list of dicts

    if not rows:
        return 0

    features = _group_features(rows)

    POINT_TYPES    = {"Point", "Block", "Text", "Circle_Center"}
    POLYLINE_TYPES = {"Line", "Polyline", "Arc", "Spline", "Circle_Vertex", "Ellipse"}
    POLYGON_TYPES  = {"Polygon"}

    points   = [f for f in features if f[0].get("GeometryType","") in POINT_TYPES]
    polylines= [f for f in features if f[0].get("GeometryType","") in POLYLINE_TYPES]
    polygons = [f for f in features if f[0].get("GeometryType","") in POLYGON_TYPES]

    out_dir.mkdir(parents=True, exist_ok=True)
    count = 0

    if points:
        p = str(out_dir / "points")
        meta_keys = _meta_fields(points)
        with shapefile.Writer(p, shapefile.POINT) as w:
            w.field("Layer", "C", 50)
            for mk in meta_keys:
                w.field(FIELD_ALIASES.get(mk, mk)[:10], "C", 80)
            for feat in points:
                r = feat[0]
                w.point(float(r["X"]), float(r["Y"]))
                w.record(r.get("Layer",""), *[r.get(mk,"") for mk in meta_keys])
        _write_prj(p + ".prj")
        count += len(points)

    if polylines:
        p = str(out_dir / "lines")
        meta_keys = _meta_fields(polylines)
        with shapefile.Writer(p, shapefile.POLYLINE) as w:
            w.field("Layer",    "C", 50)
            w.field("Length_m", "N", 15, 3)
            for mk in meta_keys:
                w.field(FIELD_ALIASES.get(mk, mk)[:10], "C", 80)
            for feat in polylines:
                pts = [(float(r["X"]), float(r["Y"])) for r in feat]
                if len(pts) >= 2:
                    w.line([pts])
                    r0 = feat[0]
                    w.record(r0.get("Layer",""), float(r0.get("Length_m",0) or 0),
                             *[r0.get(mk,"") for mk in meta_keys])
        _write_prj(p + ".prj")
        count += len(polylines)

    if polygons:
        p = str(out_dir / "polygons")
        meta_keys = _meta_fields(polygons)
        with shapefile.Writer(p, shapefile.POLYGON) as w:
            w.field("Layer",    "C", 50)
            w.field("Area_sqm", "N", 18, 2)
            w.field("Length_m", "N", 15, 3)
            for mk in meta_keys:
                w.field(FIELD_ALIASES.get(mk, mk)[:10], "C", 80)
            for feat in polygons:
                pts = [(float(r["X"]), float(r["Y"])) for r in feat]
                if len(pts) >= 3:
                    if pts[0] != pts[-1]:
                        pts.append(pts[0])
                    w.poly([pts])
                    r0 = feat[0]
                    w.record(r0.get("Layer",""),
                             float(r0.get("Area_sqm",0) or 0),
                             float(r0.get("Length_m",0) or 0),
                             *[r0.get(mk,"") for mk in meta_keys])
        _write_prj(p + ".prj")
        count += len(polygons)

    return count


def _rows_to_kml(kml_mod, rows: list, kml_path: str):
    """Write rows to a temp CSV then convert to KML via csv_to_kml module."""
    import tempfile, os as _os
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False,
            encoding="utf-8-sig", newline=""
        ) as tf:
            w = csv_mod.DictWriter(tf, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)
            tmp = tf.name
        kml_mod.csv_to_kml(tmp, kml_path)
    finally:
        if tmp:
            try: _os.unlink(tmp)
            except: pass


def _run_step3(params: dict):
    """Legacy CSV → SHP/KML step (kept for backward compat)."""
    global _job_running

    files      = [Path(p) for p in params["files"]]
    output_dir = Path(params["output_dir"])
    fmt        = params.get("format", "kml")   # "kml" | "shp" | "both"
    output_dir.mkdir(parents=True, exist_ok=True)
    total = len(files)

    if total == 0:
        _job_queue.put({"type": "error", "message": "לא נבחרו קבצים"})
        _job_queue.put({"type": "done_thread"})
        _job_running = False
        return

    kml_mod = None
    if fmt in ("kml", "both"):
        try:
            kml_mod = _load_kml_converter()
        except Exception as e:
            _job_queue.put({"type": "error", "message": str(e)})
            _job_queue.put({"type": "done_thread"})
            _job_running = False
            return

    _job_queue.put({"type": "start", "total": total})

    ok = errors = 0
    t_start = time.time()

    for i, csv_file in enumerate(files):
        t0 = time.time()
        count = 0
        try:
            with open(csv_file, encoding="utf-8-sig", newline="") as fh:
                all_rows = list(csv_mod.DictReader(fh))

            if all_rows and "SourceFile" in all_rows[0]:
                groups: dict = {}
                for row in all_rows:
                    groups.setdefault(row["SourceFile"], []).append(row)
                for src_name, src_rows in groups.items():
                    if fmt in ("kml", "both") and kml_mod:
                        kml_out = output_dir / (src_name + ".kml")
                        _rows_to_kml(kml_mod, src_rows, str(kml_out))
                        count += 1
                    if fmt in ("shp", "both"):
                        shp_out = output_dir / src_name
                        count += _csv_to_shp(src_rows, shp_out)
            else:
                if fmt in ("kml", "both") and kml_mod:
                    kml_out = output_dir / (csv_file.stem + ".kml")
                    _rows_to_kml(kml_mod, all_rows, str(kml_out))
                    count += 1
                if fmt in ("shp", "both"):
                    shp_out = output_dir / csv_file.stem
                    count += _csv_to_shp(all_rows, shp_out)

            ok += 1
            status, error = "ok", ""
        except Exception as e:
            errors += 1
            status, error = "error", str(e)

        _job_queue.put({
            "type": "progress",
            "file": csv_file.name, "status": status, "count": count, "error": error,
            "elapsed": round(time.time() - t0, 3),
            "processed": i + 1, "total": total,
            "ok": ok, "errors": errors,
        })

    _job_queue.put({
        "type": "done", "total": total,
        "ok": ok, "errors": errors,
        "output_dir": str(output_dir),
        "format": fmt,
        "elapsed": round(time.time() - t_start, 2),
    })
    _job_queue.put({"type": "done_thread"})
    _job_running = False


_RZ_PREFIXES  = ('Mt_', 'At_', 'F5_')
_TZR_PREFIXES = ('C40_', 'C42_', 'C43_')

def _row_map_type(row: dict) -> str:
    """זיהוי סוג מפה לפי שמות שדות (fallback). מחזיר 'RZ', 'TZR', או ''."""
    for k in row:
        if k.startswith(_TZR_PREFIXES): return 'TZR'
        if k.startswith(_RZ_PREFIXES):  return 'RZ'
    return ''

def _row_map_type_reliable(row: dict) -> str:
    """זיהוי סוג מפה: קודם לפי _survey_cache (שכבת חילוץ), fallback לפי פרפיקסי שדות."""
    source = row.get('SourceFile', '')
    if source and source in _survey_cache:
        mt = _survey_cache[source].get('map_type', '')
        if mt in ('RZ', 'TZR'):
            return mt
    return _row_map_type(row)


def _run_export(params: dict):
    """Write cached data to disk.
    Separate mode: parallelized per-map with ThreadPoolExecutor (each map → own file).
    Merged mode: unchanged (single-threaded, single output file)."""
    global _job_running

    output_dir = Path(params.get("output_dir", ""))
    exports    = params.get("exports", [])   # list of {format, mode}

    if not _parsed_cache:
        _job_queue.put({"type": "error", "message": "אין נתונים בזיכרון — הרץ קודם את שלב 2"})
        _job_queue.put({"type": "done_thread"})
        _job_running = False
        return

    if not output_dir or not str(output_dir).strip():
        _job_queue.put({"type": "error", "message": "נא לבחור תיקיית יעד"})
        _job_queue.put({"type": "done_thread"})
        _job_running = False
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    total = len(exports)

    if total == 0:
        _job_queue.put({"type": "error", "message": "לא נבחר אף פורמט לייצוא"})
        _job_queue.put({"type": "done_thread"})
        _job_running = False
        return

    # Load KML module if any export uses it
    kml_mod = None
    if any(e.get("format") == "kml" for e in exports):
        try:
            kml_mod = _load_kml_converter()
        except Exception as e:
            _job_queue.put({"type": "error", "message": str(e)})
            _job_queue.put({"type": "done_thread"})
            _job_running = False
            return

    _job_queue.put({"type": "start", "total": total})

    ok = errors = 0
    output_files = []
    t_start = time.time()

    for i, exp in enumerate(exports):
        fmt  = exp.get("format", "csv")    # "csv" | "kml" | "shp"
        mode = exp.get("mode", "separate") # "merged" | "separate"
        t0   = time.time()
        count = 0
        label = f"{fmt.upper()} — {'משולב' if mode=='merged' else 'נפרד'}"
        try:
            if mode == "merged":
                all_rows = []
                for map_name, rows in _parsed_cache.items():
                    for row in rows:
                        r = dict(row); r["SourceFile"] = map_name
                        all_rows.append(r)

                if fmt == "csv":
                    out = output_dir / "combined.csv"
                    _write_csv_rows(all_rows, out)
                    output_files.append(str(out)); count = len(all_rows)
                elif fmt == "kml":
                    out = output_dir / "combined.kml"
                    _rows_to_kml(kml_mod, all_rows, str(out))
                    output_files.append(str(out)); count = 1
                elif fmt == "shp":
                    by_type: dict = {'RZ': [], 'TZR': [], '': []}
                    for r in all_rows:
                        by_type[_row_map_type_reliable(r)].append(r)
                    multi = sum(1 for v in by_type.values() if v) > 1
                    _tnames = {'RZ': 'combined_rz', 'TZR': 'combined_tzr', '': 'combined'}
                    for mt, mt_rows in by_type.items():
                        if not mt_rows:
                            continue
                        shp_out = output_dir / (_tnames[mt] if multi else 'combined')
                        count += _csv_to_shp(mt_rows, shp_out)
                        output_files.append(str(shp_out))

            else:  # separate — parallel per-map write
                map_items = list(_parsed_cache.items())
                n_exp     = min(os.cpu_count() or 4, 4)

                def _export_one(item):
                    map_name, rows = item
                    local_files, local_count = [], 0
                    if fmt == "csv":
                        out = output_dir / (map_name + ".csv")
                        _write_csv_rows(rows, out)
                        local_files.append(str(out)); local_count += len(rows)
                    elif fmt == "kml":
                        out = output_dir / (map_name + ".kml")
                        _rows_to_kml(kml_mod, rows, str(out))
                        local_files.append(str(out)); local_count += 1
                    elif fmt == "shp":
                        shp_out = output_dir / map_name
                        local_count += _csv_to_shp(rows, shp_out)
                        local_files.append(str(shp_out))
                    return local_files, local_count

                with ThreadPoolExecutor(max_workers=n_exp) as xpool:
                    futs = [xpool.submit(_export_one, item) for item in map_items]
                    for fut in as_completed(futs):
                        local_files, local_count = fut.result()
                        count += local_count
                        output_files.extend(local_files)

            ok += 1; status, error = "ok", ""
        except Exception as e:
            errors += 1; status, error = "error", str(e)

        _job_queue.put({
            "type": "progress",
            "label": label, "format": fmt, "mode": mode,
            "status": status, "count": count, "error": error,
            "elapsed": round(time.time() - t0, 3),
            "processed": i + 1, "total": total,
            "ok": ok, "errors": errors,
        })

    _job_queue.put({
        "type": "done", "total": total,
        "ok": ok, "errors": errors,
        "output_files": output_files,
        "output_dir": str(output_dir),
        "elapsed": round(time.time() - t_start, 2),
    })
    _job_queue.put({"type": "done_thread"})
    _job_running = False


# ═══════════════════════════════════════════════════════════════════════════
# LEGACY BATCH CONVERT JOB — DXF/DWG → SHP directly (runs in background thread)
# ═══════════════════════════════════════════════════════════════════════════

def _run_convert(params: dict):
    global _job_running
    try:
        mod          = _load_converter()
        _process_one = mod._process_one
    except Exception as e:
        _job_queue.put({"type": "error", "message": str(e)})
        _job_queue.put({"type": "done_thread"})
        _job_running = False
        return

    files      = [Path(p) for p in params["files"]]
    input_dir  = Path(params["input_dir"])
    output_dir = Path(params["output_dir"])
    layer      = params["layer"]
    oda_path   = params.get("oda_path") or None
    out_mode   = params.get("output_mode", "per_map")
    workers    = params.get("workers") or None
    n_workers  = int(workers) if workers else min(os.cpu_count() or 4, 8)

    total = len(files)
    if total == 0:
        _job_queue.put({"type": "error", "message": "לא נבחרו קבצים"})
        _job_queue.put({"type": "done_thread"})
        _job_running = False
        return

    _job_queue.put({"type": "start", "total": total})

    tasks = []
    for f in files:
        out_d = resolve_out_dir(f, input_dir, output_dir, out_mode)
        out_d.mkdir(parents=True, exist_ok=True)
        tasks.append((str(f), str(out_d), layer, oda_path, False))

    ok = empty = errors = 0
    total_polys = 0
    t_start     = time.time()
    processed   = 0

    with ThreadPoolExecutor(max_workers=n_workers) as pool:
        futures = {pool.submit(_process_one, t): t for t in tasks}
        for future in as_completed(futures):
            res        = future.result()
            processed += 1
            if   res["status"] == "ok":    ok    += 1; total_polys += res["count"]
            elif res["status"] == "empty": empty += 1
            else:                          errors += 1

            _job_queue.put({
                "type": "progress",
                "file": res["file"], "status": res["status"],
                "count": res["count"], "error": res["error"],
                "elapsed": round(res["elapsed"], 3),
                "processed": processed, "total": total,
                "ok": ok, "empty": empty, "errors": errors,
                "total_polys": total_polys,
            })

    elapsed = time.time() - t_start
    _job_queue.put({
        "type": "done", "total": total,
        "ok": ok, "empty": empty, "errors": errors,
        "total_polys": total_polys,
        "elapsed": round(elapsed, 2),
        "rate": round(total / elapsed, 1) if elapsed > 0 else 0,
        "output_dir": str(output_dir),
        "out_mode": out_mode,
    })
    _job_queue.put({"type": "done_thread"})
    _job_running = False


# ═══════════════════════════════════════════════════════════════════════════
# SESSION SAVE / LOAD
# ═══════════════════════════════════════════════════════════════════════════

def _do_save_session(params: dict) -> dict:
    global _session_name
    name     = params.get("name", "").strip()
    save_dir = params.get("save_dir", "").strip()
    settings = params.get("settings", {})

    if not name:
        return {"error": "נא להזין שם לעבודה"}
    if not save_dir:
        return {"error": "נא לבחור תיקיית שמירה"}
    if not _parsed_cache:
        return {"error": "אין נתונים בזיכרון — הרץ קודם את שלב 2"}

    save_path  = Path(save_dir) / (name + ".session")
    total_rows = sum(len(rows) for rows in _parsed_cache.values())

    data = {
        "version":      "1",
        "saved_at":     time.strftime("%Y-%m-%dT%H:%M:%S"),
        "name":         name,
        "map_count":    len(_parsed_cache),
        "total_rows":   total_rows,
        "parsed_layer": _parsed_layer,
        "settings":     settings,
        "maps":         _parsed_cache,
        "survey":       _survey_cache,
    }

    try:
        Path(save_dir).mkdir(parents=True, exist_ok=True)
        with gzip.open(str(save_path), "wt", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        _session_name = name
        return {"ok": True, "path": str(save_path), "name": name}
    except Exception as e:
        return {"error": str(e)}


def _do_load_session(params: dict) -> dict:
    global _parsed_cache, _survey_cache, _parsed_layer, _session_name
    path = params.get("path", "").strip()
    if not path:
        return {"error": "נא לבחור קובץ session"}
    fp = Path(path)
    if not fp.exists():
        return {"error": f"הקובץ לא נמצא: {path}"}

    try:
        with gzip.open(str(fp), "rt", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return {"error": f"שגיאה בקריאת הקובץ: {e}"}

    _parsed_cache  = {k: list(v) for k, v in data.get("maps",   {}).items()}
    _survey_cache  = {k: dict(v) for k, v in data.get("survey", {}).items()}
    _parsed_layer  = data.get("parsed_layer", "")
    _session_name  = data.get("name", fp.stem)

    total_rows     = sum(len(rows) for rows in _parsed_cache.values())
    total_features = sum(len(_group_features(rows)) for rows in _parsed_cache.values())

    return {
        "ok":             True,
        "name":           _session_name,
        "map_count":      len(_parsed_cache),
        "total_rows":     total_rows,
        "total_features": total_features,
        "layer":          _parsed_layer,
        "settings":       data.get("settings", {}),
        "map_names":      list(_parsed_cache.keys()),
    }


# ═══════════════════════════════════════════════════════════════════════════
# SHP HELPERS (for map rendering)
# ═══════════════════════════════════════════════════════════════════════════

def read_shp_data(out_dir: str, filter_map: str = "", recursive: bool = True) -> dict:
    import shapefile as _shp
    base = Path(out_dir)
    maps_data = {}
    pattern = "**/*.shp" if recursive else "*.shp"
    for shp_file in sorted(base.glob(pattern)):
        map_name = shp_file.stem if not recursive else shp_file.parent.name
        if filter_map and map_name != filter_map:
            continue
        try:
            sf = _shp.Reader(str(shp_file))
            field_names = [f[0] for f in sf.fields[1:]]  # skip DeletionFlag
            for sr in sf.shapeRecords():
                if not sr.shape.points:
                    continue
                coords = [[p[0], p[1]] for p in sr.shape.points]
                attrs  = {}
                for k, v in zip(field_names, sr.record):
                    try:
                        attrs[k] = v.strip() if isinstance(v, str) else v
                    except Exception:
                        attrs[k] = v
                maps_data.setdefault(map_name, []).append({"coords": coords, "attrs": attrs})
        except Exception:
            pass
    return maps_data


def list_shp_maps(out_dir: str, recursive: bool = True) -> list:
    base    = Path(out_dir)
    pattern = "**/*.shp" if recursive else "*.shp"
    names   = []
    for f in sorted(base.glob(pattern)):
        n = f.parent.name if recursive else f.stem
        if n not in names:
            names.append(n)
    return names


def build_zip(out_dir: str, selected_maps: list) -> bytes:
    base = Path(out_dir)
    buf  = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for shp_file in sorted(base.rglob("*.shp")):
            map_name = shp_file.parent.name
            if selected_maps and map_name not in selected_maps:
                continue
            for ext in (".shp", ".dbf", ".shx", ".prj", ".cpg"):
                sc = shp_file.with_suffix(ext)
                if sc.exists():
                    zf.write(sc, str(sc.relative_to(base)))
    buf.seek(0)
    return buf.read()


# ═══════════════════════════════════════════════════════════════════════════
# TRAINING DATA — persistence + row builder
# ═══════════════════════════════════════════════════════════════════════════

def _normalize_date(raw) -> str:
    """מנרמל כל פורמט תאריך נפוץ ל-YYYY-MM-DD (נדרש ע"י input[type=date]).
    מחזיר מחרוזת ריקה אם לא ניתן לפרסר."""
    if not raw:
        return ""
    s = str(raw).strip()
    if not s:
        return ""
    from datetime import datetime
    # פורמטים שנבדקים לפי סדר
    for fmt in ("%d/%m/%Y", "%d.%m.%Y", "%d-%m-%Y",
                "%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    # תאריך עם שעה (DD/MM/YYYY HH:MM)
    for fmt in ("%d/%m/%Y %H:%M", "%d.%m.%Y %H:%M"):
        try:
            return datetime.strptime(s[:16], fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return ""   # לא הצלחנו לפרסר — מחזירים ריק


def _itm_to_wgs84(x: float, y: float) -> tuple:
    try:
        from pyproj import Transformer
        t = Transformer.from_crs("EPSG:2039", "EPSG:4326", always_xy=True)
        lon, lat = t.transform(x, y)
        return round(lat, 6), round(lon, 6)
    except Exception:
        return None, None


def _build_training_rows(office_lat: float = 32.0883, office_lon: float = 34.8878) -> list:
    import math

    def _haversine(lat1, lon1, lat2, lon2):
        R = 6371.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat / 2) ** 2
             + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
             * math.sin(dlon / 2) ** 2)
        return round(R * 2 * math.asin(math.sqrt(a)), 3)

    results = []
    for map_name, rows in _parsed_cache.items():
        survey   = _survey_cache.get(map_name, {})
        features = _group_features(rows)
        polys    = [f for f in features if f[0].get("GeometryType") == "Polygon"]
        if not polys:
            continue

        main  = max(polys, key=lambda f: float(f[0].get("Area_sqm") or 0))
        pts   = [(float(r["X"]), float(r["Y"])) for r in main]
        area  = float(main[0].get("Area_sqm") or 0)
        perim = float(main[0].get("Length_m") or 0)
        shape_index = round(perim ** 2 / (4 * math.pi * area), 4) if area > 0 else None

        cx  = sum(p[0] for p in pts) / len(pts)
        cy  = sum(p[1] for p in pts) / len(pts)
        lat, lon = _itm_to_wgs84(cx, cy)
        dist_km  = _haversine(lat, lon, office_lat, office_lon) if lat is not None else None

        meta     = rows[0] if rows else {}
        map_type = survey.get("map_type", "")

        results.append({
            "project_id":        map_name,
            "project_name":      map_name,
            "map_type":          map_type,
            "survey_type":       ("לקדסטר" if map_type == "RZ"
                                  else ("תצ\"ר" if map_type == "TZR" else "")),
            "site_type":         "mixed",
            "client_name":       meta.get("Mt_CLIENT") or meta.get("C40_ORDERE", ""),
            "city":              meta.get("At_SETTLEM") or meta.get("C40_SETTLE", ""),
            "gush":              meta.get("At_GUSH")    or meta.get("C40_GUSH_N", ""),
            "helka":             meta.get("At_PARCEL")  or meta.get("C40_PARCEL", ""),
            "survey_date":       _normalize_date(meta.get("F5_SURVEY_") or meta.get("C43_SRV_DT", "")),
            "finish_date":       _normalize_date(meta.get("F5_FINISH_") or meta.get("C43_FINISH", "")),
            "official_area_sqm": meta.get("At_AREA", ""),
            "area_sqm":          round(area, 2),
            "perimeter_m":       round(perim, 2),
            "shape_index":       shape_index,
            "center_lat":        lat,
            "center_lon":        lon,
            "distance_km":       dist_km,
            "survey_points":     survey.get("count", 0),
            "quoted_price":      "",
            "actual_hours":      "",
            "hourly_cost":       180,
            "profit":            "",
            "profit_margin_pct": "",
            "status":            "completed",
            "is_accepted":       "",
        })
    return results


def _training_load() -> list:
    if not TRAINING_DB.exists():
        return []
    try:
        return json.loads(TRAINING_DB.read_text("utf-8"))
    except Exception:
        return []


def _training_save(rows: list) -> int:
    existing = {r["project_id"]: r for r in _training_load() if r.get("project_id")}
    for r in rows:
        if r.get("project_id"):
            existing[r["project_id"]] = r
    merged = list(existing.values())
    TRAINING_DB.write_text(json.dumps(merged, ensure_ascii=False, indent=2), "utf-8")
    return len(merged)


# ═══════════════════════════════════════════════════════════════════════════
# GEOMETRY HELPERS — polygon features from WGS84 coords or DWG file
# ═══════════════════════════════════════════════════════════════════════════

def _haversine_km(lat1, lon1, lat2, lon2):
    import math
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    return round(R * 2 * math.asin(math.sqrt(a)), 3)


def _estimate_points_raw(area_sqm: float, map_type: str = "", terrain: str = "mixed") -> int:
    """Rule-based survey-points estimate: 400 pts per 500 sqm (RZ baseline)."""
    base           = (area_sqm / 500.0) * 400.0
    map_factors    = {"RZ": 1.0, "TZR": 0.5}
    terrain_factors = {"open": 0.75, "mixed": 1.0, "built": 1.25}
    mt  = map_factors.get(map_type, 0.75)
    ter = terrain_factors.get(terrain, 1.0)
    return max(1, round(base * mt * ter))


def _calc_geometry_from_wgs84(coords: list, office_lat=32.0883, office_lon=34.8878,
                               map_type: str = "", terrain: str = "mixed") -> dict:
    """coords = [[lat, lon], ...] in WGS84. Returns geometry features dict."""
    import math
    try:
        from pyproj import Transformer
        t_fwd = Transformer.from_crs("EPSG:4326", "EPSG:2039", always_xy=True)
        t_rev = Transformer.from_crs("EPSG:2039", "EPSG:4326", always_xy=True)
    except ImportError:
        return {"error": "pyproj לא מותקן — הרץ: pip install pyproj"}

    if len(coords) < 3:
        return {"error": "פוליגון דורש לפחות 3 נקודות"}

    itm = [t_fwd.transform(lon, lat) for lat, lon in coords]
    n   = len(itm)

    area = abs(sum(
        itm[i][0] * itm[(i + 1) % n][1] - itm[(i + 1) % n][0] * itm[i][1]
        for i in range(n)
    )) / 2

    perim = sum(
        math.sqrt((itm[(i + 1) % n][0] - itm[i][0]) ** 2 +
                  (itm[(i + 1) % n][1] - itm[i][1]) ** 2)
        for i in range(n)
    )

    shape_index = round(perim ** 2 / (4 * math.pi * area), 4) if area > 0 else 1.0

    cx = sum(p[0] for p in itm) / n
    cy = sum(p[1] for p in itm) / n
    clon, clat = t_rev.transform(cx, cy)

    dist_km          = _haversine_km(clat, clon, office_lat, office_lon)
    pts_raw          = _estimate_points_raw(area, map_type, terrain)
    pts_ml           = _impute_survey_points(area, map_type)

    return {
        "area_sqm":          round(area, 2),
        "perimeter_m":       round(perim, 2),
        "shape_index":       round(shape_index, 4),
        "center_lat":        round(clat, 6),
        "center_lon":        round(clon, 6),
        "distance_km":       round(dist_km, 3),
        "survey_points_raw": pts_raw,
        "survey_points_ml":  pts_ml,
        "survey_points_est": pts_ml if pts_ml is not None else pts_raw,
    }


def _impute_survey_points(area_sqm: float, map_type: str = "", k: int = 5):
    """Estimate survey_points from k nearest historical projects by area + map_type."""
    rows = _training_load()
    scored = []
    for r in rows:
        try:
            r_pts  = int(float(r.get("survey_points") or 0))
            r_area = float(r.get("area_sqm") or 0)
            if r_pts <= 0 or r_area <= 0:
                continue
            r_mt  = str(r.get("map_type", ""))
            ratio = max(area_sqm, r_area) / max(min(area_sqm, r_area), 1)
            pen   = 1.0 if r_mt == map_type else 2.0
            scored.append((ratio * pen, r_pts))
        except (ValueError, TypeError):
            continue
    if not scored:
        return None
    scored.sort(key=lambda x: x[0])
    top = [pts for _, pts in scored[:k]]
    return round(sum(top) / len(top))


def _extract_polygon_from_dwg(dwg_path: str, office_lat=32.0883, office_lon=34.8878) -> dict:
    """DWG → DXF → parse M1200/C1602_0 → return geometry features + WGS84 polygon."""
    import math, shutil as _sh
    fp = Path(dwg_path)
    if not fp.exists():
        return {"error": f"קובץ לא נמצא: {dwg_path}"}

    try:
        mod  = _load_csv_converter()
        conv = mod.DwgToCsvConverter()
    except Exception as e:
        return {"error": f"שגיאה בטעינת הממיר: {e}"}

    tmp_cleanup = None
    try:
        dxf_path = conv.convert_dwg_to_dxf(str(fp))
        if not dxf_path or not Path(dxf_path).exists():
            return {"error": "ההמרה ל-DXF נכשלה — ודא שנתיב ODA מוגדר"}
        tmp_cleanup = str(Path(dxf_path).parent)

        stem     = fp.stem
        layer    = _auto_layer(stem) or "M1200"
        map_type = ("RZ"  if layer == "M1200"
                    else "TZR" if layer.upper().startswith("C1602") else "")

        rows = conv.parse_dxf(dxf_path, [layer], polygon_only=True)
        if not rows:
            fallback = "C1602_0" if layer == "M1200" else "M1200"
            rows     = conv.parse_dxf(dxf_path, [fallback], polygon_only=True)
            if rows:
                map_type = "TZR" if fallback.upper().startswith("C1602") else "RZ"
            else:
                return {"error": f"לא נמצאו פוליגונים בשכבות {layer} / {fallback}"}

        features = _group_features(rows)
        polys    = [f for f in features if f[0].get("GeometryType") == "Polygon"]
        if not polys:
            return {"error": "לא נמצאו גאומטריות פוליגון"}

        main      = max(polys, key=lambda f: float(f[0].get("Area_sqm") or 0))
        itm_pts   = [(float(r["X"]), float(r["Y"])) for r in main]
        area      = float(main[0].get("Area_sqm") or 0)
        perim     = float(main[0].get("Length_m") or 0)
        si        = round(perim ** 2 / (4 * math.pi * area), 4) if area > 0 else 1.0

        cx = sum(p[0] for p in itm_pts) / len(itm_pts)
        cy = sum(p[1] for p in itm_pts) / len(itm_pts)
        clat, clon = _itm_to_wgs84(cx, cy)
        dist_km    = _haversine_km(clat, clon, office_lat, office_lon) if clat else None

        polygon_wgs84 = []
        try:
            from pyproj import Transformer
            t = Transformer.from_crs("EPSG:2039", "EPSG:4326", always_xy=True)
            for x, y in itm_pts:
                lon_, lat_ = t.transform(x, y)
                polygon_wgs84.append([round(lat_, 7), round(lon_, 7)])
        except Exception:
            pass

        return {
            "area_sqm":          round(area, 2),
            "perimeter_m":       round(perim, 2),
            "shape_index":       round(si, 4),
            "center_lat":        round(clat, 6) if clat else None,
            "center_lon":        round(clon, 6) if clon else None,
            "distance_km":       round(dist_km, 3) if dist_km else None,
            "polygon_wgs84":     polygon_wgs84,
            "map_type":          map_type,
            "survey_points_est": _impute_survey_points(area, map_type),
            "source":            "dwg",
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        if tmp_cleanup:
            _sh.rmtree(tmp_cleanup, ignore_errors=True)


# ═══════════════════════════════════════════════════════════════════════════
# PROFITABILITY MODEL — load / train / predict
# ═══════════════════════════════════════════════════════════════════════════

_PROFIT_DIR  = _DIR / "profitability_model"
_PROFIT: dict = {}   # populated by _profit_load()

_PROFIT_FEATURES = [
    "area_sqm_log", "survey_points", "distance_km",
    "shape_index", "quoted_price_log", "map_type_rz",
]
_PROFIT_LABELS_HE = {
    "area_sqm_log":     "שטח החלקה",
    "survey_points":    "נקודות מדידה",
    "distance_km":      "מרחק מהמשרד",
    "shape_index":      "מורכבות צורה",
    "quoted_price_log": "מחיר ההצעה",
    "map_type_rz":      "סוג מדידה (RZ)",
}


def _profit_load():
    """Load model artifacts from profitability_model/*.pkl + feature_meta.json."""
    global _PROFIT
    clf_p  = _PROFIT_DIR / "model_clf.pkl"
    reg_p  = _PROFIT_DIR / "model_reg.pkl"
    sc_p   = _PROFIT_DIR / "scaler.pkl"
    meta_p = _PROFIT_DIR / "feature_meta.json"

    if not meta_p.exists():
        _PROFIT = {"loaded": False, "error": "מודל לא מאומן עדיין — לחץ 'אמן מחדש'"}
        return

    try:
        import numpy as _np_load
        meta = json.loads(meta_p.read_text("utf-8"))

        # Reconstruct inference objects from JSON coefficients (no pickle / no sklearn needed)
        _sm  = _np_load.array(meta["scaler_mean"])
        _ss  = _np_load.array(meta["scaler_scale"])
        _cc  = _np_load.array(meta["coef"])
        _ci  = float(meta.get("clf_intercept", 0.0))
        _rc  = _np_load.array(meta["reg_coef"])
        _ri  = float(meta["reg_intercept"])

        class _Scaler:
            def transform(self, X):
                return (_np_load.array(X) - _sm) / _ss

        class _Clf:
            coef_ = _cc.reshape(1, -1)
            intercept_ = _np_load.array([_ci])
            def predict_proba(self, X):
                z  = _np_load.array(X) @ _cc + _ci
                p1 = 1.0 / (1.0 + _np_load.exp(-_np_load.clip(z, -500, 500)))
                p1 = p1.flatten()
                return _np_load.column_stack([1 - p1, p1])

        class _Reg:
            coef_      = _rc
            intercept_ = _ri
            def predict(self, X):
                return _np_load.array(X) @ _rc + _ri

        clf    = _Clf()
        reg    = _Reg()
        scaler = _Scaler()
        _PROFIT = {"loaded": True, "clf": clf, "reg": reg,
                   "scaler": scaler, "meta": meta}
        print(f"  [ML] model loaded ({meta.get('n_train',0)} training rows)")
    except Exception as e:
        _PROFIT = {"loaded": False, "error": str(e)}


def _profit_train_inline():
    """Run the training script in-process and reload the model."""
    import importlib.util, sys as _sys
    train_py = _PROFIT_DIR / "train.py"
    if not train_py.exists():
        return {"ok": False, "error": "train.py לא נמצא"}
    try:
        spec = importlib.util.spec_from_file_location("profit_train", train_py)
        mod  = importlib.util.module_from_spec(spec)
        _sys.modules["profit_train"] = mod   # register before training so pickle can find classes
        spec.loader.exec_module(mod)
        mod.train(save=True)
        _profit_load()
        if not _PROFIT.get("loaded"):
            return {"ok": False, "error": _PROFIT.get("error", "שגיאה לא ידועה")}
        meta = _PROFIT["meta"]
        return {
            "ok": True,
            "n_train":   meta.get("n_train", 0),
            "cv_acc":    round(meta.get("cv_accuracy_mean", 0), 3),
            "cv_std":    round(meta.get("cv_accuracy_std",  0), 3),
        }
    except SystemExit as e:
        return {"ok": False, "error": f"אימון נכשל — {e}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _profit_predict(params: dict) -> dict:
    """Run inference. Returns verdict, confidence, margin, factor list, similar projects."""
    import math as _m

    if not _PROFIT.get("loaded"):
        return {"error": _PROFIT.get("error", "מודל לא נטען")}

    try:
        area   = float(params.get("area_sqm")      or 0)
        pts    = float(params.get("survey_points")  or 0)
        dist   = float(params.get("distance_km")    or 0)
        si     = float(params.get("shape_index")    or 1)
        qp     = float(params.get("quoted_price")   or 0)
        mt_rz  = 1 if str(params.get("map_type", "")).upper() == "RZ" else 0
    except (ValueError, TypeError) as e:
        return {"error": f"פרמטר לא תקין: {e}"}

    clf    = _PROFIT["clf"]
    scaler = _PROFIT["scaler"]
    meta   = _PROFIT["meta"]

    import numpy as _np
    x_raw = _np.array([[
        _m.log1p(area), pts, dist, si, _m.log1p(qp), mt_rz
    ]])
    x_sc = scaler.transform(x_raw)

    prob_profitable = float(clf.predict_proba(x_sc)[0][1])

    margin_threshold = meta.get("margin_threshold", 20.0)
    borderline_lo    = meta.get("borderline_lo",    10.0)

    # Cost is fixed per survey point — independent of quoted price
    _COST_PER_POINT = 7.0
    actual_cost_est = pts * _COST_PER_POINT
    expected_profit = qp - actual_cost_est
    real_margin     = (expected_profit / qp * 100) if qp > 0 else 0.0

    if prob_profitable >= 0.60 and real_margin >= margin_threshold:
        verdict = "profitable"
    elif prob_profitable >= 0.40 or real_margin >= borderline_lo:
        verdict = "borderline"
    else:
        verdict = "not_profitable"

    # ── Feature importance for this specific prediction ─────────────────────
    coef       = _np.array(meta["coef"])
    feat_std   = _np.array(meta.get("scaler_scale", [1]*6))
    importance = _np.abs(coef * feat_std)
    importance = importance / importance.sum() if importance.sum() > 0 else importance

    top_factors = sorted([
        {
            "key":        _PROFIT_FEATURES[i],
            "name":       _PROFIT_LABELS_HE.get(_PROFIT_FEATURES[i], _PROFIT_FEATURES[i]),
            "importance": round(float(importance[i]) * 100, 1),
            "direction":  1 if coef[i] > 0 else -1,
        }
        for i in range(len(_PROFIT_FEATURES))
    ], key=lambda x: x["importance"], reverse=True)

    # ── Similar historical projects ──────────────────────────────────────────
    similar = _profit_find_similar(area, pts, dist, qp, mt_rz, top_n=5)

    return {
        "verdict":             verdict,
        "prob_profitable":     round(prob_profitable * 100, 1),
        "expected_margin_pct": round(real_margin, 1),
        "quoted_price":        qp,
        "expected_cost":       round(actual_cost_est, 0),
        "expected_profit":     round(expected_profit, 0),
        "top_factors":         top_factors,
        "similar_projects":    similar,
        "model_info": {
            "n_train":      meta.get("n_train", 0),
            "cv_accuracy":  round(meta.get("cv_accuracy_mean", 0) * 100, 1),
        }
    }


def _profit_find_similar(area, pts, dist, qp, mt_rz, top_n=5):
    """Return top_n most similar completed projects from training_data.json."""
    import math as _m
    rows = _training_load()
    scored = []
    for r in rows:
        try:
            if str(r.get("status","")) not in ("completed","submitted","archived"):
                continue
            if not r.get("profit_margin_pct") or not r.get("quoted_price"):
                continue
            r_area = float(r.get("area_sqm") or 0)
            r_pts  = float(r.get("survey_points") or 0)
            r_dist = float(r.get("distance_km") or 0)
            r_qp   = float(r.get("quoted_price") or 0)
            r_mt   = 1 if str(r.get("map_type","")).upper()=="RZ" else 0
            # normalized euclidean distance on log-scale features
            d = _m.sqrt(
                (_m.log1p(area) - _m.log1p(r_area))**2 +
                (pts   - r_pts )**2 / max(1, max(pts, r_pts))**2 +
                (dist  - r_dist)**2 / max(1, max(dist, r_dist))**2 +
                (_m.log1p(qp) - _m.log1p(r_qp))**2 +
                (mt_rz - r_mt)**2
            )
            scored.append((d, r))
        except (ValueError, TypeError):
            continue

    scored.sort(key=lambda x: x[0])
    result = []
    for _, r in scored[:top_n]:
        margin = float(r.get("profit_margin_pct") or 0)
        result.append({
            "project_id":       r.get("project_id",""),
            "project_name":     r.get("project_name",""),
            "area_sqm":         r.get("area_sqm",""),
            "distance_km":      r.get("distance_km",""),
            "quoted_price":     r.get("quoted_price",""),
            "profit_margin_pct":round(margin, 1),
            "map_type":         r.get("map_type",""),
            "city":             r.get("city",""),
        })
    return result


# טעינה ראשונית בהפעלת השרת
_profit_load()


# ═══════════════════════════════════════════════════════════════════════════
# HTTP HANDLER
# ═══════════════════════════════════════════════════════════════════════════

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def _send_json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_bytes(self, code, data, ctype, filename=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", len(data))
        self.send_header("Access-Control-Allow-Origin", "*")
        if filename:
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(data)

    def _serve_file(self, p, ctype):
        try:
            data = Path(p).read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", len(data))
            self.end_headers()
            self.wfile.write(data)
        except FileNotFoundError:
            self.send_response(404); self.end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        p      = parsed.path
        qs     = parse_qs(parsed.query)

        if p in ("/", "/index.html"):
            self._serve_file(_DIR / "index.html", "text/html; charset=utf-8")

        elif p == "/api/stream":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control",  "no-cache")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            try:
                while True:
                    try:
                        msg  = _job_queue.get(timeout=15)
                        self.wfile.write(("data: " + json.dumps(msg, ensure_ascii=False) + "\n\n").encode())
                        self.wfile.flush()
                        if msg["type"] == "done_thread": break
                    except queue.Empty:
                        self.wfile.write(b": ping\n\n"); self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError): pass

        elif p == "/api/browse":
            try:
                import tkinter as tk
                from tkinter import filedialog
                root = tk.Tk(); root.withdraw()
                root.wm_attributes("-topmost", True)
                folder = filedialog.askdirectory(parent=root, title="בחר תיקייה")
                root.destroy()
                self._send_json(200, {"path": folder.replace("/", "\\") if folder else None})
            except Exception as e:
                self._send_json(500, {"error": str(e)})

        elif p == "/api/browse-file":
            try:
                import tkinter as tk
                from tkinter import filedialog
                root = tk.Tk(); root.withdraw()
                root.wm_attributes("-topmost", True)
                filepath = filedialog.askopenfilename(
                    parent=root, title="בחר קובץ עבודה",
                    filetypes=[("Session files", "*.session"), ("All files", "*.*")],
                )
                root.destroy()
                self._send_json(200, {"path": filepath.replace("/", "\\") if filepath else None})
            except Exception as e:
                self._send_json(500, {"error": str(e)})

        elif p == "/api/shplist":
            d = qs.get("dir", [""])[0]
            if not d: self._send_json(400, {"error": "missing dir"}); return
            try:    self._send_json(200, {"maps": list_shp_maps(d)})
            except Exception as e: self._send_json(500, {"error": str(e)})

        elif p == "/api/geojson":
            d   = qs.get("dir", [""])[0]
            fm  = qs.get("map", [""])[0]
            rec = qs.get("recursive", ["1"])[0] not in ("0", "false", "False")
            if not d: self._send_json(400, {"error": "missing dir"}); return
            try:    self._send_json(200, {"maps": read_shp_data(d, fm, recursive=rec)})
            except Exception as e: self._send_json(500, {"error": str(e)})

        elif p == "/api/list-output":
            try:
                self._send_json(200, do_list_output(qs_flat(qs)))
            except Exception as e: self._send_json(500, {"error": str(e)})

        elif p == "/api/open-folder":
            folder = qs.get("path", [""])[0]
            if folder and Path(folder).exists():
                import subprocess
                subprocess.Popen(["explorer", folder])
            self._send_json(200, {"ok": True})

        elif p == "/api/metadata":
            _STANDARD = {'MapName','Layer','EntityType','GeometryType',
                         'VertexIndex','VertexCount','X','Y','Z',
                         'Color','IsClosed','Length','Area','Notes'}
            result: dict = {}
            for map_name, rows in _parsed_cache.items():
                meta: dict = {}
                for row in rows:
                    for k, v in row.items():
                        if k in _STANDARD or k in EXCLUDED_META_FIELDS:
                            continue
                        display_key = FIELD_ALIASES.get(k, k)
                        if display_key not in meta and v not in (None, ''):
                            meta[display_key] = str(v)
                if meta:
                    result[map_name] = meta
            self._send_json(200, {"metadata": result, "survey": _survey_cache})

        elif p == "/api/map-types":
            try:
                mod = _load_csv_converter()
                self._send_json(200, {"map_types": mod.MAP_TYPES, "rules": mod.MAP_TYPE_RULES})
            except Exception as e:
                self._send_json(500, {"error": str(e)})

        elif p == "/api/layers":
            dxf_dir = qs.get("dir", [""])[0]
            if not dxf_dir:
                self._send_json(400, {"error": "missing dir"}); return
            try:
                dxf_files = sorted(Path(dxf_dir).rglob("*.dxf"))
                layers = _get_dxf_layers([str(f) for f in dxf_files])
                self._send_json(200, {"layers": layers, "dxf_count": len(dxf_files)})
            except Exception as e:
                self._send_json(500, {"error": str(e)})

        elif p == "/api/parsed-geojson":
            fm = qs.get("map", [""])[0]
            try:
                maps_data, geom_summary = _get_parsed_geojson(fm)
                self._send_json(200, {
                    "maps":         maps_data,
                    "layer":        _parsed_layer,
                    "names":        list(_parsed_cache.keys()),
                    "geom_summary": geom_summary,
                })
            except Exception as e:
                self._send_json(500, {"error": str(e)})

        elif p == "/api/training-data":
            try:
                lat = float(qs.get("lat", [32.0883])[0])
                lon = float(qs.get("lon", [34.8878])[0])
                rows = _build_training_rows(office_lat=lat, office_lon=lon)
                self._send_json(200, {"rows": rows, "count": len(rows)})
            except Exception as e:
                self._send_json(500, {"error": str(e)})

        elif p == "/api/training-load":
            try:
                self._send_json(200, {"rows": _training_load()})
            except Exception as e:
                self._send_json(500, {"error": str(e)})

        elif p == "/api/model-status":
            meta = _PROFIT.get("meta", {})
            self._send_json(200, {
                "loaded":      _PROFIT.get("loaded", False),
                "error":       _PROFIT.get("error", ""),
                "n_train":     meta.get("n_train", 0),
                "cv_accuracy": round(meta.get("cv_accuracy_mean", 0) * 100, 1),
                "cv_std":      round(meta.get("cv_accuracy_std",  0) * 100, 1),
                "n_data":      len(_training_load()),
            })

        elif p == "/api/debug-attribs":
            file_path = qs.get("path", [""])[0]
            block_name = qs.get("block", ["FORM_5"])[0]
            layer_name = qs.get("layer", [""])[0] or None
            if not file_path:
                self._send_json(400, {"error": "missing path"}); return
            dxf_path = None
            tmp_cleanup = None
            try:
                import shutil as _shutil
                fp = Path(file_path)
                mod = _load_csv_converter()
                if fp.suffix.lower() == '.dwg':
                    conv = mod.DwgToCsvConverter()
                    dxf_path = conv.convert_dwg_to_dxf(str(fp))
                    if not dxf_path:
                        self._send_json(500, {"error": "DWG conversion failed"}); return
                    tmp_cleanup = str(Path(dxf_path).parent)
                elif fp.suffix.lower() == '.dxf':
                    dxf_path = str(fp)
                else:
                    self._send_json(400, {"error": "unsupported file type"}); return
                instances = mod.debug_block_attribs(dxf_path, block_name, layer_name)
                self._send_json(200, {
                    "file": fp.name,
                    "block": block_name,
                    "layer_filter": layer_name,
                    "instance_count": len(instances),
                    "instances": instances,
                })
            except Exception as e:
                self._send_json(500, {"error": str(e)})
            finally:
                if tmp_cleanup:
                    import shutil as _shutil2
                    _shutil2.rmtree(tmp_cleanup, ignore_errors=True)

        else:
            self.send_response(404); self.end_headers()

    def do_POST(self):
        global _job_running
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        body   = self.rfile.read(length)
        try:    params = json.loads(body) if body else {}
        except: self._send_json(400, {"error": "Invalid JSON"}); return

        if parsed.path == "/api/scan":
            try:    self._send_json(200, do_scan(params))
            except Exception as e: self._send_json(500, {"error": str(e)})

        elif parsed.path in ("/api/step1", "/api/step2", "/api/step1_2", "/api/export", "/api/convert"):
            with _job_lock:
                if _job_running:
                    self._send_json(409, {"error": "Job already running"}); return
                while not _job_queue.empty():
                    try: _job_queue.get_nowait()
                    except: pass
                _job_running = True

            runner_map = {
                "/api/step1":    _run_step1,
                "/api/step2":    _run_step2,
                "/api/step1_2":  _run_step1_2,
                "/api/export":   _run_export,
                "/api/convert":  _run_convert,
            }
            runner = runner_map[parsed.path]
            threading.Thread(target=runner, args=(params,), daemon=True).start()
            self._send_json(200, {"ok": True})

        elif parsed.path == "/api/save-session":
            try:    self._send_json(200, _do_save_session(params))
            except Exception as e: self._send_json(500, {"error": str(e)})

        elif parsed.path == "/api/load-session":
            try:    self._send_json(200, _do_load_session(params))
            except Exception as e: self._send_json(500, {"error": str(e)})

        elif parsed.path == "/api/export-zip":
            out_dir  = params.get("output_dir", "")
            selected = params.get("maps", [])
            if not out_dir: self._send_json(400, {"error": "missing output_dir"}); return
            try:
                data = build_zip(out_dir, selected)
                self._send_bytes(200, data, "application/zip", "shp_export.zip")
            except Exception as e: self._send_json(500, {"error": str(e)})

        elif parsed.path == "/api/training-save":
            rows = params.get("rows", [])
            try:
                total = _training_save(rows)
                self._send_json(200, {"ok": True, "total": total})
            except Exception as e:
                self._send_json(500, {"error": str(e)})

        elif parsed.path == "/api/calc-geometry":
            try:
                coords     = params.get("polygon", [])
                office_lat = float(params.get("office_lat", 32.0883))
                office_lon = float(params.get("office_lon", 34.8878))
                map_type   = params.get("map_type", "")
                terrain    = params.get("terrain", "mixed")
                result     = _calc_geometry_from_wgs84(coords, office_lat, office_lon, map_type, terrain)
                code       = 400 if "error" in result else 200
                self._send_json(code, result)
            except Exception as e:
                self._send_json(500, {"error": str(e)})

        elif parsed.path == "/api/extract-polygon":
            try:
                dwg_path   = params.get("dwg_path", "")
                office_lat = float(params.get("office_lat", 32.0883))
                office_lon = float(params.get("office_lon", 34.8878))
                if not dwg_path:
                    self._send_json(400, {"error": "missing dwg_path"}); return
                result = _extract_polygon_from_dwg(dwg_path, office_lat, office_lon)
                code   = 400 if "error" in result else 200
                self._send_json(code, result)
            except Exception as e:
                self._send_json(500, {"error": str(e)})

        elif parsed.path == "/api/train-model":
            try:
                result = _profit_train_inline()
                self._send_json(200, result)
            except Exception as e:
                self._send_json(500, {"ok": False, "error": str(e)})

        elif parsed.path == "/api/predict":
            try:
                result = _profit_predict(params)
                code   = 400 if "error" in result else 200
                self._send_json(code, result)
            except Exception as e:
                self._send_json(500, {"error": str(e)})

        else:
            self.send_response(404); self.end_headers()


def qs_flat(qs: dict) -> dict:
    return {k: v[0] if v else "" for k, v in qs.items()}


# ═══════════════════════════════════════════════════════════════════════════
def main():
    port   = 7654
    server = HTTPServer(("127.0.0.1", port), Handler)
    url    = f"http://localhost:{port}"
    print(f"\n  DWG->SHP Pipeline v3  |  {url}\n  Ctrl+C to stop.\n")
    threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:    server.serve_forever()
    except KeyboardInterrupt: print("\n  Stopped.")

if __name__ == "__main__":
    from multiprocessing import freeze_support
    freeze_support()
    main()
