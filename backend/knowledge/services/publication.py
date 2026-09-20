from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from knowledge.models import Claim, ClaimRevision
from knowledge.models.enums import WorkflowState


@transaction.atomic
def publish_claim(*, claim: Claim, reviewer, reason: str) -> Claim:
    if not reviewer.is_staff:
        raise PermissionDenied("Only staff reviewers can publish claims.")
    if claim.workflow_state != WorkflowState.APPROVED:
        raise ValidationError("Claim must be approved before publication.")
    if not reason.strip():
        raise ValidationError("Publication requires a review reason.")
    if not claim.citations.exists():
        raise ValidationError("Published claim requires at least one citation.")
    for citation in claim.citations.all():
        citation.full_clean()

    previous_state = claim.workflow_state
    claim.workflow_state = WorkflowState.PUBLISHED
    claim.published_at = timezone.now()
    claim.save(update_fields=["workflow_state", "published_at", "updated_at"])
    ClaimRevision.objects.create(
        claim=claim,
        reviewer=reviewer,
        from_state=previous_state,
        to_state=WorkflowState.PUBLISHED,
        text_snapshot=claim.text,
        reason=reason.strip(),
    )
    return claim
