import json
from pathlib import Path

import pytest
from django.core.management import call_command

from knowledge.models import Claim, Person, Region
from knowledge.services.extraction import extract_candidates
from knowledge.services.importing import import_open_data

OPEN_DATA = {
    "source": {
        "title": "开放测试来源",
        "kind": "dataset",
        "license_status": "metadata_only",
        "canonical_url": "https://example.test/source",
    },
    "claims": [
        {
            "text": "测试陈述",
            "start_year": 1520,
            "end_year": 1520,
            "precision": "year",
            "display_text": "1520",
            "region_slugs": ["europe"],
            "topic_slugs": ["politics"],
            "certainty": "inferred",
            "event_title": "测试事件",
            "snapshot_label": "欧洲政治状态",
            "snapshot_dimension": "politics",
            "citation": {
                "edition_label": "测试版本",
                "locator": "条目",
                "stable_url": "https://example.test/source",
            },
        }
    ],
}


@pytest.mark.django_db
def test_open_data_import_creates_draft_and_is_idempotent():
    call_command("load_reference_data")

    first = import_open_data(OPEN_DATA)
    second = import_open_data(OPEN_DATA)

    claim = Claim.objects.get()
    assert first.created == 1
    assert second.created == 0
    assert second.skipped == 1
    assert claim.workflow_state == "draft"
    assert claim.ai_generated is False
    assert claim.event.title == "测试事件"
    assert claim.snapshot.label == "欧洲政治状态"
    assert claim.citations.get().stable_url == "https://example.test/source"


@pytest.mark.django_db
def test_seed_file_imports_four_drafts():
    call_command("load_reference_data")
    path = Path(__file__).parents[2] / "content" / "seed" / "early-modern.json"

    result = import_open_data(json.loads(path.read_text(encoding="utf-8")))

    assert result.created == 4
    assert Claim.objects.filter(workflow_state="draft").count() == 4
    assert Claim.objects.get(text__contains="九十五条").event.people.filter(name="马丁·路德").exists()


@pytest.mark.django_db
def test_skeleton_seed_covers_four_regions_as_unverified_drafts():
    call_command("load_reference_data")
    root = Path(__file__).parents[2] / "content" / "seed"
    early = json.loads((root / "early-modern.json").read_text(encoding="utf-8"))
    skeleton = json.loads((root / "early-modern-skeleton.json").read_text(encoding="utf-8"))

    import_open_data(early)
    result = import_open_data(skeleton)

    claims = Claim.objects.prefetch_related("regions", "citations")
    region_slugs = {slug for claim in claims for slug in claim.regions.values_list("slug", flat=True)}
    assert result.created == len(skeleton["claims"])
    assert result.created >= 40
    assert "sekigahara" in region_slugs
    assert "beijing" in region_slugs
    roots = set()
    for claim in claims:
        for region in claim.regions.all():
            while region.parent_id is not None:
                region = region.parent
            roots.add(region.slug)
    assert roots <= {"east-asia", "west-asia-north-africa", "europe", "americas"}
    assert claims.filter(workflow_state="draft", certainty="unverified").count() == result.created
    assert all(claim.citations.get().stable_url.startswith("https://") for claim in claims)
    assert Claim.objects.get(text__contains="关原").event.people.filter(name="德川家康").exists()


@pytest.mark.django_db
def test_long_span_seed_reaches_before_the_common_era():
    call_command("load_reference_data")
    path = Path(__file__).parents[2] / "content" / "seed" / "long-span.json"
    payload = json.loads(path.read_text(encoding="utf-8"))

    result = import_open_data(payload)

    assert result.created == len(payload["claims"])
    assert Claim.objects.filter(timespan__start_year__lt=0).exists()


@pytest.mark.django_db
def test_wikidata_seed_imports_as_unverified_batches_with_person_ids():
    call_command("load_reference_data")
    path = Path(__file__).parents[2] / "content" / "seed" / "wikidata.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    slugs = {slug for claim in payload["claims"] for slug in claim["region_slugs"]}
    assert slugs <= set(Region.objects.values_list("slug", flat=True))

    sample = {"source": payload["source"], "claims": payload["claims"][:60]}
    sample["claims"].append({**sample["claims"][0], "text": sample["claims"][0]["text"] + "（复核）"})
    result = import_open_data(sample)

    assert result.created == len(sample["claims"])
    claims = Claim.objects.all()
    assert claims.filter(workflow_state="draft", certainty="unverified").count() == result.created
    assert set(claims.values_list("review_batch", flat=True)) <= {"wikidata-1", "china-1949-plus"}
    assert all(claim.wikidata_id.startswith("Q") for claim in claims)
    first = sample["claims"][0]
    assert Person.objects.filter(wikidata_id=first["person_qids"][0]).count() == 1


@pytest.mark.django_db
def test_wikidata_places_hang_under_known_regions():
    call_command("load_reference_data")
    roots = set()
    for region in Region.objects.filter(wikidata_id__startswith="Q").select_related("parent")[:400]:
        while region.parent_id is not None:
            region = region.parent
        roots.add(region.slug)
    assert roots <= {
        "east-asia", "west-asia-north-africa", "europe", "americas",
        "south-asia", "southeast-asia", "central-asia", "africa", "oceania",
    }


def test_extract_candidates_reads_structured_lines():
    text = "1517-1517|europe|culture|宗教改革展开|https://example.test/luther|条目正文\n忽略这一行"

    candidates = extract_candidates(text)

    assert candidates == [
        {
            "text": "宗教改革展开",
            "start_year": 1517,
            "end_year": 1517,
            "precision": "year",
            "display_text": "1517",
            "region_slugs": ["europe"],
            "topic_slugs": ["culture"],
            "certainty": "unverified",
            "citation": {
                "edition_label": "文本抽取",
                "locator": "条目正文",
                "stable_url": "https://example.test/luther",
            },
        }
    ]
