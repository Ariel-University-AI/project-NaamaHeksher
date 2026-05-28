"""
DWG/DXF -> SHP Batch Converter
================================
Reads DXF files (or DWG via ODA File Converter), extracts polygons from a
specified layer, and writes a Shapefile per map.

Supports:
  - LWPOLYLINE (closed)
  - POLYLINE (closed, 2D/3D)
  - HATCH (boundary paths)
  - SPLINE (approximated as polyline)
  - INSERT (block references, flattened)

Performance:
  - Parallel processing via ProcessPoolExecutor
  - Worker count auto-tuned to CPU cores
  - Progress bar via tqdm (optional)

Usage:
  python dwg_to_shp.py --input_dir C:/maps --output_dir C:/shp --layer PARCEL
  python dwg_to_shp.py --input_dir C:/maps --output_dir C:/shp --layer PARCEL --workers 8 --ext dxf
  python dwg_to_shp.py --input_dir C:/maps --output_dir C:/shp --layer PARCEL --oda_path "C:/ODA/OdaFileConverter.exe"
"""

import os
import sys
import argparse
import logging
import time
import subprocess
import tempfile
import shutil
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import List, Tuple, Optional

import ezdxf
from ezdxf.math import Matrix44
import shapefile

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False


# ---------------------------------------------------------------------------
# Geometry extraction helpers
# ---------------------------------------------------------------------------

def _close_ring(pts: list) -> list:
    """Ensure first == last point (closed ring)."""
    if not pts:
        return pts
    if pts[0] != pts[-1]:
        pts.append(pts[0])
    return pts


def _lwpolyline_to_polygons(entity, transform: Optional[Matrix44]) -> List[list]:
    """Extract polygon rings from LWPOLYLINE."""
    if not entity.closed:
        return []
    pts = [(p[0], p[1]) for p in entity.get_points()]
    if transform:
        pts = [(transform.transform((x, y, 0))[0], transform.transform((x, y, 0))[1]) for x, y in pts]
    pts = _close_ring(pts)
    return [pts] if len(pts) >= 4 else []


def _polyline_to_polygons(entity, transform: Optional[Matrix44]) -> List[list]:
    """Extract polygon rings from 2D/3D POLYLINE."""
    if not entity.is_closed:
        return []
    pts = [(v.dxf.location.x, v.dxf.location.y) for v in entity.vertices]
    if transform:
        pts = [(transform.transform((x, y, 0))[0], transform.transform((x, y, 0))[1]) for x, y in pts]
    pts = _close_ring(pts)
    return [pts] if len(pts) >= 4 else []


def _hatch_to_polygons(entity, transform: Optional[Matrix44]) -> List[list]:
    """Extract polygon rings from HATCH boundary paths."""
    results = []
    for path in entity.paths:
        pts = []
        if hasattr(path, "vertices"):
            # PolylinePath
            pts = [(v[0], v[1]) for v in path.vertices]
        elif hasattr(path, "edges"):
            # EdgePath — approximate by sampling LINE/ARC edges
            for edge in path.edges:
                etype = edge.EDGE_TYPE
                if etype == "LineEdge":
                    pts.append((edge.start.x, edge.start.y))
                elif etype == "ArcEdge":
                    import math
                    cx, cy, r = edge.center.x, edge.center.y, edge.radius
                    a0 = math.radians(edge.start_angle)
                    a1 = math.radians(edge.end_angle)
                    if a1 < a0:
                        a1 += 2 * math.pi
                    steps = max(8, int((a1 - a0) / math.radians(5)))
                    for i in range(steps + 1):
                        a = a0 + (a1 - a0) * i / steps
                        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
                elif etype == "SplineEdge":
                    if edge.control_points:
                        pts.extend([(p[0], p[1]) for p in edge.control_points])
        if transform:
            pts = [(transform.transform((x, y, 0))[0], transform.transform((x, y, 0))[1]) for x, y in pts]
        pts = _close_ring(pts)
        if len(pts) >= 4:
            results.append(pts)
    return results


