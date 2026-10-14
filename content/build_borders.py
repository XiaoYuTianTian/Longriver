"""Build offline border assets from the Cliopatria dataset (CC BY 4.0).

Inputs live in content/raw/ and are not committed:
  cliopatria.geojson  from https://doi.org/10.5281/zenodo.13363121
  ne_50m_land.geojson from Natural Earth (public domain)
"""

import json
import zlib
from collections import defaultdict
from pathlib import Path

from shapely import STRtree
from shapely.geometry import Point, mapping, shape
from shapely.validation import make_valid

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "content" / "raw"
ASSETS = ROOT / "android" / "app" / "src" / "main" / "assets"
START_YEAR = -3000
END_YEAR = 1911
TOLERANCE = 0.06
MIN_AREA_KM2 = 800
BUCKET_YEARS = 100
PALETTE_SIZE = 8


def cliopatria_path() -> Path:
    matches = sorted(RAW.rglob("cliopatria.geojson"))
    if not matches:
        raise SystemExit("content/raw/ 下没有 cliopatria.geojson，请先下载并解压 Cliopatria。")
    return matches[0]


def rounded(geometry: dict) -> dict:
    def walk(value):
        if isinstance(value, (list, tuple)) and value and isinstance(value[0], (int, float)):
            return [round(value[0], 2), round(value[1], 2)]
        return [walk(item) for item in value]

    return {"type": geometry["type"], "coordinates": walk(geometry["coordinates"])}


def polygonal(geometry):
    if geometry.geom_type in ("Polygon", "MultiPolygon"):
        return geometry
    if geometry.geom_type == "GeometryCollection":
        parts = [part for part in geometry.geoms if part.geom_type in ("Polygon", "MultiPolygon")]
        if parts:
            from shapely.ops import unary_union

            return unary_union(parts)
    return None


def simplify(geometry):
    geometry = make_valid(geometry)
    geometry = polygonal(geometry)
    if geometry is None or geometry.is_empty:
        return None
    geometry = geometry.simplify(TOLERANCE, preserve_topology=True)
    geometry = polygonal(make_valid(geometry)) if not geometry.is_valid else geometry
    if geometry is None or geometry.is_empty:
        return None
    return geometry


def palette_index(name: str) -> int:
    return zlib.crc32(name.encode("utf-8")) % PALETTE_SIZE


def build_land() -> None:
    source = RAW / "ne_50m_land.geojson"
    if not source.exists():
        raise SystemExit("content/raw/ 下没有 ne_50m_land.geojson。")
    features = []
    for feature in json.loads(source.read_text(encoding="utf-8"))["features"]:
        geometry = shape(feature["geometry"]).simplify(0.03, preserve_topology=True)
        if geometry.is_empty or geometry.area < 0.05:
            continue
        features.append({"type": "Feature", "properties": {}, "geometry": rounded(mapping(geometry))})
    out = {"type": "FeatureCollection", "features": features}
    (ASSETS / "land.geojson").write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
    print(f"land: {len(features)} polygons")


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    zh_table = json.loads((ROOT / "content" / "polity_names_zh.json").read_text(encoding="utf-8"))["names"]
    raw = json.loads(cliopatria_path().read_text(encoding="utf-8"))["features"]

    polity_ids = {}
    polities = {}
    rows = []
    for feature in raw:
        props = feature["properties"]
        name = props["Name"]
        if props.get("Type") != "POLITY" or name.startswith("("):
            continue
        start = max(props["FromYear"], START_YEAR)
        end = min(props["ToYear"], END_YEAR)
        if start > end or props["Area"] < MIN_AREA_KM2 or feature["geometry"] is None:
            continue
        geometry = simplify(shape(feature["geometry"]))
        if geometry is None:
            continue
        pid = polity_ids.setdefault(name, len(polity_ids) + 1)
        zh, capital = zh_table.get(name, ["", ""])
        if not any("\u4e00" <= ch <= "\u9fff" for ch in zh):
            zh = ""
        entry = polities.setdefault(
            pid,
            {
                "id": pid,
                "name": name,
                "zh": zh,
                "capital": capital,
                "wikipedia": props.get("Wikipedia") or "",
                "from": start,
                "to": end,
                "labels": [],
            },
        )
        entry["from"] = min(entry["from"], start)
        entry["to"] = max(entry["to"], end)
        label = geometry.representative_point()
        entry["labels"].append([start, end, round(label.x, 2), round(label.y, 2), round(props["Area"])])
        rows.append((start, end, pid, palette_index(name), geometry))

    buckets = defaultdict(list)
    for start, end, pid, color, geometry in rows:
        first = (start - START_YEAR) // BUCKET_YEARS
        last = (end - START_YEAR) // BUCKET_YEARS
        feature = {
            "type": "Feature",
            "properties": {"p": pid, "f": start, "t": end, "c": color},
            "geometry": rounded(mapping(geometry)),
        }
        for bucket in range(first, last + 1):
            buckets[bucket].append(feature)

    border_dir = ASSETS / "borders"
    border_dir.mkdir(exist_ok=True)
    for old in border_dir.glob("*.geojson"):
        old.unlink()
    total = 0
    for bucket, features in sorted(buckets.items()):
        text = json.dumps({"type": "FeatureCollection", "features": features}, separators=(",", ":"))
        (border_dir / f"{bucket}.geojson").write_text(text, encoding="utf-8")
        total += len(text.encode("utf-8"))

    index = {
        "attribution": "疆域数据：Cliopatria（Seshat Global History Databank），CC BY 4.0，已裁剪与简化。",
        "start": START_YEAR,
        "bucket_years": BUCKET_YEARS,
        "polities": sorted(polities.values(), key=lambda item: item["id"]),
    }
    (ASSETS / "polities.json").write_text(
        json.dumps(index, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )

    places = []
    for name in ("gazetteer.json", "gazetteer_wikidata.json"):
        path = ROOT / "content" / name
        if path.exists():
            places.extend(json.loads(path.read_text(encoding="utf-8"))["places"])
    tree = STRtree([geometry for *_, geometry in rows])
    place_polities = {}
    for place in places:
        point = Point(place["longitude"], place["latitude"])
        spans = [
            [rows[i][0], rows[i][1], rows[i][2]]
            for i in tree.query(point, predicate="within")
        ]
        place_polities[place["slug"]] = sorted(spans)
    (ROOT / "content" / "place_polities.json").write_text(
        json.dumps(place_polities, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )

    translated = sum(1 for item in polities.values() if item["zh"] != item["name"])
    print(f"borders: {len(rows)} rows, {len(polities)} polities ({translated} 有中文名), {len(buckets)} buckets, {total / 1e6:.1f} MB")
    build_land()


if __name__ == "__main__":
    main()
