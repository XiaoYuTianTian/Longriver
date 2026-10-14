"""Extract candidate people, events and places from Wikidata (CC0).

Output is unreviewed: every claim is marked "unverified" and must pass human
review in the admin before it is published.

    python content/build_wikidata.py            # uses cached responses
    python content/build_wikidata.py --refresh  # re-query the endpoint
"""

import argparse
import hashlib
import json
import math
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from opencc import OpenCC

T2S = OpenCC("t2s")
ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"
CACHE = CONTENT / "raw" / "wikidata"
GAZETTEER = CONTENT / "gazetteer.json"
OUT_PLACES = CONTENT / "gazetteer_wikidata.json"
OUT_PEOPLE = CONTENT / "wikidata_people.json"
OUT_SEED = CONTENT / "seed" / "wikidata.json"

ENDPOINT = "https://qlever.dev/api/wikidata"
OFFICIAL = "https://query.wikidata.org/sparql"
USER_AGENT = "ChangheContentBuild/0.3 (historical atlas app; content pipeline)"
PREFIX = """PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX wikibase: <http://wikiba.se/ontology#>
PREFIX schema: <http://schema.org/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
"""

PEOPLE_LIMIT = 3000
EVENT_LIMIT = 3000
LATEST_BIRTH = 1935
LATEST_EVENT = 2000
SENSITIVE_BATCH = "china-1949-plus"
STATE_CLASSES = {
    "Q6256", "Q3024240", "Q7275", "Q417175", "Q48349", "Q1250464", "Q3624078", "Q859563", "Q1790360",
    "Q12759805", "Q28171280", "Q50068795", "Q164950",
}
ZH_LANGS = ["zh-hans", "zh-cn", "zh-sg", "zh", "zh-my", "zh-hant", "zh-tw", "zh-hk"]
REUSE_KM = 25

EVENT_CLASSES = {
    "Q178561": "politics",  # battle
    "Q198": "politics",  # war
    "Q131569": "politics",  # treaty
    "Q10931": "politics",  # revolution
    "Q124734": "politics",  # rebellion
    "Q188055": "politics",  # siege
    "Q45382": "politics",  # coup d'etat
    "Q7944": "society",  # earthquake
    "Q44512": "society",  # epidemic
    "Q2401485": "technology",  # expedition
}

# Kept beside the big battle list so a famous war cannot crowd them out.
EXTRA_EVENT_CLASSES = {
    "Q209715": "politics",  # coronation
    "Q3882219": "politics",  # assassination
    "Q12772819": "technology",  # discovery
    "Q12579633": "technology",  # invention
}

CHINESE_STATES = ["Q148", "Q29520", "Q13426199", "Q8733", "Q9903", "Q7313", "Q9683", "Q7462", "Q7209", "Q35216"]

EXISTING_COUNTRIES = {
    "Q148": "china", "Q29520": "china", "Q8646": "china", "Q14773": "china", "Q865": "taiwan",
    "Q13426199": "china",
    "Q17": "japan", "Q884": "korea", "Q423": "korea",
    "Q159": "russia", "Q15180": "russia", "Q34266": "russia",
    "Q796": "iraq", "Q851": "arabia", "Q12560": "ottoman", "Q794": "iran", "Q79": "egypt",
    "Q41": "greece", "Q38": "italy", "Q145": "england", "Q21": "england", "Q183": "germany",
    "Q40": "austria", "Q29": "spain", "Q142": "france", "Q96": "mexico", "Q419": "peru",
    "Q750": "bolivia", "Q155": "brazil", "Q778": "bahamas",
}

CONTINENTS = {
    "Q46": "europe", "Q49": "americas", "Q18": "americas", "Q828": "americas",
    "Q55643": "oceania", "Q538": "oceania", "Q15": "africa", "Q48": "asia",
}


