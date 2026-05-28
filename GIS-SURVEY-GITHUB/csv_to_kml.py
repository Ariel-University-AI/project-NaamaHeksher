"""
CSV → KML Converter
ממיר פלט של dwg_to_csv.py לקובץ KML (Google Earth / QGIS).
המרת קואורדינטות: IG05/12 (EPSG:6991) → WGS84 (EPSG:4326)

שימוש:
    python csv_to_kml.py input.csv
    python csv_to_kml.py input.csv --output output.kml

דרישות:
    pip install pyproj
"""

import csv
import sys
import argparse
from pathlib import Path

try:
    from pyproj import Transformer
except ImportError:
    print("❌ חסרה ספריית pyproj. התקן אותה עם:")
    print("   pip install pyproj")
    sys.exit(1)

# IG05/12 (Israel TM Grid) → WGS84
transformer = Transformer.from_crs("EPSG:6991", "EPSG:4326", always_xy=True)


def group_polygons(rows):
    """מקבץ שורות CSV לרשימת פוליגונים לפי VertexIndex."""
    polygons = []
    current = []

    for row in rows:
        idx = int(row["VertexIndex"])
        if idx == 0 and current:
            polygons.append(current)
            current = []
        current.append(row)

    if current:
        polygons.append(current)

    return polygons


def to_wgs84(x, y):
    """ממיר קואורדינטות IG05/12 ל-WGS84 (lon, lat)."""
    lon, lat = transformer.transform(x, y)
    return lon, lat


_KML_STANDARD = frozenset({
    'Layer', 'EntityType', 'GeometryType', 'VertexIndex', 'VertexCount',
    'X', 'Y', 'Z', 'CoordinateSystem', 'IsClosed', 'Length_m', 'Area_sqm',
    'Radius', 'Bulge', 'Rotation', 'Color', 'Notes', 'SourceFile',
})


def polygon_to_kml(polygon, index):
    """מייצר בלוק KML עבור פוליגון בודד."""
    row0 = polygon[0]
    layer = row0["Layer"]
    area = row0.get("Area_sqm", "")
    length = row0.get("Length_m", "")
    notes = row0.get("Notes", "")

    desc_lines = []
    if area:
        desc_lines.append(f"שטח: {area} מ״ר")
    if length:
        desc_lines.append(f"היקף: {length} מ׳")
    if notes:
        desc_lines.append(notes)
    for k, v in row0.items():
        if k not in _KML_STANDARD and v not in (None, ""):
            desc_lines.append(f"{k}: {v}")
    description = "<![CDATA[" + "<br/>".join(desc_lines) + "]]>" if desc_lines else ""

    coords_parts = []
    for row in polygon:
        x, y, z = float(row["X"]), float(row["Y"]), float(row["Z"])
        lon, lat = to_wgs84(x, y)
        coords_parts.append(f"{lon:.8f},{lat:.8f},{z:.3f}")

    # סגירת הפוליגון (חזרה לנקודה הראשונה)
    first = polygon[0]
    lon0, lat0 = to_wgs84(float(first["X"]), float(first["Y"]))
    coords_parts.append(f"{lon0:.8f},{lat0:.8f},{float(first['Z']):.3f}")

    coords_str = "\n                    ".join(coords_parts)

    return f"""    <Placemark>
      <name>{layer} — פוליגון {index + 1}</name>
      <description>{description}</description>
      <Polygon>
        <extrude>0</extrude>
        <altitudeMode>clampToGround</altitudeMode>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>
                    {coords_str}
            </coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </Placemark>"""


def csv_to_kml(csv_path, kml_path=None):
    csv_path = Path(csv_path)
    kml_path = Path(kml_path) if kml_path else csv_path.with_suffix(".kml")

    print(f"📖 קורא: {csv_path.name}")

    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        print("❌ הקובץ ריק")
        return

    # סינון פוליגונים בלבד (למקרה שה-CSV מכיל ישויות מעורבות)
    polygon_rows = [r for r in rows if r.get("GeometryType") == "Polygon"]
    print(f"   שורות: {len(rows)} | שורות פוליגון: {len(polygon_rows)}")

    if not polygon_rows:
        print("❌ לא נמצאו פוליגונים ב-CSV")
        return

    polygons = group_polygons(polygon_rows)
    print(f"   פוליגונים: {len(polygons)}")

    # בניית KML
    placemarks = "\n".join(polygon_to_kml(p, i) for i, p in enumerate(polygons))

    layer_name = polygon_rows[0]["Layer"]
    kml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>{layer_name}</name>
    <Style id="polygonStyle">
      <LineStyle>
        <color>ff0000ff</color>
        <width>2</width>
      </LineStyle>
      <PolyStyle>
        <color>330000ff</color>
      </PolyStyle>
    </Style>
{placemarks}
  </Document>
</kml>"""

    with open(kml_path, "w", encoding="utf-8") as f:
        f.write(kml_content)

    print(f"✅ KML נוצר: {kml_path}")


def main():
    parser = argparse.ArgumentParser(description="ממיר CSV (פלט dwg_to_csv) ל-KML")
    parser.add_argument("input", help="נתיב לקובץ CSV")
    parser.add_argument("--output", "-o", help="נתיב לקובץ KML (ברירת מחדל: אותו שם)")
    args = parser.parse_args()

    csv_to_kml(args.input, args.output)


if __name__ == "__main__":
    main()
