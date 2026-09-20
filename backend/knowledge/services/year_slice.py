from collections.abc import Sequence

from django.db.models import QuerySet

from knowledge.models import Claim
from knowledge.models.enums import WorkflowState


def select_year_slice(
    *,
    year: int,
    region_ids: Sequence[int] = (),
    topic_slugs: Sequence[str] = (),
) -> QuerySet[Claim]:
    claims = (
        Claim.objects.filter(
            workflow_state=WorkflowState.PUBLISHED,
            timespan__start_year__lte=year,
            timespan__end_year__gte=year,
        )
        .select_related("timespan", "event", "snapshot")
        .prefetch_related(
            "regions",
            "topics",
            "citations__edition__source",
        )
    )
    if region_ids:
        claims = claims.filter(regions__id__in=region_ids)
    if topic_slugs:
        claims = claims.filter(topics__slug__in=topic_slugs)
    return claims.distinct().order_by(
        "timespan__start_year",
        "timespan__end_year",
        "id",
    )