def _spline_to_polygons(entity, transform: Optional[Matrix44]) -> List[list]:
    """Approximate SPLINE as polygon (closed only)."""
    if not entity.closed:
        return []
    try:
        pts = [(p[0], p[1]) for p in entity.approximate(segments=50)]
    except Exception:
        if entity.control_points:
            pts = [(p[0], p[1]) for p in entity.control_points]
        else:
            return []
    if transform:
        pts = [(transform.transform((x, y, 0))[0], transform.transform((x, y, 0))[1]) for x, y in pts]
    pts = _close_ring(pts)
    return [pts] if len(pts) >= 4 else []


def extract_polygons_from_layer(
    dxf_path: str,
    layer_name: str,
    case_sensitive: bool = False,
) -> List[list]:
    """
    Open a DXF file and return all polygon rings from the specified layer.
    Returns a list of rings, each ring is a list of (x, y) tuples.
    """
    try:
        doc = ezdxf.readfile(dxf_path)
    except Exception as e:
        raise RuntimeError(f"Cannot read DXF: {e}")

    msp = doc.modelspace()
    rings = []

    def layer_match(name: str) -> bool:
        if case_sensitive:
            return name == layer_name
        return name.upper() == layer_name.upper()

    def process_entity(entity, transform=None):
        etype = entity.dxftype()
        layer = entity.dxf.get("layer", "")
        if layer_match(layer):
            if etype == "LWPOLYLINE":
                rings.extend(_lwpolyline_to_polygons(entity, transform))
            elif etype == "POLYLINE":
                rings.extend(_polyline_to_polygons(entity, transform))
            elif etype == "HATCH":
                rings.extend(_hatch_to_polygons(entity, transform))
            elif etype == "SPLINE":
                rings.extend(_spline_to_polygons(entity, transform))

    for entity in msp:
        if entity.dxftype() == "INSERT":
            # Explode block references
            try:
                t = entity.matrix44()
                block = doc.blocks.get(entity.dxf.name)
                if block:
                    for sub in block:
                        process_entity(sub, transform=t)
            except Exception:
                pass
        else:
            process_entity(entity)

    return rings


# ---------------------------------------------------------------------------
# SHP writer
# ---------------------------------------------------------------------------

