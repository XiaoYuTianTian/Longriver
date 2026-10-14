from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from knowledge.models import KnowledgeRelease
from knowledge.models.enums import ReleaseStatus
from knowledge.services.catalog import build_catalog


def current_release() -> KnowledgeRelease | None:
    return (
        KnowledgeRelease.objects.filter(status=ReleaseStatus.PUBLISHED).order_by("-version").first()
    )


@transaction.atomic
def publish_release(*, reviewer, note: str) -> KnowledgeRelease:
    if not reviewer.is_staff:
        raise PermissionDenied("Only staff reviewers can publish a knowledge release.")
    if not note.strip():
        raise ValidationError("Release requires a note.")

    latest = KnowledgeRelease.objects.select_for_update().order_by("-version").first()
    version = 1 if latest is None else latest.version + 1
    KnowledgeRelease.objects.filter(status=ReleaseStatus.PUBLISHED).update(
        status=ReleaseStatus.SUPERSEDED
    )
    return KnowledgeRelease.objects.create(
        version=version,
        status=ReleaseStatus.PUBLISHED,
        manifest=build_catalog(),
        note=note.strip(),
        created_by=reviewer,
    )


@transaction.atomic
def withdraw_release(*, release: KnowledgeRelease, reviewer, reason: str) -> KnowledgeRelease:
    if not reviewer.is_staff:
        raise PermissionDenied("Only staff reviewers can withdraw a knowledge release.")
    if not reason.strip():
        raise ValidationError("Withdrawal requires a reason.")

    locked = KnowledgeRelease.objects.select_for_update().get(pk=release.pk)
    if locked.status != ReleaseStatus.PUBLISHED:
        raise ValidationError("Only the current published release can be withdrawn.")
    locked.status = ReleaseStatus.WITHDRAWN
    locked.note = f"{locked.note}\n撤回：{reason.strip()}"
    locked.save(update_fields=["status", "note"])
    previous = (
        KnowledgeRelease.objects.filter(status=ReleaseStatus.SUPERSEDED)
        .order_by("-version")
        .first()
    )
    if previous is not None:
        previous.status = ReleaseStatus.PUBLISHED
        previous.save(update_fields=["status"])
    return locked


def build_package(*, since: int | None) -> dict:
    current = current_release()
    if current is None:
        return _empty_package()
    if since is None or since <= 0 or since > current.version:
        return _full_package(current)
    try:
        previous = KnowledgeRelease.objects.get(version=since)
    except KnowledgeRelease.DoesNotExist:
        return _full_package(current)
    if previous.version == current.version:
        package = _full_package(current)
        package["full"] = False
        package["claims"] = []
        package["removed_claim_ids"] = []
        return package
    return _delta_package(previous, current)


def _empty_package() -> dict:
    return {
        "version": 0,
        "full": True,
        "claims": [],
        "removed_claim_ids": [],
        "regions": [],
        "topics": [],
        "events": [],
        "snapshots": [],
        "people": [],
        "polities": [],
    }


def _full_package(release: KnowledgeRelease) -> dict:
    manifest = release.manifest
    return {
        "version": release.version,
        "full": True,
        "claims": manifest["claims"],
        "removed_claim_ids": [],
        "regions": manifest["regions"],
        "topics": manifest["topics"],
        "events": manifest["events"],
        "snapshots": manifest["snapshots"],
        "people": manifest["people"],
        "polities": manifest["polities"],
    }


def _delta_package(previous: KnowledgeRelease, current: KnowledgeRelease) -> dict:
    old_claims = {claim["id"]: claim for claim in previous.manifest["claims"]}
    new_claims = {claim["id"]: claim for claim in current.manifest["claims"]}
    changed = [claim for claim_id, claim in new_claims.items() if old_claims.get(claim_id) != claim]
    removed = [claim_id for claim_id in old_claims if claim_id not in new_claims]
    package = _full_package(current)
    package["full"] = False
    package["claims"] = changed
    package["removed_claim_ids"] = removed
    return package
