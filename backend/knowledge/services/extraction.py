import re

_CANDIDATE_LINE = re.compile(
    r"^(?P<start>-?\d+)(?:-(?P<end>-?\d+))?\|"
    r"(?P<region>[a-z0-9-]+)\|"
    r"(?P<topic>[a-z0-9-]+)\|"
    r"(?P<text>[^|]+)\|"
    r"(?P<url>https?://\S+)\|"
    r"(?P<locator>[^|]+)$"
)


def extract_candidates(text: str) -> list[dict]:
    candidates = []
    for raw_line in text.splitlines():
        match = _CANDIDATE_LINE.match(raw_line.strip())
        if match is None:
            continue
        start_year = int(match.group("start"))
        end_year = int(match.group("end") or start_year)
        candidates.append(
            {
                "text": match.group("text").strip(),
                "start_year": start_year,
                "end_year": end_year,
                "precision": "year" if start_year == end_year else "range",
                "display_text": str(start_year)
                if start_year == end_year
                else f"{start_year}–{end_year}",
                "region_slugs": [match.group("region")],
                "topic_slugs": [match.group("topic")],
                "certainty": "unverified",
                "citation": {
                    "edition_label": "文本抽取",
                    "locator": match.group("locator").strip(),
                    "stable_url": match.group("url"),
                },
            }
        )
    return candidates
