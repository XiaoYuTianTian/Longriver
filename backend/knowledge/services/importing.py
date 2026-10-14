from dataclasses import dataclass

from django.core.exceptions import ValidationError

from knowledge.models import (
    Citation,
    Claim,
    Edition,
    Event,
    HistoricalTimeSpan,
    Person,
    Region,
    Snapshot,
    Source,
    Topic,
)
from knowledge.models.enums import WorkflowState


@dataclass(frozen=True)
class ImportResult:
    created: int
    skipped: int


def import_open_data(payload: dict, *, ai_generated: bool = False) -> ImportResult:
    source_payload = payload["source"]
    source, _ = Source.objects.get_or_create(
        title=source_payload["title"],
        canonical_url=source_payload.get("canonical_url", ""),
        defaults={
            "kind": source_payload["kind"],
            "license_status": source_payload["license_status"],
            "license_note": source_payload.get("license_note", ""),
        },
    )
    if source_payload.get("license_note") and not source.license_note:
        source.license_note = source_payload["license_note"]
        source.save(update_fields=["license_note"])
    created = 0
    skipped = 0
    for claim_payload in payload["claims"]:
        if _existing_claim(claim_payload) is not None:
            skipped += 1
            continue
        _create_claim(claim_payload, source, ai_generated=ai_generated)
        created += 1
    return ImportResult(created=created, skipped=skipped)


def _existing_claim(payload: dict) -> Claim | None:
    region_slugs = set(payload["region_slugs"])
    matches = Claim.objects.filter(
        text=payload["text"],
        timespan__start_year=payload["start_year"],
        timespan__end_year=payload["end_year"],
    ).prefetch_related("regions")
    for claim in matches:
        if set(claim.regions.values_list("slug", flat=True)) == region_slugs:
            return claim
    return None


def _create_claim(payload: dict, source: Source, *, ai_generated: bool) -> Claim:
    regions = list(Region.objects.filter(slug__in=payload["region_slugs"]))
    if len(regions) != len(set(payload["region_slugs"])):
        raise ValidationError("Import region slug does not exist.")
    topics = list(Topic.objects.filter(slug__in=payload["topic_slugs"]))
    if len(topics) != len(set(payload["topic_slugs"])):
        raise ValidationError("Import topic slug does not exist.")

    timespan = HistoricalTimeSpan.objects.create(
        start_year=payload["start_year"],
        end_year=payload["end_year"],
        precision=payload["precision"],
        display_text=payload["display_text"],
    )
    event = None
    if payload.get("event_title"):
        event = Event.objects.filter(
            title=payload["event_title"],
            timespan__start_year=payload["start_year"],
            timespan__end_year=payload["end_year"],
        ).first()
        if event is None:
            event = Event.objects.create(title=payload["event_title"], timespan=timespan)
        event.regions.add(*regions)
        qids = payload.get("person_qids") or []
        for index, name in enumerate(payload.get("people") or []):
            if index < len(qids):
                person, _ = Person.objects.get_or_create(wikidata_id=qids[index], defaults={"name": name})
            else:
                person = Person.objects.filter(name=name).first() or Person.objects.create(name=name)
            event.people.add(person)
    snapshot = None
    if payload.get("snapshot_label"):
        snapshot = Snapshot.objects.filter(
            label=payload["snapshot_label"],
            region=regions[0],
            dimension=payload["snapshot_dimension"],
            timespan__start_year=payload["start_year"],
            timespan__end_year=payload["end_year"],
        ).first()
        if snapshot is None:
            snapshot = Snapshot.objects.create(
                label=payload["snapshot_label"],
                region=regions[0],
                dimension=payload["snapshot_dimension"],
                timespan=timespan,
            )
    claim = Claim.objects.create(
        text=payload["text"],
        timespan=timespan,
        certainty=payload["certainty"],
        workflow_state=WorkflowState.DRAFT,
        ai_generated=ai_generated,
        review_batch=payload.get("review_batch", ""),
        wikidata_id=payload.get("wikidata", ""),
        event=event,
        snapshot=snapshot,
    )
    claim.regions.add(*regions)
    claim.topics.add(*topics)
    citation_payload = payload["citation"]
    edition, _ = Edition.objects.get_or_create(
        source=source,
        label=citation_payload["edition_label"],
    )
    citation = Citation(
        edition=edition,
        locator=citation_payload.get("locator", ""),
        stable_url=citation_payload.get("stable_url", ""),
        quotation=citation_payload.get("quotation", ""),
    )
    citation.full_clean()
    citation.save()
    claim.citations.add(citation)
    return claim
