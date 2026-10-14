from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from knowledge.models import Claim, ClaimRevision
from knowledge.models.enums import WorkflowState


@transaction.atomic
def publish_claim(*, claim: Claim, reviewer, reason: str) -> Claim:
    if not reviewer.is_staff:
        raise PermissionDenied("Only staff reviewers can publish claims.")

    locked_claim = Claim.objects.select_for_update().get(pk=claim.pk)
    if locked_claim.workflow_state != WorkflowState.APPROVED:
        raise ValidationError("Claim must be approved before publication.")
    if not reason.strip():
        raise ValidationError("Publication requires a review reason.")
    if not locked_claim.citations.exists():
        raise ValidationError("Published claim requires at least one citation.")
    for citation in locked_claim.citations.all():
        citation.full_clean()

    previous_state = locked_claim.workflow_state
    locked_claim.workflow_state = WorkflowState.PUBLISHED
    locked_claim.published_at = timezone.now()
    locked_claim.save(update_fields=["workflow_state", "published_at", "updated_at"])
    ClaimRevision.objects.create(
        claim=locked_claim,
        reviewer=reviewer,
        from_state=previous_state,
        to_state=WorkflowState.PUBLISHED,
        text_snapshot=locked_claim.text,
        reason=reason.strip(),
    )
    return locked_claim


@transaction.atomic
def withdraw_claim(*, claim: Claim, reviewer, reason: str) -> Claim:
    if not reviewer.is_staff:
        raise PermissionDenied("Only staff reviewers can withdraw claims.")
    if not reason.strip():
        raise ValidationError("Withdrawal requires a reason.")

    locked_claim = Claim.objects.select_for_update().get(pk=claim.pk)
    if locked_claim.workflow_state != WorkflowState.PUBLISHED:
        raise ValidationError("Only a published claim can be withdrawn.")

    previous_state = locked_claim.workflow_state
    locked_claim.workflow_state = WorkflowState.WITHDRAWN
    locked_claim.save(update_fields=["workflow_state", "updated_at"])
    ClaimRevision.objects.create(
        claim=locked_claim,
        reviewer=reviewer,
        from_state=previous_state,
        to_state=WorkflowState.WITHDRAWN,
        text_snapshot=locked_claim.text,
        reason=reason.strip(),
    )
    return locked_claim
