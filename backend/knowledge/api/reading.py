from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from knowledge.models import Claim, Event, Person, Polity, Region, Snapshot
from knowledge.models.enums import WorkflowState
from knowledge.services.catalog import serialize_claim


class PublicReadView(APIView):
    authentication_classes = []
    permission_classes = []


class EventDetailView(PublicReadView):
    def get(self, request, pk):
        event = get_object_or_404(
            Event.objects.select_related("timespan").prefetch_related("regions", "people"),
            pk=pk,
            claims__workflow_state=WorkflowState.PUBLISHED,
        )
        return Response(_event_payload(event))


class SnapshotDetailView(PublicReadView):
    def get(self, request, pk):
        snapshot = get_object_or_404(
            Snapshot.objects.select_related("timespan", "region", "polity"),
            pk=pk,
            claims__workflow_state=WorkflowState.PUBLISHED,
        )
        return Response(_snapshot_payload(snapshot))


class PersonDetailView(PublicReadView):
    def get(self, request, pk):
        person = get_object_or_404(
            Person.objects.filter(
                events__claims__workflow_state=WorkflowState.PUBLISHED
            ).distinct(),
            pk=pk,
        )
        claims = Claim.objects.filter(
            event__people=person,
            workflow_state=WorkflowState.PUBLISHED,
        )
        return Response(
            {
                "id": person.id,
                "name": person.name,
                "claims": _published_claims(claims),
            }
        )


class PolityDetailView(PublicReadView):
    def get(self, request, pk):
        polity = get_object_or_404(
            Polity.objects.filter(claims__workflow_state=WorkflowState.PUBLISHED).distinct(),
            pk=pk,
        )
        return Response(
            {
                "id": polity.id,
                "name": polity.name,
                "slug": polity.slug,
                "claims": _published_claims(
                    polity.claims.filter(workflow_state=WorkflowState.PUBLISHED)
                ),
            }
        )


class RegionDetailView(PublicReadView):
    def get(self, request, pk):
        region = get_object_or_404(Region, pk=pk)
        return Response(
            {
                "id": region.id,
                "name": region.name,
                "slug": region.slug,
                "claims": _published_claims(
                    region.claims.filter(workflow_state=WorkflowState.PUBLISHED)
                ),
            }
        )


def _published_claims(claims) -> list[dict]:
    claims = claims.select_related("timespan", "event", "snapshot").prefetch_related(
        "regions",
        "topics",
        "polities",
        "citations__edition__source",
    )
    return [serialize_claim(claim) for claim in claims.order_by("id").distinct()]


def _event_payload(event: Event) -> dict:
    return {
        "id": event.id,
        "title": event.title,
        "time_label": event.timespan.display_text,
        "start_year": event.timespan.start_year,
        "end_year": event.timespan.end_year,
        "regions": [
            {"id": region.id, "slug": region.slug, "name": region.name}
            for region in event.regions.all()
        ],
        "people": [{"id": person.id, "name": person.name} for person in event.people.all()],
        "claims": _published_claims(event.claims.filter(workflow_state=WorkflowState.PUBLISHED)),
    }


def _snapshot_payload(snapshot: Snapshot) -> dict:
    return {
        "id": snapshot.id,
        "label": snapshot.label,
        "dimension": snapshot.dimension,
        "time_label": snapshot.timespan.display_text,
        "start_year": snapshot.timespan.start_year,
        "end_year": snapshot.timespan.end_year,
        "region": {
            "id": snapshot.region_id,
            "slug": snapshot.region.slug,
            "name": snapshot.region.name,
        },
        "claims": _published_claims(snapshot.claims.filter(workflow_state=WorkflowState.PUBLISHED)),
    }
