"""Check that packaged claims, places, and borders use the same years and places.

Prints counts. Exits with an error if a claim points at a missing place, a year
range is reversed, or the modern country layer splits Taiwan, Hong Kong, or Macao
out of China. Polity-span gaps and duplicate titles are reported and left in place:
Wikidata rows stay unverified.
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "content" / "dist" / "knowledge-package.json"
COUNTRIES = ROOT / "content" / "dist" / "countries.geojson"
HISTORICAL_END = 1911
SEPARATED = {"台湾", "臺灣", "香港", "澳门", "澳門"}


def overlaps(start: int, end: int, span_from: int, span_to: int) -> bool:
    return start <= span_to and end >= span_from


def descendants(root: int, children: dict[int, list[int]]) -> set[int]:
    seen = set()
    stack = [root]
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        stack.extend(children.get(current, []))
    return seen


def main() -> None:
    package = json.loads(PACKAGE.read_text(encoding="utf-8"))
    regions = {region["id"]: region for region in package["regions"]}
    children: dict[int, list[int]] = defaultdict(list)
    for region in regions.values():
        parent = region.get("parent_id")
        if parent is not None:
            children[parent].append(region["id"])
    events = {event["id"]: event for event in package["events"]}
    china = next(region for region in regions.values() if region["slug"] == "china")
    china_ids = descendants(china["id"], children)

    missing_place = 0
    reversed_years = 0
    china_1912_1949 = 0
    polity_gap = 0
    titles: dict[tuple[str, int], int] = defaultdict(int)

    for claim in package["claims"]:
        start, end = claim["start_year"], claim["end_year"]
        if start > end:
            reversed_years += 1
        ids = claim["region_ids"]
        if not ids or any(region_id not in regions for region_id in ids):
            missing_place += 1
            continue
        if any(region_id in china_ids for region_id in ids) and overlaps(start, end, 1912, 1949):
            china_1912_1949 += 1
        if start <= HISTORICAL_END:
            covered = False
            for region_id in ids:
                for span in regions[region_id].get("polity_spans") or []:
                    if overlaps(start, min(end, HISTORICAL_END), span[0], span[1]):
                        covered = True
                        break
                if covered:
                    break
            if not covered:
                polity_gap += 1
        title = events.get(claim["event_id"], {}).get("title") or ""
        if title:
            titles[(title, start)] += 1

    countries = json.loads(COUNTRIES.read_text(encoding="utf-8"))
    names = [feature["properties"].get("n") or "" for feature in countries["features"]]
    has_china = names.count("中国") == 1
    separated = sorted({name for name in names if name in SEPARATED})
    duplicate_groups = sum(1 for count in titles.values() if count > 1)

    print(f"claims {len(package['claims'])}")
    print(f"missing_place {missing_place}")
    print(f"reversed_years {reversed_years}")
    print(f"china_1912_1949 {china_1912_1949}")
    print(f"polity_gap_before_1912 {polity_gap}")
    print(f"duplicate_title_year {duplicate_groups}")
    print(f"country_china {has_china} separated {separated or 'none'}")

    if missing_place or reversed_years or not has_china or separated:
        sys.exit(1)


if __name__ == "__main__":
    main()
