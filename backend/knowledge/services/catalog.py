import json

from django.core.serializers.json import DjangoJSONEncoder

from knowledge.api.serializers import ClaimSerializer
from knowledge.models import Claim, Event, Person, Polity, Region, Snapshot, Topic
from knowledge.models.enums import WorkflowState


def _plain(value):
    return json.loads(json.dumps(value, cls=DjangoJSONEncoder))


def serialize_claim(claim: Claim) -> dict:
    data = _plain(ClaimSerializer(claim).data)
    data.update(
        {
            "start_year": claim.timespan.start_year,
            "end_year": claim.timespan.end_year,
            "precision": claim.timespan.precision,
            "region_ids": [region.id for region in claim.regions.all()],
            "topic_slugs": [topic.slug for topic in claim.topics.all()],
            "polity_ids": [polity.id for polity in claim.polities.all()],
        }
    )
    return data


def build_catalog() -> dict:
    claims = list(
        Claim.objects.filter(workflow_state=WorkflowState.PUBLISHED)
        .select_related("timespan", "event", "snapshot")
        .prefetch_related(
            "regions",
            "topics",
            "polities",
            "citations__edition__source",
            "event__regions",
            "event__people",
            "event__timespan",
            "snapshot__region",
            "snapshot__polity",
            "snapshot__timespan",
        )
        .order_by("id")
    )
    serialized_claims = [serialize_claim(claim) for claim in claims]
    event_ids = {claim.event_id for claim in claims if claim.event_id}
    snapshot_ids = {claim.snapshot_id for claim in claims if claim.snapshot_id}
    person_ids = set(
        Person.objects.filter(events__claims__workflow_state=WorkflowState.PUBLISHED)
        .values_list("id", flat=True)
        .distinct()
    )
    polity_ids = {polity_id for claim in serialized_claims for polity_id in claim["polity_ids"]}
    return {
        "claims": serialized_claims,
        "regions": [
            {
                "id": region.id,
                "slug": region.slug,
                "name": region.name,
                "sort_order": region.sort_order,
            }
            for region in Region.objects.all()
        ],
        "topics": [{"slug": topic.slug, "name": topic.name} for topic in Topic.objects.all()],
        "events": [
            _serialize_event(event)
            for event in Event.objects.filter(id__in=event_ids).order_by("id")
        ],
        "snapshots": [
            _serialize_snapshot(snapshot)
            for snapshot in Snapshot.objects.filter(id__in=snapshot_ids).order_by("id")
        ],
        "people": [
            {"id": person.id, "name": person.name}
            for person in Person.objects.filter(id__in=person_ids).order_by("id")
        ],
        "polities": [
            {"id": polity.id, "name": polity.name, "slug": polity.slug}
            for polity in Polity.objects.filter(id__in=polity_ids).order_by("id")
        ],
    }


def _serialize_event(event: Event) -> dict:
    return {
        "id": event.id,
        "title": event.title,
        "time_label": event.timespan.display_text,
        "start_year": event.timespan.start_year,
        "end_year": event.timespan.end_year,
        "region_ids": list(event.regions.values_list("id", flat=True)),
        "person_ids": list(event.people.values_list("id", flat=True)),
    }


def _serialize_snapshot(snapshot: Snapshot) -> dict:
    return {
        "id": snapshot.id,
        "label": snapshot.label,
        "region_id": snapshot.region_id,
        "polity_id": snapshot.polity_id,
        "dimension": snapshot.dimension,
        "time_label": snapshot.timespan.display_text,
        "start_year": snapshot.timespan.start_year,
        "end_year": snapshot.timespan.end_year,
    }
