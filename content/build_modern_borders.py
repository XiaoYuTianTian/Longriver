"""Build 1912+ country outlines from Natural Earth 50m admin-0 (public domain).

CShapes and similar historical country datasets are GPL / non-commercial, so they
cannot go in this app. Natural Earth is public domain and already supplies land.geojson.

Taiwan / Hong Kong / Macao polygons are merged into China so the offline layer does
not draw them as separate countries.

Requires: pip install pyshp shapely
Input: content/raw/ne_50m_admin_0_countries/ne_50m_admin_0_countries.shp
  from https://www.naturalearthdata.com/downloads/50m-cultural-vectors/
"""

import json
import zlib
from collections import defaultdict
from pathlib import Path

import shapefile
from shapely.geometry import mapping, shape
from shapely.ops import unary_union
from shapely.validation import make_valid

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "content" / "raw" / "ne_50m_admin_0_countries" / "ne_50m_admin_0_countries"
ASSETS = ROOT / "content" / "dist"
CHINA_PARTS = {"CHN", "TWN", "HKG", "MAC"}
PALETTE_SIZE = 8
MIN_AREA = 0.04
TOLERANCE = 0.04


def rounded(geometry: dict) -> dict:
    def walk(value):
        if isinstance(value, (list, tuple)) and value and isinstance(value[0], (int, float)):
            return [round(value[0], 2), round(value[1], 2)]
        return [walk(item) for item in value]

    return {"type": geometry["type"], "coordinates": walk(geometry["coordinates"])}


def polygonal(geometry):
    geometry = make_valid(geometry)
    if geometry.geom_type in ("Polygon", "MultiPolygon"):
        return geometry
    if geometry.geom_type == "GeometryCollection":
        parts = [part for part in geometry.geoms if part.geom_type in ("Polygon", "MultiPolygon")]
        if parts:
            return unary_union(parts)
    return None


def simplify(geometry):
    geometry = polygonal(geometry)
    if geometry is None or geometry.is_empty:
        return None
    geometry = geometry.simplify(TOLERANCE, preserve_topology=True)
    geometry = polygonal(geometry)
    if geometry is None or geometry.is_empty or geometry.area < MIN_AREA:
        return None
    return geometry


def main() -> None:
    reader = shapefile.Reader(str(RAW))
    fields = [field[0] for field in reader.fields[1:]]
    grouped: dict[str, dict] = defaultdict(lambda: {"geoms": [], "zh": ""})
    for item in reader.shapeRecords():
        rec = {name: item.record[i] for i, name in enumerate(fields)}
        code = (rec.get("ADM0_A3") or "").strip()
        if not code or code == "-99":
            continue
        if code in CHINA_PARTS:
            code = "CHN"
        geometry = simplify(shape(item.shape.__geo_interface__))
        if geometry is None:
            continue
        grouped[code]["geoms"].append(geometry)
        zh = (rec.get("NAME_ZH") or "").strip()
        if code != "CHN" and zh and not grouped[code]["zh"]:
            grouped[code]["zh"] = zh
    grouped["CHN"]["zh"] = "中国"

    features = []
    labels = []
    for code, entry in grouped.items():
        geometry = simplify(unary_union(entry["geoms"]))
        if geometry is None:
            continue
        color = zlib.crc32(code.encode("utf-8")) % PALETTE_SIZE
        features.append(
            {
                "type": "Feature",
                "properties": {"c": color, "n": entry["zh"]},
                "geometry": rounded(mapping(geometry)),
            }
        )
        zh = entry["zh"]
        if zh and any("\u4e00" <= ch <= "\u9fff" for ch in zh) and geometry.area >= 8:
            point = geometry.representative_point()
            labels.append(
                {
                    "n": zh,
                    "lon": round(point.x, 2),
                    "lat": round(point.y, 2),
                    "a": round(geometry.area * 12000),
                }
            )
    dest = ASSETS / "countries.geojson"
    dest.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    (ASSETS / "country-labels.json").write_text(
        json.dumps(labels, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(f"countries: {len(features)} polygons, {len(labels)} labels, {dest.stat().st_size / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
