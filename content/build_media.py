"""Fetch licensed thumbnails from Wikimedia Commons and zh.wikipedia summaries.

Images are re-encoded to WebP and written under backend/media/commons/, so the
app loads them from our own server instead of Wikimedia (unstable in mainland
China). Only public-domain, CC0, CC BY and CC BY-SA files are kept.

    python content/build_media.py
"""

import concurrent.futures
import hashlib
import html
import io
import json
import re
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"
MEDIA_ROOT = ROOT / "backend" / "media"
MANIFEST = CONTENT / "media_manifest.json"
SKIPPED = CONTENT / "media_skipped.json"
SUMMARIES = CONTENT / "wiki_summaries.json"
socket.setdefaulttimeout(25)
USER_AGENT = "ChangheContentBuild/0.3 (historical atlas app; media pipeline)"
THUMB_WIDTH = 330
WEBP_QUALITY = 72
ALLOWED = re.compile(r"^(public domain|pd\b|pd-|cc0|cc[- ]by(-sa)?[- ]\d)", re.IGNORECASE)
BLOCKED = re.compile(r"\b(nc|nd)\b|non-?commercial|no ?deriv", re.IGNORECASE)


def pause_for(error: Exception, attempt: int) -> None:
    retry_after = 0
    if isinstance(error, urllib.error.HTTPError):
        try:
            retry_after = int(error.headers.get("Retry-After") or 0)
        except (TypeError, ValueError):
            retry_after = 0
        if error.code == 429:
            time.sleep(max(retry_after, 20 * (attempt + 1)))
            return
    time.sleep(4 * (attempt + 1))


def request_json(url: str) -> dict | None:
    """Return parsed JSON, {} for a confirmed miss, or None when the request should be retried later."""
    for attempt in range(8):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=60) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return {}
            pause_for(error, attempt)
        except (urllib.error.URLError, TimeoutError) as error:
            pause_for(error, attempt)
    return None


def fetch_bytes(url: str) -> bytes | None:
    for attempt in range(8):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=60) as response:
                return response.read()
        except urllib.error.HTTPError as error:
            if error.code in (400, 403, 404):
                return None
            pause_for(error, attempt)
        except (urllib.error.URLError, TimeoutError) as error:
            pause_for(error, attempt)
    return None


def plain(text: str | None) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", text or "")).strip()[:500]


def licence_ok(name: str) -> bool:
    return bool(name) and bool(ALLOWED.search(name)) and not BLOCKED.search(name)


def image_titles() -> list[str]:
    people = json.loads((CONTENT / "wikidata_people.json").read_text(encoding="utf-8"))["people"]
    places = json.loads((CONTENT / "gazetteer_wikidata.json").read_text(encoding="utf-8"))["places"]
    titles = [p["image"] for p in people if p.get("image")]
    titles += [p["image"] for p in places if p.get("image")]
    return list(dict.fromkeys(titles))


def image_info(titles: list[str]) -> tuple[dict[str, dict], set[str]]:
    info = {}
    missing = set()
    for start in range(0, len(titles), 20):
        chunk = titles[start:start + 20]
        query = urllib.parse.urlencode({
            "action": "query", "format": "json", "prop": "imageinfo",
            "iiprop": "url|size|extmetadata", "iiurlwidth": THUMB_WIDTH,
            "iiextmetadatafilter": "LicenseShortName|LicenseUrl|Artist",
            "titles": "|".join("File:" + t for t in chunk),
        })
        data = request_json("https://commons.wikimedia.org/w/api.php?" + query)
        if data is None:
            print(f"  imageinfo {min(start + 20, len(titles))}/{len(titles)} deferred", file=sys.stderr)
            time.sleep(2)
            continue
        normalized = {n["to"]: n["from"] for n in data.get("query", {}).get("normalized", [])}
        seen = set()
        for page in data.get("query", {}).get("pages", {}).values():
            title = normalized.get(page.get("title", ""), page.get("title", "")).removeprefix("File:")
            seen.add(title)
            if page.get("missing") is not None or page.get("invalid") is not None:
                missing.add(title)
                continue
            if not page.get("imageinfo"):
                continue
            item = page["imageinfo"][0]
            meta = item.get("extmetadata", {})
            info[title] = {
                "thumb": item.get("thumburl"),
                "source_url": item.get("descriptionurl"),
                "license": plain(meta.get("LicenseShortName", {}).get("value")),
                "license_url": plain(meta.get("LicenseUrl", {}).get("value")),
                "author": plain(meta.get("Artist", {}).get("value")),
            }
        print(f"  imageinfo {min(start + 20, len(titles))}/{len(titles)}", file=sys.stderr)
        time.sleep(1.2)
    return info, missing