def sparql(name: str, query: str, refresh: bool, endpoint: str = ENDPOINT) -> list[dict]:
    CACHE.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1(query.encode()).hexdigest()[:10]
    path = CACHE / f"{name}-{key}.json"
    if path.exists() and not refresh:
        return json.loads(path.read_text(encoding="utf-8"))
    body = urllib.parse.urlencode({"query": PREFIX + query}).encode()
    request = urllib.request.Request(
        endpoint,
        data=body,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/sparql-results+json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    for attempt in range(8):
        try:
            time.sleep(1.2)
            with urllib.request.urlopen(request, timeout=300) as response:
                rows = json.load(response)["results"]["bindings"]
            break
        except urllib.error.HTTPError as error:
            if attempt == 7:
                raise
            wait = 25 * (attempt + 1) if error.code == 429 else 8 * (attempt + 1)
            print(f"  retry {name}: {error}", file=sys.stderr)
            time.sleep(wait)
        except (urllib.error.URLError, TimeoutError) as error:
            if attempt == 7:
                raise
            print(f"  retry {name}: {error}", file=sys.stderr)
            time.sleep(8 * (attempt + 1))
    path.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    return rows


def qid(binding: dict | None) -> str | None:
    if not binding or binding.get("type") != "uri":
        return None
    match = re.search(r"/entity/(Q\d+)$", binding["value"])
    return match.group(1) if match else None


def historical_year(binding: dict | None) -> int | None:
    """Wikidata RDF uses XSD 1.1 years (0 = 1 BCE); convert to -N = N BCE."""
    if not binding:
        return None
    match = re.match(r"^(-?)(\d{1,})-", binding["value"])
    if not match:
        return None
    year = int(match.group(2)) * (-1 if match.group(1) else 1)
    return year if year > 0 else year - 1


def point(binding: dict | None) -> tuple[float, float] | None:
    if not binding:
        return None
    match = re.match(r"point\(([-\d.eE]+) ([-\d.eE]+)\)", binding["value"], re.IGNORECASE)
    if not match:
        return None
    lon, lat = float(match.group(1)), float(match.group(2))
    if not (-180 <= lon <= 180 and -90 <= lat <= 90):
        return None
    return lon, lat


class Pick:
    """Collect multi-valued SPARQL rows into one record per entity."""

    def __init__(self):
        self.labels: dict[str, str] = {}
        self.descs: dict[str, str] = {}
        self.values: dict[str, list] = {}

    def text(self, kind: str, binding: dict | None):
        if not binding:
            return
        store = self.labels if kind == "label" else self.descs
        store.setdefault(binding.get("xml:lang", ""), binding["value"])

    def add(self, key: str, value):
        if value is not None and value not in self.values.setdefault(key, []):
            self.values[key].append(value)

    def first(self, key: str):
        values = self.values.get(key) or []
        return values[0] if values else None

    def label(self) -> str | None:
        text = next((self.labels[lang] for lang in ZH_LANGS if lang in self.labels), None)
        return T2S.convert(text) if text else None

    def desc(self) -> str | None:
        text = next((self.descs[lang] for lang in ZH_LANGS[:5] if lang in self.descs), None)
        return T2S.convert(text) if text else None

    def lowest(self, key: str):
        values = self.values.get(key) or []
        return min(values) if values else None

    def highest(self, key: str):
        values = self.values.get(key) or []
        return max(values) if values else None


def collect(rows: list[dict], id_var: str, fields: dict) -> dict[str, Pick]:
    picks: dict[str, Pick] = {}
    for row in rows:
        key = qid(row.get(id_var))
        if not key:
            continue
        pick = picks.setdefault(key, Pick())
        pick.text("label", row.get("label"))
        pick.text("desc", row.get("desc"))
        for var, parse in fields.items():
            pick.add(var, parse(row.get(var)))
    return picks


def literal(binding):
    return binding["value"] if binding else None


def number(binding):
    return int(binding["value"]) if binding else None


def article(binding):
    if not binding:
        return None
    return urllib.parse.unquote(binding["value"].rsplit("/wiki/", 1)[-1]).replace("_", " ")


def commons_file(binding):
    if not binding:
        return None
    return urllib.parse.unquote(binding["value"].rsplit("/", 1)[-1]).replace("_", " ")


def batched(items: list[str], size: int):
    for start in range(0, len(items), size):
        yield start // size, items[start:start + size]


LABEL_BLOCK = """
  OPTIONAL { ?%(v)s rdfs:label ?label FILTER(LANG(?label) IN ("zh-hans","zh-cn","zh-sg","zh","zh-my","zh-hant","zh-tw","zh-hk")) }
  OPTIONAL { ?%(v)s schema:description ?desc FILTER(LANG(?desc) IN ("zh-hans","zh-cn","zh-sg","zh","zh-my")) }
  OPTIONAL { ?art schema:about ?%(v)s ; schema:isPartOf <https://zh.wikipedia.org/> }
"""


def fetch_people(refresh: bool) -> dict[str, Pick]:
    ranked = sparql("people-top", f"""
SELECT DISTINCT ?p ?sl WHERE {{
  ?p wdt:P31 wd:Q5 ; wikibase:sitelinks ?sl ; wdt:P569 ?b .
  FILTER(?sl >= 45 && YEAR(?b) <= {LATEST_BIRTH})
}} ORDER BY DESC(?sl) LIMIT {PEOPLE_LIMIT}
""", refresh)
    states = " ".join(f"wd:{q}" for q in CHINESE_STATES)
    chinese = sparql("people-china", f"""
SELECT DISTINCT ?p ?sl WHERE {{
  VALUES ?state {{ {states} }}
  ?p wdt:P31 wd:Q5 ; wikibase:sitelinks ?sl ; wdt:P569 ?b ; wdt:P27 ?state .
  FILTER(?sl >= 8 && YEAR(?b) <= {LATEST_BIRTH})
}} ORDER BY DESC(?sl) LIMIT 2200
""", refresh)
    ids = list(dict.fromkeys(q for row in ranked + chinese if (q := qid(row["p"]))))
    print(f"people candidates: {len(ids)}")
    picks: dict[str, Pick] = {}
    for n, chunk in batched(ids, 300):
        values = " ".join(f"wd:{q}" for q in chunk)
        rows = sparql(f"people-detail-{n}", f"""
SELECT ?p ?label ?desc ?birth ?death ?bp ?citizen ?img ?art ?sl WHERE {{
  VALUES ?p {{ {values} }}
  ?p wikibase:sitelinks ?sl .
  {LABEL_BLOCK % {"v": "p"}}
  OPTIONAL {{ ?p wdt:P569 ?birth }}
  OPTIONAL {{ ?p wdt:P570 ?death }}
  OPTIONAL {{ ?p wdt:P19 ?bp }}
  OPTIONAL {{ ?p wdt:P27 ?citizen }}
  OPTIONAL {{ ?p wdt:P18 ?img }}
}}
""", refresh)
        picks.update(collect(rows, "p", {
            "birth": historical_year, "death": historical_year, "bp": qid, "citizen": qid,
            "img": commons_file, "art": article, "sl": number,
        }))
    return picks


def fetch_events(refresh: bool) -> dict[str, Pick]:
    classes = " ".join(f"wd:{q}" for q in list(EVENT_CLASSES) + list(EXTRA_EVENT_CLASSES))
    ranked = []
    for cls in EVENT_CLASSES:
        ranked += sparql(f"events-{cls}", f"""
SELECT ?e ?sl WHERE {{
  ?e wdt:P31/wdt:P279* wd:{cls} .
  ?e wikibase:sitelinks ?sl .
}} ORDER BY DESC(?sl) LIMIT {EVENT_LIMIT}
""", refresh)
    ranked = [row for row in ranked if int(row["sl"]["value"]) >= 8]
    ranked.sort(key=lambda row: -int(row["sl"]["value"]))
    ranked = ranked[: EVENT_LIMIT * 2]
    states = " ".join(f"wd:{q}" for q in CHINESE_STATES)
    china = sparql("events-china", f"""
SELECT DISTINCT ?e ?sl WHERE {{
  VALUES ?state {{ {states} }}
  VALUES ?cls {{ {classes} }}
  ?e wdt:P31/wdt:P279* ?cls ; wikibase:sitelinks ?sl ; wdt:P17 ?state .
  FILTER(?sl >= 3)
}} ORDER BY DESC(?sl) LIMIT 1600
""", refresh)
    extra = []
    for cls in EXTRA_EVENT_CLASSES:
        extra += sparql(f"events-extra-{cls}", f"""
SELECT ?e ?sl WHERE {{
  ?e wdt:P31 wd:{cls} ; wikibase:sitelinks ?sl .
  FILTER(?sl >= 6)
}} ORDER BY DESC(?sl) LIMIT 400
""", refresh)
    ids = list(dict.fromkeys(q for row in ranked + china + extra if (q := qid(row["e"]))))
    print(f"event candidates: {len(ids)}")
    picks: dict[str, Pick] = {}
    for n, chunk in batched(ids, 250):
        values = " ".join(f"wd:{q}" for q in chunk)
        rows = sparql(f"events-detail-{n}", f"""
SELECT ?e ?label ?desc ?at ?invented ?inception ?from ?to ?coord ?loc ?country ?who ?cls ?img ?art ?sl WHERE {{
  VALUES ?e {{ {values} }}
  ?e wikibase:sitelinks ?sl .
  {LABEL_BLOCK % {"v": "e"}}
  OPTIONAL {{ ?e wdt:P585 ?at }}
  OPTIONAL {{ ?e wdt:P575 ?invented }}
  OPTIONAL {{ ?e wdt:P571 ?inception }}
  OPTIONAL {{ ?e wdt:P580 ?from }}
  OPTIONAL {{ ?e wdt:P582 ?to }}
  OPTIONAL {{ ?e wdt:P625 ?coord }}
  OPTIONAL {{ ?e wdt:P276 ?loc }}
  OPTIONAL {{ ?e wdt:P17 ?country }}
  OPTIONAL {{ ?e wdt:P710 ?who }}
  OPTIONAL {{ ?e wdt:P31 ?cls }}
  OPTIONAL {{ ?e wdt:P18 ?img }}
}}
""", refresh)
        picks.update(collect(rows, "e", {
            "at": historical_year, "invented": historical_year, "inception": historical_year,
            "from": historical_year, "to": historical_year, "coord": point,
            "loc": qid, "country": qid, "who": qid, "cls": qid, "img": commons_file, "art": article,
            "sl": number,
        }))
    for pick in picks.values():
        if pick.values.get("at"):
            continue
        for key in ("invented", "inception"):
            if pick.values.get(key):
                pick.values["at"] = list(pick.values[key])
                break
    return picks


def zh_literal(binding):
    if not binding or binding.get("xml:lang") not in ZH_LANGS:
        return None
    return T2S.convert(binding["value"])


def fetch_works(refresh: bool) -> dict[str, Pick]:
    """Bibliographic records only: title, year, author and a one-line description. No full text."""
    ranked = sparql("works-top", """
SELECT ?w ?sl WHERE {
  ?w wdt:P31/wdt:P279* wd:Q7725634 ; wikibase:sitelinks ?sl ; wdt:P577 ?pub .
  FILTER(?sl >= 18 && YEAR(?pub) >= -3000 && YEAR(?pub) <= 2000)
} ORDER BY DESC(?sl) LIMIT 500
""", refresh)
    chinese = sparql("works-zh", """
SELECT ?w ?sl WHERE {
  ?w wdt:P31/wdt:P279* wd:Q7725634 ; wikibase:sitelinks ?sl ; wdt:P577 ?pub ; wdt:P407 wd:Q7850 .
  FILTER(?sl >= 3 && YEAR(?pub) >= -800 && YEAR(?pub) <= 2000)
} ORDER BY DESC(?sl) LIMIT 700
""", refresh)
    ids = list(dict.fromkeys(q for row in ranked + chinese if (q := qid(row["w"]))))
    print(f"work candidates: {len(ids)}")
    picks: dict[str, Pick] = {}
    for n, chunk in batched(ids, 60):
        values = " ".join(f"wd:{q}" for q in chunk)
        rows = sparql(f"works-detail-{n}", f"""
SELECT ?w ?label ?desc ?published ?country ?art ?sl WHERE {{
  VALUES ?w {{ {values} }}
  ?w wikibase:sitelinks ?sl .
  {LABEL_BLOCK % {"v": "w"}}
  OPTIONAL {{ ?w wdt:P577 ?published }}
  OPTIONAL {{ ?w wdt:P495 ?country }}
}}
""", refresh, endpoint=OFFICIAL)
        picks.update(collect(rows, "w", {
            "published": historical_year, "country": qid, "art": article, "sl": number,
        }))
    return picks


def fetch_links(people: list[str], events: set[str], refresh: bool) -> dict[str, set[str]]:
    """Event qid -> people qids, from P1344 (participant in) and P607 (conflict)."""
    links: dict[str, set[str]] = {}
    for n, chunk in batched(people, 400):
        values = " ".join(f"wd:{q}" for q in chunk)
        rows = sparql(f"links-{n}", f"""
SELECT ?p ?e WHERE {{
  VALUES ?p {{ {values} }}
  {{ ?p wdt:P1344 ?e }} UNION {{ ?p wdt:P607 ?e }}
}}
""", refresh)
        for row in rows:
            event, person = qid(row.get("e")), qid(row.get("p"))
            if event in events and person:
                links.setdefault(event, set()).add(person)
    return links


def fetch_places(ids: list[str], refresh: bool, name: str) -> dict[str, Pick]:
    picks: dict[str, Pick] = {}
    for n, chunk in batched(ids, 300):
        values = " ".join(f"wd:{q}" for q in chunk)
        rows = sparql(f"{name}-{n}", f"""
SELECT ?x ?label ?desc ?coord ?country ?continent ?cls ?img ?art WHERE {{
  VALUES ?x {{ {values} }}
  {LABEL_BLOCK % {"v": "x"}}
  OPTIONAL {{ ?x wdt:P31 ?cls }}
  OPTIONAL {{ ?x wdt:P625 ?coord }}
  OPTIONAL {{ ?x wdt:P17 ?country }}
  OPTIONAL {{ ?x wdt:P30 ?continent }}
  OPTIONAL {{ ?x wdt:P18 ?img }}
}}
""", refresh)
        picks.update(collect(rows, "x", {
            "coord": point, "country": qid, "continent": qid, "cls": qid, "img": commons_file, "art": article,
        }))
    return picks


def distance_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    lon1, lat1, lon2, lat2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def assign_region(continents: list[str], lon: float, lat: float) -> str:
    kinds = {CONTINENTS.get(c) for c in continents} - {None}
    if "europe" in kinds and "asia" not in kinds:
        return "europe"
    if "americas" in kinds:
        return "americas"
    if "oceania" in kinds:
        return "oceania"
    if "africa" in kinds:
        return "west-asia-north-africa" if lat >= 18 else "africa"
    if not kinds:
        if lon < -30:
            return "americas"
        if lat > 36 and -25 < lon < 40:
            return "europe"
        if lat < 18 and -20 < lon < 52:
            return "africa"
    if lon < 60:
        return "west-asia-north-africa" if lat < 42 else "europe"
    if lat >= 38 and lon < 110:
        return "central-asia"
    if lon < 92:
        return "south-asia"
    if lat < 23:
        return "southeast-asia"
    if lon > 110 and lat < -10:
        return "oceania"
    return "east-asia"


class Gazetteer:
    def __init__(self, places: list[dict]):
        self.base = places
        self.by_slug = {p["slug"]: p for p in places}
        self.added: dict[str, dict] = {}
        self.sort = 5000

    def all(self):
        return list(self.by_slug.values())

    def root_country(self, slug: str) -> str | None:
        current = self.by_slug.get(slug)
        while current and current["level"] not in ("country", "region"):
            current = self.by_slug.get(current["parent"])
        return current["slug"] if current and current["level"] == "country" else None

    def add(self, entry: dict) -> str:
        self.sort += 1
        entry["sort_order"] = self.sort
        self.by_slug[entry["slug"]] = entry
        self.added[entry["slug"]] = entry
        return entry["slug"]


def country_slug(gaz: Gazetteer, q: str, countries: dict[str, Pick]) -> str | None:
    if q in CHINESE_STATES:
        return "china"
    if q in EXISTING_COUNTRIES:
        return EXISTING_COUNTRIES[q]
    slug = f"wd-{q.lower()}"
    if slug in gaz.by_slug:
        return slug
    pick = countries.get(q)
    if not pick or not pick.label() or not pick.first("coord"):
        return None
    lon, lat = pick.first("coord")
    return gaz.add({
        "slug": slug, "name": pick.label(), "parent": assign_region(pick.values.get("continent", []), lon, lat),
        "level": "country", "latitude": round(lat, 3), "longitude": round(lon, 3),
        "wikidata": q, "image": pick.first("img"), "zhwiki": pick.first("art"), "description": pick.desc(),
    })


def place_slug(gaz: Gazetteer, q: str | None, places: dict[str, Pick], countries: dict[str, Pick]) -> str | None:
    if not q:
        return None
    if q in EXISTING_COUNTRIES or q in countries and q not in places:
        return country_slug(gaz, q, countries)
    slug = f"wd-{q.lower()}"
    if slug in gaz.by_slug:
        return slug
    if q in CHINESE_STATES:
        return "china"
    pick = places.get(q)
    if not pick:
        return None
    parent = next((s for c in pick.values.get("country", []) if c != q and (s := country_slug(gaz, c, countries))), None)
    if STATE_CLASSES & set(pick.values.get("cls", [])):
        return parent or country_slug(gaz, q, {**countries, q: pick})
    if not pick.first("coord"):
        return parent
    if q in countries or pick.label() is None:
        return parent
    lon, lat = pick.first("coord")
    if parent:
        country = gaz.root_country(parent) or parent
        for existing in gaz.all():
            if existing["level"] in ("city", "province") and gaz.root_country(existing["slug"]) == country:
                if distance_km((lon, lat), (existing["longitude"], existing["latitude"])) < REUSE_KM:
                    return existing["slug"]
    if not parent:
        return None
    return gaz.add({
        "slug": slug, "name": pick.label(), "parent": parent, "level": "city",
        "latitude": round(lat, 3), "longitude": round(lon, 3),
        "wikidata": q, "image": pick.first("img"), "zhwiki": pick.first("art"), "description": pick.desc(),
    })


def year_text(year: int) -> str:
    return f"公元前{-year}年" if year < 0 else f"{year}年"


def year_short(year: int) -> str:
    return f"前{-year}" if year < 0 else str(year)


def citation(title: str | None, q: str) -> dict:
    if title:
        return {
            "edition_label": "维基百科条目",
            "locator": "条目正文",
            "stable_url": "https://zh.wikipedia.org/wiki/" + title.replace(" ", "_"),
        }
    return {"edition_label": "维基数据", "locator": q, "stable_url": f"https://www.wikidata.org/wiki/{q}"}


def clean(text: str | None) -> str:
    return (text or "").strip().rstrip("。.；;，,")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()

    people = fetch_people(args.refresh)
    events = fetch_events(args.refresh)
    try:
        works = fetch_works(args.refresh)
    except Exception as error:
        print(f"works skipped: {error}", file=sys.stderr)
        works = {}
    try:
        links = fetch_links(list(people), set(events), args.refresh)
    except Exception as error:
        print(f"links skipped: {error}", file=sys.stderr)
        links = {}

    location_ids = {q for p in people.values() for q in p.values.get("bp", [])}
    location_ids |= {q for e in events.values() for q in e.values.get("loc", [])}
    places = fetch_places(sorted(location_ids), args.refresh, "places")
    country_ids = {q for p in places.values() for q in p.values.get("country", [])}
    country_ids |= {q for e in events.values() for q in e.values.get("country", [])}
    country_ids |= {q for p in people.values() for q in p.values.get("citizen", [])}
    country_ids |= {q for w in works.values() for q in w.values.get("country", [])}
    countries = fetch_places(sorted(country_ids), args.refresh, "countries")
    print(f"places: {len(places)}, countries: {len(countries)}")

    gaz = Gazetteer(json.loads(GAZETTEER.read_text(encoding="utf-8"))["places"])
    claims = []
    people_out = []
    skipped = {"person": 0, "event": 0}

    for q, pick in sorted(people.items(), key=lambda item: -(item[1].first("sl") or 0)):
        name, birth = pick.label(), pick.lowest("birth")
        if not name or birth is None:
            skipped["person"] += 1
            continue
        slug = place_slug(gaz, pick.first("bp"), places, countries)
        if not slug:
            slug = next((s for c in pick.values.get("citizen", []) if (s := country_slug(gaz, c, countries))), None)
        if not slug:
            skipped["person"] += 1
            continue
        death = pick.first("death")
        desc = clean(pick.desc())
        people_out.append({
            "qid": q, "name": name, "birth_year": birth, "death_year": death, "description": desc,
            "place_slug": slug, "image": pick.first("img"), "zhwiki": pick.first("art"),
            "sitelinks": pick.first("sl") or 0,
        })
        where = gaz.by_slug[slug]["name"]
        lead = desc if desc and len(desc) <= 18 else ""
        claims.append({
            "review_batch": "wikidata-1",
            "text": f"{year_text(birth)}，{lead}{name}出生于{where}。",
            "start_year": birth, "end_year": birth, "precision": "year",
            "display_text": year_short(birth), "region_slugs": [slug], "topic_slugs": ["society"],
            "certainty": "unverified", "people": [name], "person_qids": [q],
            "event_title": f"{name}出生", "snapshot_label": f"{name}生平", "snapshot_dimension": "society",
            "citation": citation(pick.first("art"), q), "wikidata": q,
        })

    people_names = {p["qid"]: p["name"] for p in people_out}
    for q, pick in sorted(events.items(), key=lambda item: -(item[1].first("sl") or 0)):
        title = pick.label()
        start = pick.lowest("from") if pick.lowest("from") is not None else pick.lowest("at")
        end = pick.highest("to") if pick.highest("to") is not None else pick.highest("at")
        if not title or start is None or re.search(r"[A-Za-z]{4,}", title):
            skipped["event"] += 1
            continue
        end = max(start, end if end is not None else start)
        if end > LATEST_EVENT or start < -3000:
            skipped["event"] += 1
            continue
        slug = None
        coord = pick.first("coord")
        if coord:
            country = next((s for c in pick.values.get("country", []) if (s := country_slug(gaz, c, countries))), None)
            loc = place_slug(gaz, pick.first("loc"), places, countries)
            if loc and loc not in EXISTING_COUNTRIES.values() and gaz.by_slug[loc]["level"] != "country":
                slug = loc
            elif country:
                cslug = f"wd-{q.lower()}"
                slug = gaz.add({
                    "slug": cslug, "name": title[:12], "parent": country, "level": "city",
                    "latitude": round(coord[1], 3), "longitude": round(coord[0], 3), "wikidata": q,
                    "image": None, "zhwiki": None, "description": None,
                }) if cslug not in gaz.by_slug else cslug
        if not slug:
            slug = place_slug(gaz, pick.first("loc"), places, countries)
        if not slug:
            slug = next((s for c in pick.values.get("country", []) if (s := country_slug(gaz, c, countries))), None)
        if not slug:
            skipped["event"] += 1
            continue
        topic_classes = {**EVENT_CLASSES, **EXTRA_EVENT_CLASSES}
        topic = next((topic_classes[c] for c in pick.values.get("cls", []) if c in topic_classes), "politics")
        who = sorted(set(pick.values.get("who", [])) | links.get(q, set()))
        who = [p for p in who if p in people_names]
        when = year_text(start) if start == end else f"{year_text(start)}至{year_text(end)}"
        desc = clean(pick.desc())
        text = f"{when}，{title}" + (f"：{desc}" if desc and desc != title else "") + "。"
        sensitive = end >= 1949 and (gaz.root_country(slug) == "china" or slug == "china")
        claims.append({
            "review_batch": SENSITIVE_BATCH if sensitive else "wikidata-1",
            "text": text, "start_year": start, "end_year": end,
            "precision": "year" if start == end else "range",
            "display_text": year_short(start) if start == end else f"{year_short(start)}–{year_short(end)}",
            "region_slugs": [slug], "topic_slugs": [topic], "certainty": "unverified",
            "people": [people_names[p] for p in who], "person_qids": who,
            "event_title": title, "snapshot_label": title, "snapshot_dimension": topic,
            "citation": citation(pick.first("art"), q), "wikidata": q,
            "event_image": pick.first("img"),
        })

    for q, pick in sorted(works.items(), key=lambda item: -(item[1].first("sl") or 0)):
        title = pick.label()
        year = pick.lowest("published")
        if not title or year is None or re.search(r"[A-Za-z]{4,}", title):
            continue
        if year < -3000 or year > LATEST_EVENT:
            continue
        slug = next((s for c in pick.values.get("country", []) if (s := country_slug(gaz, c, countries))), None)
        if not slug:
            skipped["event"] += 1
            continue
        author = pick.first("authorLabel")
        author_q = pick.first("author")
        desc = clean(pick.desc())
        made = f"，{author}完成《{title}》" if author else f"，《{title}》成书"
        text = f"{year_text(year)}{made}" + (f"：{desc}" if desc and desc != title else "") + "。"
        sensitive = year >= 1949 and (gaz.root_country(slug) == "china" or slug == "china")
        known = [author_q] if author_q in people_names else []
        claims.append({
            "review_batch": SENSITIVE_BATCH if sensitive else "wikidata-1",
            "text": text, "start_year": year, "end_year": year, "precision": "year",
            "display_text": year_short(year), "region_slugs": [slug], "topic_slugs": ["culture"],
            "certainty": "unverified",
            "people": [author] if author else [],
            "person_qids": known,
            "event_title": f"《{title}》",
            "snapshot_label": f"《{title}》",
            "snapshot_dimension": "culture",
            "citation": citation(pick.first("art"), q), "wikidata": q,
        })

    OUT_PLACES.write_text(json.dumps({
        "note": "由 build_wikidata.py 生成的地点，来源维基数据（CC0），待人工核对。",
        "places": list(gaz.added.values()),
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    OUT_PEOPLE.write_text(json.dumps({
        "note": "由 build_wikidata.py 生成的人物，来源维基数据（CC0），待人工核对。",
        "people": people_out,
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    OUT_SEED.write_text(json.dumps({
        "source": {
            "title": "维基数据",
            "kind": "dataset",
            "license_status": "open",
            "canonical_url": "https://www.wikidata.org/",
            "license_note": "结构化数据以 CC0 发布。陈述由程序按模板生成，全部为待核查候选，发布前需要人工对照出处。",
        },
        "claims": claims,
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"people: {len(people_out)}, claims: {len(claims)}, new places: {len(gaz.added)}, skipped: {skipped}")


if __name__ == "__main__":
    main()