def write_shp(rings: List[list], out_path: str, source_name: str = "") -> int:
    """
    Write a Shapefile (POLYGON) from a list of rings.
    Returns number of features written.
    """
    w = shapefile.Writer(out_path, shapefile.POLYGON)
    w.field("ID", "N", 10)
    w.field("SOURCE", "C", 100)

    for i, ring in enumerate(rings, 1):
        # pyshp expects list of rings; first = outer, rest = holes
        w.poly([ring])
        w.record(i, source_name)

    w.close()

    # Write minimal .prj (placeholder — update with your CRS if needed)
    prj_path = out_path + ".prj"
    # ITM (Israel Transverse Mercator) WKT
    itm_wkt = (
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
    with open(prj_path, "w") as f:
        f.write(itm_wkt)

    return len(rings)


# ---------------------------------------------------------------------------
# Single-file worker (runs in subprocess for parallel execution)
# ---------------------------------------------------------------------------

def _process_one(args: Tuple) -> dict:
    """
    Worker function: process a single DXF/DWG file.
    Returns a result dict with keys: file, status, count, error, elapsed.
    """
    dxf_path, out_dir, layer_name, oda_exe, keep_dxf = args
    t0 = time.time()
    stem = Path(dxf_path).stem
    result = {"file": stem, "status": "ok", "count": 0, "error": "", "elapsed": 0.0}

    tmp_dxf = None
    work_path = dxf_path

    try:
        # --- DWG -> DXF conversion via ODA File Converter ---
        if dxf_path.lower().endswith(".dwg"):
            if not oda_exe or not Path(oda_exe).exists():
                raise RuntimeError(
                    "DWG file detected but ODA File Converter not found. "
                    "Use --oda_path or convert to DXF first."
                )
            tmp_dir = tempfile.mkdtemp()
            tmp_dxf = os.path.join(tmp_dir, stem + ".dxf")
            _convert_dwg_to_dxf(dxf_path, tmp_dir, oda_exe)
            work_path = tmp_dxf

        # --- Extract polygons ---
        rings = extract_polygons_from_layer(work_path, layer_name)

        if not rings:
            result["status"] = "empty"
            result["error"] = f"No closed polygons found on layer '{layer_name}'"
        else:
            out_path = os.path.join(out_dir, stem)
            n = write_shp(rings, out_path, stem)
            result["count"] = n

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
    finally:
        if tmp_dxf and not keep_dxf:
            shutil.rmtree(os.path.dirname(tmp_dxf), ignore_errors=True)
        result["elapsed"] = time.time() - t0

    return result


def _convert_dwg_to_dxf(dwg_path: str, out_dir: str, oda_exe: str):
    """
    Convert a single DWG to DXF using ODA File Converter (CLI).
    ODA syntax: OdaFileConverter <input_dir> <output_dir> <version> <type> <recurse> <audit> [filter]
    """
    in_dir = str(Path(dwg_path).parent)
    filename = Path(dwg_path).name
    cmd = [
        oda_exe,
        in_dir,
        out_dir,
        "ACAD2018",   # output DXF version
        "DXF",        # output format
        "0",          # no recursion
        "1",          # audit
        filename,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise RuntimeError(f"ODA conversion failed: {r.stderr.strip()}")
    expected = os.path.join(out_dir, Path(dwg_path).stem + ".dxf")
    if not os.path.exists(expected):
        raise RuntimeError("ODA ran but output DXF not found.")


# ---------------------------------------------------------------------------
# Main batch runner
# ---------------------------------------------------------------------------

def run_batch(
    input_dir: str,
    output_dir: str,
    layer_name: str,
    ext: str = "dxf",
    workers: int = None,
    oda_path: str = None,
    keep_dxf: bool = False,
    recursive: bool = True,
    exclude_rz: bool = True,
    json_progress: bool = False,
):
    """
    json_progress: if True, emit one JSON line per file to stdout for GUI consumption.
    """
    import json as _json

    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # --- Collect files (recursive or flat) ---
    glob_pattern = f"**/*.{ext.lower()}" if recursive else f"*.{ext.lower()}"
    files = sorted(input_dir.glob(glob_pattern))

    # --- Filter out files containing "RZ" in the stem (case-insensitive) ---
    if exclude_rz:
        before = len(files)
        files = [f for f in files if "RZ" not in f.stem.upper()]
        skipped_rz = before - len(files)
    else:
        skipped_rz = 0

    if not files:
        msg = f"No .{ext} files found in {input_dir}"
        if json_progress:
            print(_json.dumps({"type": "error", "message": msg}), flush=True)
        else:
            log.warning(msg)
        return

    total = len(files)

    if json_progress:
        print(_json.dumps({"type": "start", "total": total, "skipped_rz": skipped_rz}), flush=True)
    else:
        log.info(f"Found {total} files ({skipped_rz} skipped - contain RZ). Layer='{layer_name}' | Workers={workers or 'auto'}")

    tasks = [(str(f), str(output_dir), layer_name, oda_path, keep_dxf) for f in files]
    n_workers = workers or min(os.cpu_count() or 4, 16)

    ok = empty = errors = 0
    total_polys = 0
    t_start = time.time()

    with ProcessPoolExecutor(max_workers=n_workers) as pool:
        futures = {pool.submit(_process_one, t): t for t in tasks}

        if HAS_TQDM and not json_progress:
            bar = tqdm(total=total, unit="file", ncols=80)

        for future in as_completed(futures):
            res = future.result()
            processed = ok + empty + errors + 1

            if res["status"] == "ok":
                ok += 1
                total_polys += res["count"]
            elif res["status"] == "empty":
                empty += 1
            else:
                errors += 1

            if json_progress:
                print(_json.dumps({
                    "type": "progress",
                    "file": res["file"],
                    "status": res["status"],
                    "count": res["count"],
                    "error": res["error"],
                    "elapsed": round(res["elapsed"], 3),
                    "processed": processed,
                    "total": total,
                    "ok": ok,
                    "empty": empty,
                    "errors": errors,
                    "total_polys": total_polys,
                }), flush=True)
            else:
                if res["status"] == "ok":
                    log.debug(f"[OK]    {res['file']} | {res['count']} polygons | {res['elapsed']:.2f}s")
                elif res["status"] == "empty":
                    log.warning(f"[EMPTY] {res['file']} | {res['error']}")
                else:
                    log.error(f"[ERROR] {res['file']} | {res['error']}")

                if HAS_TQDM:
                    bar.update(1)
                    bar.set_postfix(ok=ok, empty=empty, err=errors)

        if HAS_TQDM and not json_progress:
            bar.close()

    elapsed = time.time() - t_start
    rate = total / elapsed if elapsed > 0 else 0

    if json_progress:
        print(_json.dumps({
            "type": "done",
            "total": total,
            "ok": ok,
            "empty": empty,
            "errors": errors,
            "total_polys": total_polys,
            "elapsed": round(elapsed, 2),
            "rate": round(rate, 1),
            "skipped_rz": skipped_rz,
            "output_dir": str(output_dir),
        }), flush=True)
    else:
        print("\n" + "=" * 60)
        print(f"  DONE: {total} files in {elapsed:.1f}s ({rate:.1f} files/sec)")
        print(f"  OK:     {ok} files -> {total_polys} polygons exported")
        print(f"  EMPTY:  {empty} (layer not found or no closed polygons)")
        print(f"  ERRORS: {errors}")
        if skipped_rz:
            print(f"  SKIPPED (RZ): {skipped_rz}")
        print(f"  Output: {output_dir}")
        print("=" * 60)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Batch DWG/DXF -> SHP polygon extractor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--input_dir",  required=True, help="Folder containing DXF/DWG files")
    parser.add_argument("--output_dir", required=True, help="Folder for output SHP files")
    parser.add_argument("--layer",      required=True, help="Layer name to extract polygons from")
    parser.add_argument("--ext",        default="dxf",  help="File extension to search (dxf or dwg). Default: dxf")
    parser.add_argument("--workers",    type=int, default=None, help="Parallel workers (default: CPU count)")
    parser.add_argument("--oda_path",   default=None,  help="Path to OdaFileConverter.exe (required for DWG)")
    parser.add_argument("--keep_dxf",       action="store_true", help="Keep temporary DXF files after DWG conversion")
    parser.add_argument("--verbose",         action="store_true", help="Show per-file debug output")
    parser.add_argument("--no_recursive",    action="store_true", help="Do NOT scan sub-folders (default: recursive)")
    parser.add_argument("--include_rz",      action="store_true", help="Include files containing RZ in name (default: excluded)")
    parser.add_argument("--json_progress",   action="store_true", help="Emit JSON lines to stdout (for GUI)")

    args = parser.parse_args()

    if args.verbose:
        log.setLevel(logging.DEBUG)

    run_batch(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        layer_name=args.layer,
        ext=args.ext,
        workers=args.workers,
        oda_path=args.oda_path,
        keep_dxf=args.keep_dxf,
        recursive=not args.no_recursive,
        exclude_rz=not args.include_rz,
        json_progress=args.json_progress,
    )


if __name__ == "__main__":
    from multiprocessing import freeze_support
    freeze_support()
    main()
