"""
╔══════════════════════════════════════════════════════════════╗
║          DWG/DXF to CSV Converter — משרד מדידות             ║
║          מערכת קואורדינטות: IG05/12 (EPSG:6991)             ║
║                                                              ║
║  חילוץ: נקודות, קווים, פוליליינים, פוליגונים, עיגולים,      ║
║         קשתות, ספליינים, בלוקים, טקסטים ועוד                 ║
╚══════════════════════════════════════════════════════════════╝

שימוש:
    python dwg_to_csv.py input.dwg                    # המרת קובץ בודד
    python dwg_to_csv.py input.dxf                    # עובד גם עם DXF ישירות
    python dwg_to_csv.py input.dwg --output result.csv
    python dwg_to_csv.py input.dwg --layers "גבולות,נקודות"  # שכבות ספציפיות
    python dwg_to_csv.py folder/                      # המרת כל הקבצים בתיקייה

דרישות:
    pip install ezdxf
    + ODA File Converter (להמרת DWG → DXF) — https://www.opendesign.com/guestfiles/oda_file_converter
"""

import os
import sys
import csv
import math
import glob
import shutil
import argparse
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime

try:
    import ezdxf
    from ezdxf.math import Vec3
except ImportError:
    print("❌ חסרה ספריית ezdxf. התקן אותה עם:")
    print("   pip install ezdxf")
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════
# הגדרות מערכת קואורדינטות
# ═══════════════════════════════════════════════════════════════

COORDINATE_SYSTEM = "IG05/12"
EPSG_CODE = 6991  # IG05/12 Israel TM Grid
DECIMAL_PRECISION = 3  # דיוק של 3 ספרות אחרי הנקודה (מילימטר)

# מספר נקודות לדגימה על קשתות ועיגולים
ARC_SEGMENTS = 36
CIRCLE_SEGMENTS = 72
SPLINE_SEGMENTS = 50


# ═══════════════════════════════════════════════════════════════
# מחלקת ה-Converter הראשית
# ═══════════════════════════════════════════════════════════════

