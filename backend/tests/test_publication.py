import pytest
from django.core.exceptions import PermissionDenied, ValidationError

from knowledge.models import ClaimRevision
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
    revision = ClaimRevision.objects.get(claim=published)
    assert revision.reviewer == reviewer
    assert revision.reason == "Citation and wording verified"
