"""Fetch zh.wikipedia section extracts for event archive pages.

One plain-text extract per article. Only sections whose titles mention
background, course, or consequence are kept. The file is rewritten every 20
articles so a run can stop and continue.

    python content/build_briefs.py --limit 400
"""

import argparse
import html
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"
OUTPUT = CONTENT / "wiki_briefs.json"
SEEDS = [
    CONTENT / "seed" / "early-modern.json",
    CONTENT / "seed" / "early-modern-skeleton.json",
    CONTENT / "seed" / "long-span.json",
    CONTENT / "seed" / "wikidata.json",
    CONTENT / "seed" / "modern-china.json",
]
HELD_BATCHES = {"china-1949-plus"}
USER_AGENT = "LongriverContentBuild/0.4 (historical atlas app; encyclopedia extracts)"
KEEP = ("背景", "起因", "经过", "經過", "过程", "過程", "结果", "結果", "影响", "影響", "意义", "意義", "后果", "後果")
SKIP = (
    "参考文献", "參考文獻", "参考资料", "參考資料", "参见", "參見",
    "注释", "註釋", "脚注", "腳注", "外部链接", "外部連結", "延伸阅读", "延伸閱讀",
)
SECTION_LIMIT = 500
BRIEF_LIMIT = 1600


def read(path: Path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def article_title(url: str) -> str:
    if "/wiki/" not in url:
        return ""
    return urllib.parse.unquote(url.rsplit("/wiki/", 1)[-1]).replace("_", " ")


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
    """Return JSON, {} for a confirmed miss, or None when the request should be retried later."""
    for attempt in range(6):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept-Language": "zh-cn"})
            with urllib.request.urlopen(req, timeout=40) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return {}
            pause_for(error, attempt)
        except (urllib.error.URLError, TimeoutError) as error:
            pause_for(error, attempt)
    return None


def fetch_page(title: str) -> dict | None:
    query = urllib.parse.urlencode(
        {
            "action": "query",
            "prop": "extracts",
            "explaintext": "1",
            "exsectionformat": "wiki",
            "redirects": "1",
            "format": "json",
            "titles": title,
        }
    )
    payload = request_json("https://zh.wikipedia.org/w/api.php?" + query)
    if payload is None or payload == {}:
        return payload
    pages = (payload.get("query") or {}).get("pages") or {}
    page = next(iter(pages.values()), {})
    if page.get("missing") is not None:
        return {}
    return page


def plain(value: str) -> str:
    text = re.sub(r"<sup[^>]*>.*?</sup>", "", value or "", flags=re.S)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def clip(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    cut = text[:limit]
    for mark in ("。", "！", "？"):
        index = cut.rfind(mark)
        if index >= int(limit * 0.6):
            return cut[: index + 1]
    return cut.rstrip("，,；;、 ")


def wanted(heading: str) -> bool:
    if any(word in heading for word in SKIP):
        return False
    return any(word in heading for word in KEEP)


def extract(page: dict) -> list[dict]:
    text = page.get("extract") or ""
    marks = list(re.finditer(r"^(=+) *(.+?) *\1 *$", text, flags=re.M))
    found = []
    for index, mark in enumerate(marks):
        heading = plain(mark.group(2))
        start = mark.end()
        end = marks[index + 1].start() if index + 1 < len(marks) else len(text)
        body = plain(text[start:end])
        if heading and body and wanted(heading):
            found.append({"heading": heading[:24], "text": body})
    kept = []
    used = 0
    for section in found:
        if used >= BRIEF_LIMIT:
            break
        piece = clip(section["text"], min(SECTION_LIMIT, BRIEF_LIMIT - used))
        if len(piece) < 40:
            continue
        kept.append({"heading": section["heading"], "text": piece})
        used += len(piece)
    return kept


def titles_in_order() -> list[str]:
    events = []
    people = []
    seen = set()
    for path in SEEDS:
        for claim in read(path, {"claims": []})["claims"]:
            if claim.get("review_batch") in HELD_BATCHES:
                continue
            title = article_title((claim.get("citation") or {}).get("stable_url") or "")
            if not title or title in seen:
                continue
            seen.add(title)
            birth = (claim.get("event_title") or "").endswith("出生") or "出生于" in (claim.get("text") or "")
            (people if birth else events).append(title)
    return events + people


def save(rows: dict) -> None:
    OUTPUT.write_text(json.dumps(rows, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=400)
    args = parser.parse_args()
    existing = read(OUTPUT, {})
    pending = [title for title in titles_in_order() if title not in existing]
    batch = pending[: max(args.limit, 0)]
    print(f"briefs to fetch: {len(batch)} (already have {len(existing)}, waiting {len(pending)})", file=sys.stderr)
    for done, title in enumerate(batch, start=1):
        quoted = urllib.parse.quote(title.replace(" ", "_"))
        page = fetch_page(title)
        if page is None:
            print(f"  retry later: {title}", file=sys.stderr)
            continue
        sections = [] if page == {} else extract(page)
        existing[title] = {
            "url": "https://zh.wikipedia.org/wiki/" + quoted,
            "retrieved": date.today().isoformat(),
            "license": "CC BY-SA 4.0",
            "sections": sections,
        }
        if done % 20 == 0:
            print(f"  briefs {done}/{len(batch)}", file=sys.stderr)
            save(existing)
        time.sleep(0.35)
    save(existing)
    filled = sum(1 for row in existing.values() if row.get("sections"))
    print(f"briefs: {len(existing)} stored, {filled} with sections")


if __name__ == "__main__":
    main()
