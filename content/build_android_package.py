"""Build the shared reading package from seed JSON files and Wikidata extracts."""

import json
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"
SEEDS = [
    CONTENT / "seed" / "early-modern.json",
    CONTENT / "seed" / "early-modern-skeleton.json",
    CONTENT / "seed" / "long-span.json",
    CONTENT / "seed" / "wikidata.json",
    CONTENT / "seed" / "modern-china.json",
]
OUTPUT = CONTENT / "dist" / "knowledge-package.json"
GAZETTEERS = [CONTENT / "gazetteer.json", CONTENT / "gazetteer_wikidata.json"]
PLACE_POLITIES = CONTENT / "place_polities.json"
PEOPLE = CONTENT / "wikidata_people.json"
MANIFEST = CONTENT / "media_manifest.json"
SUMMARIES = CONTENT / "wiki_summaries.json"
BRIEFS = CONTENT / "wiki_briefs.json"
# Batches that stay in the admin until reviewed, never shipped unreviewed in the app.
HELD_BATCHES = {"china-1949-plus"}
SUMMARY_LIMIT = 300
SECTION_LIMIT = 500
BRIEF_LIMIT = 1600


def read(path: Path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


MANIFEST_DATA = read(MANIFEST, {})
SUMMARY_DATA = read(SUMMARIES, {})
BRIEF_DATA = read(BRIEFS, {})


def media(title: str | None) -> tuple[str, str]:
    entry = MANIFEST_DATA.get(title or "")
    if not entry:
        return "", ""
    author = entry["author"] or "佚名"
    return entry["file"], f"{author} · {entry['license']} · 维基共享资源"


def summary(article: str | None, fallback: str | None) -> str:
    text = SUMMARY_DATA.get(article or "") or fallback or ""
    return text[:SUMMARY_LIMIT]


def article_title(url: str) -> str:
    if "/wiki/" not in url:
        return ""
    return urllib.parse.unquote(url.rsplit("/wiki/", 1)[-1]).replace("_", " ")


def clip(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    cut = text[:limit]
    for mark in ("。", "！", "？"):
        index = cut.rfind(mark)
        if index >= int(limit * 0.6):
            return cut[: index + 1]
    return cut.rstrip("，,；;、 ")


def format_sections(title: str, limit: int) -> str:
    entry = BRIEF_DATA.get(title) or {}
    parts = []
    used = 0
    for section in entry.get("sections") or []:
        heading = str(section.get("heading") or "").strip()
        body = str(section.get("text") or "").strip()
        if not heading or not body or used >= limit:
            continue
        body = clip(body, min(SECTION_LIMIT, limit - used))
        if len(body) < 40:
            continue
        parts.append(f"§{heading}\n{body}")
        used += len(body)
    return "\n\n".join(parts)


def claim_brief(text: str, citation: dict) -> str:
    """Encyclopedia extract for the detail page. The one-sentence fact stays in text."""
    title = article_title(citation.get("stable_url") or "")
    if not title:
        return ""
    lead = (SUMMARY_DATA.get(title) or "").strip()
    if lead and lead in text:
        lead = ""
    parts = []
    room = BRIEF_LIMIT
    if lead:
        piece = clip(lead, min(SUMMARY_LIMIT, room))
        if len(piece) >= 40:
            parts.append(piece)
            room -= len(piece)
    sections = format_sections(title, room)
    if sections:
        parts.append(sections)
    return "\n\n".join(parts)


def load_regions() -> list[dict]:
    places = [place for path in GAZETTEERS for place in read(path, {"places": []})["places"]]
    spans = read(PLACE_POLITIES, {})
    ids = {place["slug"]: index for index, place in enumerate(places, start=1)}
    regions = []
    for place in places:
        parent = place["parent"]
        image, credit = media(place.get("image"))
        regions.append(
            {
                "id": ids[place["slug"]],
                "slug": place["slug"],
                "name": place["name"],
                "sort_order": place["sort_order"],
                "parent_id": ids[parent] if parent else None,
                "latitude": place["latitude"],
                "longitude": place["longitude"],
                "level": place["level"],
                "polity_spans": spans.get(place["slug"], []),
                "description": summary(place.get("zhwiki"), place.get("description")),
                "image": image,
                "image_credit": credit,
            }
        )
    return regions


TOPICS = [
    {"slug": "politics", "name": "政治"},
    {"slug": "economy", "name": "经济"},
    {"slug": "society", "name": "社会"},
    {"slug": "technology", "name": "科技"},
    {"slug": "culture", "name": "文化"},
    {"slug": "birth", "name": "出生"},
    {"slug": "war", "name": "战争"},
    {"slug": "battle", "name": "战役"},
    {"slug": "siege", "name": "围城"},
    {"slug": "treaty", "name": "条约"},
    {"slug": "revolution", "name": "革命"},
    {"slug": "rebellion", "name": "叛乱"},
    {"slug": "coup", "name": "政变"},
    {"slug": "coronation", "name": "加冕"},
    {"slug": "assassination", "name": "刺杀"},
    {"slug": "earthquake", "name": "地震"},
    {"slug": "epidemic", "name": "疫病"},
    {"slug": "disaster", "name": "灾害"},
    {"slug": "expedition", "name": "远征"},
    {"slug": "discovery", "name": "发现"},
    {"slug": "invention", "name": "发明"},
    {"slug": "work", "name": "著作"},
    {"slug": "election", "name": "选举"},
    {"slug": "conference", "name": "会议"},
    {"slug": "founding", "name": "建国"},
]
REGIONS = load_regions()
REGION_IDS = {region["slug"]: region["id"] for region in REGIONS}


def main() -> None:
    claims_in = []
    for path in SEEDS:
        claims_in.extend(read(path, {"claims": []})["claims"])
    held = sum(1 for claim in claims_in if claim.get("review_batch") in HELD_BATCHES)
    claims_in = [claim for claim in claims_in if claim.get("review_batch") not in HELD_BATCHES]
    claims_in.sort(key=lambda claim: (claim["start_year"], claim["end_year"], claim["text"]))

    people: dict[str, dict] = {}
    for entry in read(PEOPLE, {"people": []})["people"]:
        image, credit = media(entry.get("image"))
        people[entry["qid"]] = {
            "id": len(people) + 1,
            "name": entry["name"],
            "birth_year": entry["birth_year"],
            "death_year": entry["death_year"],
            "description": summary(entry.get("zhwiki"), entry["description"]),
            "region_id": REGION_IDS.get(entry["place_slug"]),
            "image": image,
            "image_credit": credit,
            "wikidata": entry["qid"],
            "role": entry.get("role") or "other",
        }

    def person_id(name: str, qid: str | None) -> int:
        key = qid or f"name:{name}"
        if key not in people:
            people[key] = {"id": len(people) + 1, "name": name}
        return people[key]["id"]

    events = {}
    snapshots = {}
    claims = []
    citation_id = 1

    for claim in claims_in:
        slugs = [slug for slug in claim["region_slugs"] if slug in REGION_IDS]
        if not slugs:
            continue
        citation = claim["citation"]
        qids = claim.get("person_qids") or []
        names = claim.get("people") or []
        person_ids = [person_id(name, qids[i] if i < len(qids) else None) for i, name in enumerate(names)]
        event_key = (claim["event_title"], claim["start_year"], claim["end_year"])
        if event_key not in events:
            events[event_key] = {
                "id": len(events) + 1,
                "title": claim["event_title"],
                "time_label": claim["display_text"],
                "person_ids": person_ids,
            }
        snapshot_key = (
            claim["snapshot_label"],
            claim["region_slugs"][0],
            claim["snapshot_dimension"],
            claim["start_year"],
            claim["end_year"],
        )
        if snapshot_key not in snapshots:
            snapshots[snapshot_key] = {
                "id": len(snapshots) + 1,
                "label": claim["snapshot_label"],
                "time_label": claim["display_text"],
            }
        claims.append(
            {
                "id": len(claims) + 1,
                "text": claim["text"],
                "brief": claim_brief(claim["text"], citation),
                "certainty": claim["certainty"],
                "time_label": claim["display_text"],
                "start_year": claim["start_year"],
                "end_year": claim["end_year"],
                "region_ids": [REGION_IDS[slug] for slug in slugs],
                "topic_slugs": claim["topic_slugs"],
                "event_id": events[event_key]["id"],
                "snapshot_id": snapshots[snapshot_key]["id"],
                "citations": [
                    {
                        "id": citation_id,
                        "source_title": "维基数据" if citation["edition_label"] == "维基数据" else "维基百科",
                        "edition_label": citation["edition_label"],
                        "locator": citation["locator"],
                        "quotation": "",
                        "stable_url": citation["stable_url"],
                    }
                ],
            }
        )
        citation_id += 1

    package = {
        "version": 0,
        "full": True,
        "removed_claim_ids": [],
        "regions": REGIONS,
        "topics": TOPICS,
        "events": list(events.values()),
        "snapshots": list(snapshots.values()),
        "people": list(people.values()),
        "polities": [],
        "claims": claims,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(package, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    size = OUTPUT.stat().st_size / 1e6
    with_brief = sum(1 for claim in claims if claim["brief"])
    print(
        f"wrote {len(claims)} claims, {len(people)} people, {len(REGIONS)} places "
        f"({held} held for review, {with_brief} with a brief), {size:.1f} MB"
    )


if __name__ == "__main__":
    main()
