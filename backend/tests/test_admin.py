from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.contrib import admin
from django.core.exceptions import ValidationError

from knowledge.admin import approve_reviewed, move_to_review, publish_approved
from knowledge.models import (
    Citation,
    Claim,
    Edition,
    Event,
    Person,
    Polity,
    Region,
    Snapshot,
    Source,
    Topic,
)
from knowledge.services.publication import publish_claim
from tests.factories import make_claim, make_staff_user

EDITORIAL_MODELS = [
    Claim,
    Citation,
    Source,
    Edition,
    Event,
    Snapshot,
    Region,
    Polity,
    Topic,
    Person,
]


def test_editorial_models_have_searchable_filterable_admin():
    for model in EDITORIAL_MODELS:
        assert model in admin.site._registry, f"{model.__name__} is not registered"
        model_admin = admin.site._registry[model]
        assert model_admin.__class__ is not admin.ModelAdmin, (
            f"{model.__name__} uses a bare ModelAdmin"
        )
        assert model_admin.search_fields, f"{model.__name__} is missing search_fields"
        assert model_admin.list_filter, f"{model.__name__} is missing list_filter"

    claim_admin = admin.site._registry[Claim]
    assert "workflow_state" in claim_admin.readonly_fields
    assert publish_approved in claim_admin.actions
    assert move_to_review in claim_admin.actions
    assert approve_reviewed in claim_admin.actions


@pytest.mark.django_db
def test_move_to_review_only_transitions_draft_claims():
    draft = make_claim(workflow_state="draft")
    in_review = make_claim(workflow_state="in_review")
    approved = make_claim(workflow_state="approved")
    published = make_claim(workflow_state="published")
    withdrawn = make_claim(workflow_state="withdrawn")

    move_to_review(None, None, Claim.objects.all())

    draft.refresh_from_db()
    in_review.refresh_from_db()
    approved.refresh_from_db()
    published.refresh_from_db()
    withdrawn.refresh_from_db()

    assert draft.workflow_state == "in_review"
    assert in_review.workflow_state == "in_review"
    assert approved.workflow_state == "approved"
    assert published.workflow_state == "published"
    assert withdrawn.workflow_state == "withdrawn"


@pytest.mark.django_db
def test_approve_reviewed_only_transitions_in_review_claims():
    draft = make_claim(workflow_state="draft")
    in_review = make_claim(workflow_state="in_review")
    approved = make_claim(workflow_state="approved")
    published = make_claim(workflow_state="published")
    withdrawn = make_claim(workflow_state="withdrawn")

    approve_reviewed(None, None, Claim.objects.all())

    draft.refresh_from_db()
    in_review.refresh_from_db()
    approved.refresh_from_db()
    published.refresh_from_db()
    withdrawn.refresh_from_db()

    assert draft.workflow_state == "draft"
    assert in_review.workflow_state == "approved"
    assert approved.workflow_state == "approved"
    assert published.workflow_state == "published"
    assert withdrawn.workflow_state == "withdrawn"


@pytest.mark.django_db
def test_publish_approved_calls_publish_claim_instead_of_bulk_publishing():
    claim = make_claim(workflow_state="approved")
    request = SimpleNamespace(user=make_staff_user())
    modeladmin = admin.site._registry[Claim]

    with (
        patch("knowledge.admin.publish_claim", wraps=publish_claim) as spy,
        pytest.raises(ValidationError, match="citation"),
    ):
        publish_approved(modeladmin, request, Claim.objects.filter(pk=claim.pk))

    spy.assert_called_once()
    claim.refresh_from_db()
    assert claim.workflow_state == "approved"
    assert claim.published_at is None
