import pytest
from django.urls import reverse

from knowledge.models import ContentFeedback
from knowledge.services.publication import publish_claim
from tests.factories import add_citation, make_claim, make_staff_user


@pytest.mark.django_db
def test_feedback_api_stores_claim_correction(client):
    reviewer = make_staff_user()
    claim = make_claim()
    add_citation(claim)
    publish_claim(claim=claim, reviewer=reviewer, reason="Verified")

    response = client.post(
        reverse("knowledge_api:feedback"),
        {"claim_id": claim.id, "message": "年份应标为约1520年"},
        content_type="application/json",
    )

    assert response.status_code == 201
    feedback = ContentFeedback.objects.get()
    assert feedback.claim_id == claim.id
    assert feedback.status == "open"
    assert feedback.message == "年份应标为约1520年"


@pytest.mark.django_db
def test_feedback_api_rejects_blank_message(client):
    response = client.post(
        reverse("knowledge_api:feedback"),
        {"message": "  "},
        content_type="application/json",
    )

    assert response.status_code == 400
    assert ContentFeedback.objects.count() == 0
