from unittest.mock import patch

import pytest
from django.core.exceptions import PermissionDenied, ValidationError

from knowledge.models import Citation, Claim, ClaimRevision, Edition, Source
from knowledge.services.publication import publish_claim
from tests.factories import add_citation, make_claim, make_staff_user


@pytest.mark.django_db
def test_publish_claim_requires_citation():
    claim = make_claim()
    reviewer = make_staff_user()

    with pytest.raises(ValidationError, match="citation"):
        publish_claim(claim=claim, reviewer=reviewer, reason="Reviewed against source")


@pytest.mark.django_db
def test_publish_claim_requires_staff_reviewer(django_user_model):
    claim = make_claim()
    add_citation(claim)
    reviewer = django_user_model.objects.create_user(username="reader")

    with pytest.raises(PermissionDenied):
        publish_claim(claim=claim, reviewer=reviewer, reason="Not authorized")


@pytest.mark.django_db
def test_publish_claim_requires_approved_claim():
    claim = make_claim(workflow_state="draft")
    add_citation(claim)
    reviewer = make_staff_user()

    with pytest.raises(ValidationError, match="approved"):
        publish_claim(claim=claim, reviewer=reviewer, reason="Reviewed against source")


@pytest.mark.django_db
def test_publish_claim_requires_non_blank_reason():
    claim = make_claim()
    add_citation(claim)
    reviewer = make_staff_user()

    with pytest.raises(ValidationError, match="reason"):
        publish_claim(claim=claim, reviewer=reviewer, reason="   ")


@pytest.mark.django_db
def test_publish_claim_rejects_whitespace_only_citation_locator():
    claim = make_claim()
    source = Source.objects.create(
        title="Whitespace citation source",
        kind="book",
        license_status="metadata_only",
    )
    edition = Edition.objects.create(source=source, label="Whitespace edition")
    citation = Citation.objects.create(edition=edition, locator="   ", stable_url="")
    claim.citations.add(citation)
    reviewer = make_staff_user()

    with pytest.raises(ValidationError, match="Citation requires"):
        publish_claim(claim=claim, reviewer=reviewer, reason="Reviewed against source")


@pytest.mark.django_db
def test_publish_claim_records_revision():
    claim = make_claim()
    add_citation(claim)
    reviewer = make_staff_user()

    published = publish_claim(
        claim=claim,
        reviewer=reviewer,
        reason="Citation and wording verified",
    )

    assert published.workflow_state == "published"
    assert published.published_at is not None
    published.refresh_from_db()
    assert published.workflow_state == "published"
    assert published.published_at is not None
    revision = ClaimRevision.objects.get(claim=published)
    assert revision.reviewer == reviewer
    assert revision.from_state == "approved"
    assert revision.to_state == "published"
    assert revision.text_snapshot == "Synthetic historical claim for automated tests."
    assert revision.reason == "Citation and wording verified"


@pytest.mark.django_db
def test_publish_claim_rejects_stale_approved_instance_after_publication():
    claim = make_claim()
    add_citation(claim)
    reviewer = make_staff_user()
    first_instance = Claim.objects.get(pk=claim.pk)
    stale_instance = Claim.objects.get(pk=claim.pk)

    publish_claim(
        claim=first_instance,
        reviewer=reviewer,
        reason="Citation and wording verified",
    )

    with pytest.raises(ValidationError, match="approved"):
        publish_claim(
            claim=stale_instance,
            reviewer=reviewer,
            reason="Stale publish attempt",
        )

    assert ClaimRevision.objects.filter(claim_id=claim.pk).count() == 1


@pytest.mark.django_db
def test_publish_claim_rolls_back_state_when_revision_creation_fails():
    claim = make_claim()
    add_citation(claim)
    reviewer = make_staff_user()

    with (
        patch(
            "knowledge.services.publication.ClaimRevision.objects.create",
            side_effect=RuntimeError("revision write failed"),
        ),
        pytest.raises(RuntimeError, match="revision write failed"),
    ):
        publish_claim(
            claim=claim,
            reviewer=reviewer,
            reason="Citation and wording verified",
        )

    claim.refresh_from_db()
    assert claim.workflow_state == "approved"
    assert claim.published_at is None
    assert ClaimRevision.objects.filter(claim=claim).count() == 0