def store(title: str, meta: dict) -> dict | None:
    digest = hashlib.sha1(title.encode("utf-8")).hexdigest()
    relative = f"commons/{digest[:2]}/{digest}.webp"
    target = MEDIA_ROOT / relative
    if not target.exists():
        raw = fetch_bytes(meta["thumb"])
        if raw is None:
            return None
        try:
            image = Image.open(io.BytesIO(raw))
            image = image.convert("RGBA" if image.mode in ("RGBA", "LA", "P") else "RGB")
        except OSError:
            return None
        image.thumbnail((THUMB_WIDTH, THUMB_WIDTH * 2))
        target.parent.mkdir(parents=True, exist_ok=True)
        image.save(target, "WEBP", quality=WEBP_QUALITY, method=5)
    with Image.open(target) as saved:
        width, height = saved.size
    return {
        "file": relative, "width": width, "height": height, "author": meta["author"],
        "license": meta["license"], "license_url": meta["license_url"], "source_url": meta["source_url"],
    }


def build_images() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    skipped = json.loads(SKIPPED.read_text(encoding="utf-8")) if SKIPPED.exists() else {}
    titles = [t for t in image_titles() if t not in manifest and t not in skipped]
    print(f"images to process: {len(titles)} (already have {len(manifest)}, skipped {len(skipped)})")
    info, missing = image_info(titles)
    for title in missing:
        skipped[title] = "missing"
    usable = {}
    for title, meta in info.items():
        if not meta["thumb"]:
            skipped[title] = "no-thumb"
        elif not licence_ok(meta["license"]):
            skipped[title] = meta["license"] or "licence-rejected"
        else:
            usable[title] = meta
    print(f"licence ok: {len(usable)}/{len(info)}")
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures = {pool.submit(store, t, m): t for t, m in usable.items()}
        for n, future in enumerate(concurrent.futures.as_completed(futures), start=1):
            entry = future.result()
            if entry:
                manifest[futures[future]] = entry
            if n % 50 == 0:
                print(f"  stored {n}/{len(usable)}", file=sys.stderr)
                MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
                SKIPPED.write_text(json.dumps(skipped, ensure_ascii=False, indent=1), encoding="utf-8")
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    SKIPPED.write_text(json.dumps(skipped, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"manifest: {len(manifest)} images, skipped: {len(skipped)}")


def summary(title: str) -> str | None:
    """Return text, \"\" when the article is confirmed missing, or None to retry later."""
    url = "https://zh.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(title.replace(" ", "_"))
    for attempt in range(6):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept-Language": "zh-cn"})
            with urllib.request.urlopen(req, timeout=40) as response:
                text = json.load(response).get("extract") or ""
            return text.strip()[:600]
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return ""
            pause_for(error, attempt)
        except (urllib.error.URLError, TimeoutError) as error:
            pause_for(error, attempt)
    return None


def build_summaries() -> None:
    people = json.loads((CONTENT / "wikidata_people.json").read_text(encoding="utf-8"))["people"]
    places = json.loads((CONTENT / "gazetteer_wikidata.json").read_text(encoding="utf-8"))["places"]
    existing = json.loads(SUMMARIES.read_text(encoding="utf-8")) if SUMMARIES.exists() else {}
    # Earlier runs stored null when the network failed. Those are not confirmed misses.
    existing = {title: text for title, text in existing.items() if text is not None}
    titles = [p["zhwiki"] for p in people + places if p.get("zhwiki") and p["zhwiki"] not in existing]
    titles = list(dict.fromkeys(titles))
    print(f"summaries to fetch: {len(titles)} (already have {len(existing)})")
    for done, title in enumerate(titles, start=1):
        text = summary(title)
        if text is not None:
            existing[title] = text
        if done % 20 == 0:
            print(f"  summaries {done}/{len(titles)}", file=sys.stderr)
            SUMMARIES.write_text(json.dumps(existing, ensure_ascii=False, indent=1), encoding="utf-8")
        time.sleep(0.35)
    SUMMARIES.write_text(json.dumps(existing, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"summaries: {sum(1 for v in existing.values() if v)} usable")


if __name__ == "__main__":
    build_images()
    build_summaries()
