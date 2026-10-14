from django.db.models import Q, QuerySet

from knowledge.models import Claim
from knowledge.models.enums import WorkflowState


def search_published(*, query: str) -> QuerySet[Claim]:
    term = query.strip()
    if not term:
        return Claim.objects.none()
    return (
        Claim.objects.filter(workflow_state=WorkflowState.PUBLISHED)
        .filter(
            Q(text__icontains=term)
            | Q(event__title__icontains=term)
            | Q(regions__name__icontains=term)
            | Q(polities__name__icontains=term)
            | Q(topics__name__icontains=term)
            | Q(event__people__name__icontains=term)
        )
        .select_related("timespan", "event", "snapshot")
        .prefetch_related("regions", "topics", "polities", "citations__edition__source")
        .distinct()
        .order_by("id")
    )