class DwgToCsvConverter:
    """ממיר קבצי DWG/DXF ל-CSV עם חילוץ כל סוגי הגאומטריות."""

    def __init__(self, oda_path=None, precision=DECIMAL_PRECISION):
        """
        Args:
            oda_path: נתיב ל-ODA File Converter (אופציונלי — מנסה למצוא אוטומטית)
            precision: מספר ספרות אחרי הנקודה
        """
        self.precision = precision
        self.oda_path = oda_path or self._find_oda_converter()
        self.stats = {
            "points": 0,
            "lines": 0,
            "polylines": 0,
            "polygons": 0,
            "circles": 0,
            "arcs": 0,
            "splines": 0,
            "texts": 0,
            "blocks": 0,
            "other": 0,
        }

    def _find_oda_converter(self):
        """מחפש את ODA File Converter במיקומים נפוצים."""
        common_paths = [
            # Windows
            r"C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe",
            r"C:\Program Files (x86)\ODA\ODAFileConverter\ODAFileConverter.exe",
            r"C:\Program Files\ODA\ODAFileConverter 26.3.0\ODAFileConverter.exe",
            r"C:\Program Files\ODA\ODAFileConverter 25.12.0\ODAFileConverter.exe",
            # Linux
            "/usr/bin/ODAFileConverter",
            "/usr/local/bin/ODAFileConverter",
        ]

        # חיפוש בנתיבי ברירת מחדל
        for path in common_paths:
            if os.path.isfile(path):
                return path

        # חיפוש ב-PATH
        oda_name = "ODAFileConverter.exe" if os.name == "nt" else "ODAFileConverter"
        oda_in_path = shutil.which(oda_name)
        if oda_in_path:
            return oda_in_path

        # חיפוש דינמי בתיקיות Program Files (Windows)
        if os.name == "nt":
            for prog_dir in [r"C:\Program Files\ODA", r"C:\Program Files (x86)\ODA"]:
                if os.path.isdir(prog_dir):
                    for folder in os.listdir(prog_dir):
                        candidate = os.path.join(prog_dir, folder, "ODAFileConverter.exe")
                        if os.path.isfile(candidate):
                            return candidate

        return None

    def convert_dwg_to_dxf(self, dwg_path):
        """
        ממיר קובץ DWG ל-DXF באמצעות ODA File Converter.

        Returns:
            נתיב לקובץ ה-DXF שנוצר, או None אם נכשל
        """
        if not self.oda_path:
            print("❌ ODA File Converter לא נמצא!")
            print("   הורד מ: https://www.opendesign.com/guestfiles/oda_file_converter")
            print("   או ציין נתיב עם --oda-path")
            return None

        dwg_path = os.path.abspath(dwg_path)
        input_dir = os.path.dirname(dwg_path)
        filename = os.path.basename(dwg_path)

        # יצירת תיקייה זמנית לפלט
        temp_dir = tempfile.mkdtemp(prefix="dwg2csv_")

        # העתקת הקובץ לתיקייה זמנית של קלט (ODA דורש תיקיות)
        temp_input_dir = tempfile.mkdtemp(prefix="dwg2csv_in_")
        temp_input_file = os.path.join(temp_input_dir, filename)
        shutil.copy2(dwg_path, temp_input_file)

        print(f"🔄 ממיר DWG → DXF: {filename}")

        try:
            result = subprocess.run(
                [
                    self.oda_path,
                    temp_input_dir,   # תיקיית מקור
                    temp_dir,         # תיקיית יעד
                    "ACAD2018",       # גרסת DXF (2018 — תאימות טובה)
                    "DXF",            # פורמט יעד
                    "0",              # לא רקורסיבי
                    "1",              # Audit — תיקון שגיאות
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )

            # חיפוש קובץ ה-DXF שנוצר
            dxf_name = Path(filename).stem + ".dxf"
            dxf_path = os.path.join(temp_dir, dxf_name)

            if os.path.isfile(dxf_path):
                print(f"✅ המרה הצליחה: {dxf_name}")
                return dxf_path
            else:
                # אולי השם שונה — מחפשים כל DXF בתיקייה
                dxf_files = glob.glob(os.path.join(temp_dir, "*.dxf"))
                if dxf_files:
                    print(f"✅ המרה הצליחה: {os.path.basename(dxf_files[0])}")
                    return dxf_files[0]

                print("❌ המרת DWG נכשלה — לא נוצר קובץ DXF")
                if result.stderr:
                    print(f"   שגיאה: {result.stderr}")
                return None

        except subprocess.TimeoutExpired:
            print("❌ המרה נכשלה — timeout")
            return None
        except Exception as e:
            print(f"❌ שגיאה בהמרה: {e}")
            return None
        finally:
            # ניקוי תיקיית הקלט הזמנית
            shutil.rmtree(temp_input_dir, ignore_errors=True)

    def parse_dxf(self, dxf_path, layer_filter=None):
        """
        מפרסר קובץ DXF ומחלץ את כל הגאומטריות.

        Args:
            dxf_path: נתיב לקובץ DXF
            layer_filter: רשימת שכבות לסינון (None = הכל)

        Returns:
            רשימת שורות CSV (dicts)
        """
        print(f"📖 קורא קובץ: {os.path.basename(dxf_path)}")

        try:
            doc = ezdxf.readfile(dxf_path)
        except Exception as e:
            print(f"❌ שגיאה בקריאת DXF: {e}")
            return []

        msp = doc.modelspace()
        rows = []

        # מידע על הקובץ
        print(f"   גרסת DXF: {doc.dxfversion}")
        print(f"   שכבות: {len(doc.layers)}")

        if layer_filter:
            layer_set = set(layer_filter)
            print(f"   סינון שכבות: {', '.join(layer_filter)}")

        # עיבוד כל הישויות
        entity_count = 0
        for entity in msp:
            entity_count += 1

            # סינון לפי שכבה
            if layer_filter:
                if entity.dxf.layer not in layer_set:
                    continue

            try:
                entity_rows = self._process_entity(entity)
                rows.extend(entity_rows)
            except Exception as e:
                print(f"   ⚠️ שגיאה בעיבוד ישות {entity.dxftype()} "
                      f"בשכבה '{entity.dxf.layer}': {e}")

        print(f"   ישויות שנקראו: {entity_count}")
        print(f"   שורות CSV: {len(rows)}")

        return rows

    def _process_entity(self, entity):
        """מעבד ישות בודדת ומחזיר רשימת שורות CSV."""
        etype = entity.dxftype()
        layer = entity.dxf.layer
        color = self._get_color(entity)

        if etype == "POINT":
            return self._process_point(entity, layer, color)
        elif etype == "LINE":
            return self._process_line(entity, layer, color)
        elif etype == "LWPOLYLINE":
            return self._process_lwpolyline(entity, layer, color)
        elif etype == "POLYLINE":
            return self._process_polyline(entity, layer, color)
        elif etype == "CIRCLE":
            return self._process_circle(entity, layer, color)
        elif etype == "ARC":
            return self._process_arc(entity, layer, color)
        elif etype == "ELLIPSE":
            return self._process_ellipse(entity, layer, color)
        elif etype == "SPLINE":
            return self._process_spline(entity, layer, color)
        elif etype == "INSERT":
            return self._process_insert(entity, layer, color)
        elif etype in ("TEXT", "MTEXT"):
            return self._process_text(entity, layer, color)
        elif etype == "3DFACE":
            return self._process_3dface(entity, layer, color)
        elif etype == "SOLID":
            return self._process_solid(entity, layer, color)
        elif etype == "HATCH":
            return self._process_hatch(entity, layer, color)
        else:
            self.stats["other"] += 1
            return []

    # ─────────────────────────────────────────────────────────
    # עיבוד סוגי ישויות
    # ─────────────────────────────────────────────────────────

    def _process_point(self, entity, layer, color):
        """POINT — נקודה בודדת."""
        self.stats["points"] += 1
        loc = entity.dxf.location
        return [self._make_row(
            layer=layer,
            entity_type="POINT",
            geometry_type="Point",
            vertex_index=0,
            vertex_count=1,
            x=loc.x, y=loc.y, z=loc.z,
            color=color,
        )]

    def _process_line(self, entity, layer, color):
        """LINE — קו ישר (2 נקודות)."""
        self.stats["lines"] += 1
        start = entity.dxf.start
        end = entity.dxf.end
        length = math.dist((start.x, start.y), (end.x, end.y))

        return [
            self._make_row(
                layer=layer,
                entity_type="LINE",
                geometry_type="Line",
                vertex_index=0,
                vertex_count=2,
                x=start.x, y=start.y, z=start.z,
                color=color,
                length=length,
            ),
            self._make_row(
                layer=layer,
                entity_type="LINE",
                geometry_type="Line",
                vertex_index=1,
                vertex_count=2,
                x=end.x, y=end.y, z=end.z,
                color=color,
                length=length,
            ),
        ]

    def _process_lwpolyline(self, entity, layer, color):
        """LWPOLYLINE — פוליליין 2D (קל)."""
        is_closed = entity.closed
        points = list(entity.get_points(format="xyseb"))
        count = len(points)

        if is_closed and count >= 3:
            geom_type = "Polygon"
            self.stats["polygons"] += 1
        else:
            geom_type = "Polyline"
            self.stats["polylines"] += 1

        # חישוב אורך כולל
        total_length = 0
        for i in range(1, count):
            total_length += math.dist(
                (points[i - 1][0], points[i - 1][1]),
                (points[i][0], points[i][1])
            )
        if is_closed and count > 1:
            total_length += math.dist(
                (points[-1][0], points[-1][1]),
                (points[0][0], points[0][1])
            )

        # חישוב שטח (אם פוליגון סגור)
        area = None
        if is_closed and count >= 3:
            area = self._calculate_polygon_area(
                [(p[0], p[1]) for p in points]
            )

        rows = []
        # קבלת גובה מ-elevation אם קיים
        elevation = getattr(entity.dxf, "elevation", 0.0) or 0.0

        for i, pt in enumerate(points):
            x, y = pt[0], pt[1]
            bulge = pt[4] if len(pt) > 4 else 0.0

            rows.append(self._make_row(
                layer=layer,
                entity_type="LWPOLYLINE",
                geometry_type=geom_type,
                vertex_index=i,
                vertex_count=count,
                x=x, y=y, z=elevation,
                color=color,
                is_closed=is_closed,
                length=total_length,
                area=area,
                bulge=bulge,
            ))

        return rows

    def _process_polyline(self, entity, layer, color):
        """POLYLINE — פוליליין 2D/3D (מלא)."""
        is_closed = entity.is_closed
        vertices = list(entity.vertices)
        points = [(v.dxf.location.x, v.dxf.location.y, v.dxf.location.z)
                   for v in vertices if v.is_poly_face_mesh_vertex is False]

        if not points:
            # fallback
            points = [(v.dxf.location.x, v.dxf.location.y, v.dxf.location.z)
                       for v in vertices]

        count = len(points)

        if is_closed and count >= 3:
            geom_type = "Polygon"
            self.stats["polygons"] += 1
        else:
            geom_type = "Polyline"
            self.stats["polylines"] += 1

        # חישוב אורך
        total_length = 0
        for i in range(1, count):
            total_length += math.dist(points[i - 1][:2], points[i][:2])
        if is_closed and count > 1:
            total_length += math.dist(points[-1][:2], points[0][:2])

        # חישוב שטח
        area = None
        if is_closed and count >= 3:
            area = self._calculate_polygon_area([(p[0], p[1]) for p in points])

        rows = []
        for i, pt in enumerate(points):
            rows.append(self._make_row(
                layer=layer,
                entity_type="POLYLINE",
                geometry_type=geom_type,
                vertex_index=i,
                vertex_count=count,
                x=pt[0], y=pt[1], z=pt[2],
                color=color,
                is_closed=is_closed,
                length=total_length,
                area=area,
            ))

        return rows

    def _process_circle(self, entity, layer, color):
        """CIRCLE — עיגול → דגימה לנקודות."""
        self.stats["circles"] += 1
        center = entity.dxf.center
        radius = entity.dxf.radius
        circumference = 2 * math.pi * radius
        area = math.pi * radius ** 2

        rows = []
        # נקודת מרכז
        rows.append(self._make_row(
            layer=layer,
            entity_type="CIRCLE",
            geometry_type="Circle_Center",
            vertex_index=0,
            vertex_count=CIRCLE_SEGMENTS + 1,
            x=center.x, y=center.y, z=center.z,
            color=color,
            radius=radius,
            length=circumference,
            area=area,
        ))

        # נקודות על ההיקף
        for i in range(CIRCLE_SEGMENTS):
            angle = (2 * math.pi * i) / CIRCLE_SEGMENTS
            px = center.x + radius * math.cos(angle)
            py = center.y + radius * math.sin(angle)

            rows.append(self._make_row(
                layer=layer,
                entity_type="CIRCLE",
                geometry_type="Circle_Vertex",
                vertex_index=i + 1,
                vertex_count=CIRCLE_SEGMENTS + 1,
                x=px, y=py, z=center.z,
                color=color,
                radius=radius,
                is_closed=True,
            ))

        return rows

    def _process_arc(self, entity, layer, color):
        """ARC — קשת → דגימה לנקודות."""
        self.stats["arcs"] += 1
        center = entity.dxf.center
        radius = entity.dxf.radius
        start_angle = math.radians(entity.dxf.start_angle)
        end_angle = math.radians(entity.dxf.end_angle)

        # חישוב זווית כוללת (בכיוון השעון)
        if end_angle < start_angle:
            total_angle = (2 * math.pi) - start_angle + end_angle
        else:
            total_angle = end_angle - start_angle

        arc_length = radius * total_angle

        rows = []
        for i in range(ARC_SEGMENTS + 1):
            t = i / ARC_SEGMENTS
            angle = start_angle + t * total_angle
            px = center.x + radius * math.cos(angle)
            py = center.y + radius * math.sin(angle)

            rows.append(self._make_row(
                layer=layer,
                entity_type="ARC",
                geometry_type="Arc",
                vertex_index=i,
                vertex_count=ARC_SEGMENTS + 1,
                x=px, y=py, z=center.z,
                color=color,
                radius=radius,
                length=arc_length,
            ))

        return rows

    def _process_ellipse(self, entity, layer, color):
        """ELLIPSE — אליפסה → דגימה לנקודות."""
        self.stats["circles"] += 1
        center = entity.dxf.center
        major_axis = entity.dxf.major_axis
        ratio = entity.dxf.ratio
        start_param = entity.dxf.start_param
        end_param = entity.dxf.end_param

        a = math.sqrt(major_axis.x ** 2 + major_axis.y ** 2)  # חצי ציר גדול
        b = a * ratio  # חצי ציר קטן
        rotation = math.atan2(major_axis.y, major_axis.x)

        is_full = abs(end_param - start_param - 2 * math.pi) < 0.01
        segments = CIRCLE_SEGMENTS if is_full else ARC_SEGMENTS

        rows = []
        for i in range(segments + 1):
            t = start_param + (end_param - start_param) * i / segments
            # נקודה על האליפסה (לפני סיבוב)
            ex = a * math.cos(t)
            ey = b * math.sin(t)
            # סיבוב
            px = center.x + ex * math.cos(rotation) - ey * math.sin(rotation)
            py = center.y + ex * math.sin(rotation) + ey * math.cos(rotation)

            rows.append(self._make_row(
                layer=layer,
                entity_type="ELLIPSE",
                geometry_type="Ellipse",
                vertex_index=i,
                vertex_count=segments + 1,
                x=px, y=py, z=center.z,
                color=color,
                is_closed=is_full,
            ))

        return rows

    def _process_spline(self, entity, layer, color):
        """SPLINE — עקומה → דגימה לנקודות."""
        self.stats["splines"] += 1

        try:
            # ezdxf יכול לפרק ספליין לנקודות
            points = list(entity.flattening(distance=0.1))
        except Exception:
            # fallback — שימוש בנקודות בקרה
            points = list(entity.control_points)

        count = len(points)
        is_closed = entity.closed

        if is_closed and count >= 3:
            geom_type = "Polygon"
        else:
            geom_type = "Spline"

        # חישוב אורך
        total_length = 0
        for i in range(1, count):
            total_length += math.dist(
                (points[i - 1].x, points[i - 1].y),
                (points[i].x, points[i].y),
            )

        rows = []
        for i, pt in enumerate(points):
            rows.append(self._make_row(
                layer=layer,
                entity_type="SPLINE",
                geometry_type=geom_type,
                vertex_index=i,
                vertex_count=count,
                x=pt.x, y=pt.y, z=pt.z,
                color=color,
                is_closed=is_closed,
                length=total_length,
            ))

        return rows

    def _process_insert(self, entity, layer, color):
        """INSERT — הכנסת בלוק → חילוץ נקודת הכנסה + מאפיינים."""
        self.stats["blocks"] += 1
        insert_pt = entity.dxf.insert
        block_name = entity.dxf.name
        rotation = getattr(entity.dxf, "rotation", 0.0) or 0.0
        x_scale = getattr(entity.dxf, "xscale", 1.0) or 1.0
        y_scale = getattr(entity.dxf, "yscale", 1.0) or 1.0

        # חילוץ מאפיינים (Attributes) של הבלוק
        attributes = {}
        if hasattr(entity, "attribs"):
            for attrib in entity.attribs:
                attributes[attrib.dxf.tag] = attrib.dxf.text

        notes = f"Block: {block_name}"
        if attributes:
            attrs_str = "; ".join(f"{k}={v}" for k, v in attributes.items())
            notes += f" | Attrs: {attrs_str}"

        return [self._make_row(
            layer=layer,
            entity_type="INSERT",
            geometry_type="Block",
            vertex_index=0,
            vertex_count=1,
            x=insert_pt.x, y=insert_pt.y, z=insert_pt.z,
            color=color,
            rotation=rotation,
            notes=notes,
        )]

    def _process_text(self, entity, layer, color):
        """TEXT / MTEXT — טקסט → חילוץ מיקום + תוכן."""
        self.stats["texts"] += 1
        etype = entity.dxftype()

        if etype == "TEXT":
            insert_pt = entity.dxf.insert
            text_content = entity.dxf.text
            height = entity.dxf.height
            rotation = getattr(entity.dxf, "rotation", 0.0) or 0.0
        else:  # MTEXT
            insert_pt = entity.dxf.insert
            text_content = entity.text  # MTEXT plain text
            height = entity.dxf.char_height
            rotation = getattr(entity.dxf, "rotation", 0.0) or 0.0

        # ניקוי טקסט (הסרת תווים מיוחדים)
        text_content = text_content.replace("\n", " ").replace(",", ";")

        return [self._make_row(
            layer=layer,
            entity_type=etype,
            geometry_type="Text",
            vertex_index=0,
            vertex_count=1,
            x=insert_pt.x, y=insert_pt.y, z=insert_pt.z,
            color=color,
            rotation=rotation,
            notes=f"Text: {text_content} | Height: {height}",
        )]

    def _process_3dface(self, entity, layer, color):
        """3DFACE — משטח תלת-ממדי (3-4 נקודות)."""
        self.stats["polygons"] += 1
        points = [entity.dxf.vtx0, entity.dxf.vtx1,
                  entity.dxf.vtx2, entity.dxf.vtx3]

        # אם vtx3 == vtx2 זה משולש
        if (points[3].x == points[2].x and
                points[3].y == points[2].y and
                points[3].z == points[2].z):
            points = points[:3]

        count = len(points)
        area = self._calculate_polygon_area([(p.x, p.y) for p in points])

        rows = []
        for i, pt in enumerate(points):
            rows.append(self._make_row(
                layer=layer,
                entity_type="3DFACE",
                geometry_type="Polygon",
                vertex_index=i,
                vertex_count=count,
                x=pt.x, y=pt.y, z=pt.z,
                color=color,
                is_closed=True,
                area=area,
            ))

        return rows

    def _process_solid(self, entity, layer, color):
        """SOLID — משטח 2D."""
        self.stats["polygons"] += 1
        points = [entity.dxf.vtx0, entity.dxf.vtx1,
                  entity.dxf.vtx2]
        if hasattr(entity.dxf, "vtx3"):
            points.append(entity.dxf.vtx3)

        count = len(points)
        rows = []
        for i, pt in enumerate(points):
            rows.append(self._make_row(
                layer=layer,
                entity_type="SOLID",
                geometry_type="Polygon",
                vertex_index=i,
                vertex_count=count,
                x=pt.x, y=pt.y, z=pt.z,
                color=color,
                is_closed=True,
            ))

        return rows

    def _process_hatch(self, entity, layer, color):
        """HATCH — תבנית מילוי → חילוץ גבולות."""
        self.stats["polygons"] += 1
        rows = []

        try:
            for path_idx, path in enumerate(entity.paths):
                if hasattr(path, "vertices"):
                    # PolylinePath
                    vertices = path.vertices
                    count = len(vertices)
                    area = self._calculate_polygon_area(
                        [(v.x, v.y) if hasattr(v, "x") else (v[0], v[1])
                         for v in vertices]
                    )

                    for i, v in enumerate(vertices):
                        vx = v.x if hasattr(v, "x") else v[0]
                        vy = v.y if hasattr(v, "y") else v[1]
                        rows.append(self._make_row(
                            layer=layer,
                            entity_type="HATCH",
                            geometry_type="Polygon",
                            vertex_index=i,
                            vertex_count=count,
                            x=vx, y=vy, z=0,
                            color=color,
                            is_closed=True,
                            area=area,
                            notes=f"Hatch boundary {path_idx}",
                        ))
        except Exception:
            pass  # Hatch יכול להיות מורכב — מדלגים על שגיאות

        return rows

    # ─────────────────────────────────────────────────────────
    # פונקציות עזר
    # ─────────────────────────────────────────────────────────

    def _make_row(self, layer, entity_type, geometry_type,
                  vertex_index, vertex_count, x, y, z,
                  color=None, is_closed=None, length=None,
                  area=None, radius=None, bulge=None,
                  rotation=None, notes=None):
        """יוצר שורת CSV מפורמטת."""
        p = self.precision
        return {
            "Layer": layer,
            "EntityType": entity_type,
            "GeometryType": geometry_type,
            "VertexIndex": vertex_index,
            "VertexCount": vertex_count,
            "X": round(x, p),
            "Y": round(y, p),
            "Z": round(z, p),
            "CoordinateSystem": COORDINATE_SYSTEM,
            "IsClosed": "Yes" if is_closed else ("No" if is_closed is False else ""),
            "Length_m": round(length, p) if length is not None else "",
            "Area_sqm": round(area, 2) if area is not None else "",
            "Radius": round(radius, p) if radius is not None else "",
            "Bulge": round(bulge, 6) if bulge is not None else "",
            "Rotation": round(rotation, 2) if rotation is not None else "",
            "Color": color or "",
            "Notes": notes or "",
        }

    def _get_color(self, entity):
        """מחזיר צבע ישות כ-ACI index."""
        try:
            color = entity.dxf.color
            if color == 256:  # BYLAYER
                return "BYLAYER"
            elif color == 0:  # BYBLOCK
                return "BYBLOCK"
            else:
                return str(color)
        except Exception:
            return ""

    @staticmethod
    def _calculate_polygon_area(points):
        """
        חישוב שטח פוליגון בשיטת Shoelace.
        Args:
            points: רשימת (x, y) tuples
        Returns:
            שטח (ערך מוחלט) ביחידות מרובעות
        """
        n = len(points)
        if n < 3:
            return 0.0

        area = 0.0
        for i in range(n):
            j = (i + 1) % n
            area += points[i][0] * points[j][1]
            area -= points[j][0] * points[i][1]

        return abs(area) / 2.0

    # ─────────────────────────────────────────────────────────
    # כתיבת CSV
    # ─────────────────────────────────────────────────────────

    def write_csv(self, rows, output_path):
        """כותב את השורות לקובץ CSV."""
        if not rows:
            print("⚠️ אין נתונים לכתיבה")
            return

        fieldnames = [
            "Layer", "EntityType", "GeometryType",
            "VertexIndex", "VertexCount",
            "X", "Y", "Z",
            "CoordinateSystem",
            "IsClosed", "Length_m", "Area_sqm",
            "Radius", "Bulge", "Rotation",
            "Color", "Notes",
        ]

        with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        print(f"\n✅ קובץ CSV נוצר בהצלחה: {output_path}")
        print(f"   שורות: {len(rows):,}")
        print(f"   גודל: {os.path.getsize(output_path) / 1024:.1f} KB")

    # ─────────────────────────────────────────────────────────
    # הרצה ראשית
    # ─────────────────────────────────────────────────────────

    def convert(self, input_path, output_path=None, layer_filter=None):
        """
        ממיר קובץ DWG/DXF ל-CSV.

        Args:
            input_path: נתיב לקובץ DWG/DXF או תיקייה
            output_path: נתיב לקובץ CSV (אופציונלי)
            layer_filter: רשימת שכבות לסינון (אופציונלי)

        Returns:
            נתיב לקובץ CSV שנוצר, או None אם נכשל
        """
        input_path = os.path.abspath(input_path)

        # בדיקה אם זה תיקייה
        if os.path.isdir(input_path):
            return self._convert_directory(input_path, layer_filter)

        # בדיקה אם הקובץ קיים
        if not os.path.isfile(input_path):
            print(f"❌ קובץ לא נמצא: {input_path}")
            return None

        ext = Path(input_path).suffix.lower()

        # קביעת נתיב פלט
        if not output_path:
            output_path = str(Path(input_path).with_suffix(".csv"))

        print("\n" + "═" * 60)
        print(f"  🔄 DWG/DXF → CSV Converter")
        print(f"  📁 קלט: {os.path.basename(input_path)}")
        print(f"  📊 פלט: {os.path.basename(output_path)}")
        print(f"  🌍 מערכת קואורדינטות: {COORDINATE_SYSTEM} (EPSG:{EPSG_CODE})")
        print("═" * 60)

        dxf_path = None
        temp_dxf = False

        if ext == ".dwg":
            # שלב 1: המרה DWG → DXF
            dxf_path = self.convert_dwg_to_dxf(input_path)
            if not dxf_path:
                return None
            temp_dxf = True
        elif ext == ".dxf":
            dxf_path = input_path
        else:
            print(f"❌ פורמט לא נתמך: {ext}")
            print("   פורמטים נתמכים: .dwg, .dxf")
            return None

        # שלב 2: פרסור DXF
        rows = self.parse_dxf(dxf_path, layer_filter)

        # שלב 3: כתיבת CSV
        if rows:
            self.write_csv(rows, output_path)
            self._print_stats()
        else:
            print("⚠️ לא נמצאו ישויות גאוגרפיות בקובץ")

        # ניקוי קבצים זמניים
        if temp_dxf and dxf_path:
            temp_dir = os.path.dirname(dxf_path)
            shutil.rmtree(temp_dir, ignore_errors=True)

        return output_path if rows else None

    def _convert_directory(self, dir_path, layer_filter=None):
        """ממיר את כל קבצי DWG/DXF בתיקייה."""
        files = (
            glob.glob(os.path.join(dir_path, "*.dwg")) +
            glob.glob(os.path.join(dir_path, "*.DWG")) +
            glob.glob(os.path.join(dir_path, "*.dxf")) +
            glob.glob(os.path.join(dir_path, "*.DXF"))
        )

        if not files:
            print(f"❌ לא נמצאו קבצי DWG/DXF בתיקייה: {dir_path}")
            return None

        print(f"\n📂 נמצאו {len(files)} קבצים בתיקייה")

        output_dir = os.path.join(dir_path, "csv_output")
        os.makedirs(output_dir, exist_ok=True)

        success = 0
        for filepath in files:
            output_path = os.path.join(
                output_dir,
                Path(filepath).stem + ".csv"
            )
            result = self.convert(filepath, output_path, layer_filter)
            if result:
                success += 1
            # איפוס סטטיסטיקות
            self.stats = {k: 0 for k in self.stats}

        print(f"\n{'═' * 60}")
        print(f"  ✅ הושלמו {success}/{len(files)} קבצים")
        print(f"  📂 קבצי CSV בתיקייה: {output_dir}")
        print(f"{'═' * 60}")

        return output_dir

    def _print_stats(self):
        """מדפיס סטטיסטיקות חילוץ."""
        print("\n📊 סיכום חילוץ:")
        print("   ┌──────────────────────────────┐")
        if self.stats["points"]:
            print(f"   │  📍 נקודות:       {self.stats['points']:>8,} │")
        if self.stats["lines"]:
            print(f"   │  📏 קווים:         {self.stats['lines']:>8,} │")
        if self.stats["polylines"]:
            print(f"   │  〰️ פוליליינים:    {self.stats['polylines']:>8,} │")
        if self.stats["polygons"]:
            print(f"   │  ⬡ פוליגונים:     {self.stats['polygons']:>8,} │")
        if self.stats["circles"]:
            print(f"   │  ⭕ עיגולים:       {self.stats['circles']:>8,} │")
        if self.stats["arcs"]:
            print(f"   │  ◗ קשתות:         {self.stats['arcs']:>8,} │")
        if self.stats["splines"]:
            print(f"   │  🌀 ספליינים:      {self.stats['splines']:>8,} │")
        if self.stats["texts"]:
            print(f"   │  🔤 טקסטים:        {self.stats['texts']:>8,} │")
        if self.stats["blocks"]:
            print(f"   │  🧱 בלוקים:        {self.stats['blocks']:>8,} │")
        if self.stats["other"]:
            print(f"   │  ❓ אחר:           {self.stats['other']:>8,} │")
        total = sum(self.stats.values())
        print(f"   │{'─' * 30}│")
        print(f"   │  סה\"כ ישויות:     {total:>8,} │")
        print("   └──────────────────────────────┘")


# ═══════════════════════════════════════════════════════════════
# CLI — ממשק שורת הפקודה
# ═══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="ממיר קבצי DWG/DXF ל-CSV — משרד מדידות",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
דוגמאות שימוש:
  python dwg_to_csv.py drawing.dwg
  python dwg_to_csv.py survey.dxf --output result.csv
  python dwg_to_csv.py drawing.dwg --layers "גבולות" "נקודות מדידה"
  python dwg_to_csv.py ./surveys/          # כל הקבצים בתיקייה
        """,
    )

    parser.add_argument(
        "input",
        help="נתיב לקובץ DWG/DXF או תיקייה",
    )
    parser.add_argument(
        "--output", "-o",
        help="נתיב לקובץ CSV (ברירת מחדל: אותו שם עם סיומת .csv)",
    )
    parser.add_argument(
        "--layers", "-l",
        nargs="+",
        help="שכבות ספציפיות לחילוץ (ברירת מחדל: הכל)",
    )
    parser.add_argument(
        "--oda-path",
        help="נתיב ל-ODA File Converter",
    )
    parser.add_argument(
        "--precision", "-p",
        type=int,
        default=DECIMAL_PRECISION,
        help=f"מספר ספרות אחרי הנקודה (ברירת מחדל: {DECIMAL_PRECISION})",
    )

    args = parser.parse_args()

    converter = DwgToCsvConverter(
        oda_path=args.oda_path,
        precision=args.precision,
    )

    result = converter.convert(
        input_path=args.input,
        output_path=args.output,
        layer_filter=args.layers,
    )

    if result:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
