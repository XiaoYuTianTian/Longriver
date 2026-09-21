from unittest.mock import patch

import pytest
from django.contrib import admin
from django.contrib.messages.storage.fallback import FallbackStorage
from django.db.models import JSONField
from django.test import RequestFactory

from knowledge.admin import approve_reviewed, move_to_review, publish_approved
from knowledge.models import (
    Citation,
    Claim,
    ClaimRevision,
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
from tests.factories import add_citation, make_claim, make_staff_user, make_superuser

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

PUBLISHED_CLAIM_READONLY_FIELDS = [
    "text",
    "timespan",
    "certainty",
    "ai_generated",
    "regions",
    "polities",
    "topics",
    "event",
    "snapshot",
    "citations",
    "workflow_state",
    "published_at",
    "created_at",
    "updated_at",
]
GLOBAL_CLAIM_READONLY_FIELDS = [
    "workflow_state",
    "published_at",
    "created_at",
    "updated_at",
]
EDITABLE_CLAIM_CONTENT_FIELDS = [
    "text",
    "timespan",
    "certainty",
    "ai_generated",
    "regions",
    "polities",
    "topics",
    "event",
    "snapshot",
    "citations",
]


def make_admin_request(user, *, path="/admin/knowledge/claim/"):
    request = RequestFactory().post(path)
    request.user = user
    request.session = {}
    request._messages = FallbackStorage(request)
    return request


def recorded_messages(request):
    return [str(message.message) for message in request._messages]


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
def test_claim_admin_published_records_are_readonly_and_not_deletable():
    request = make_admin_request(make_superuser())
    claim_admin = admin.site._registry[Claim]
    published = make_claim(workflow_state="published")
    approved = make_claim(workflow_state="approved")

    published_readonly = set(claim_admin.get_readonly_fields(request, published))
    approved_readonly = set(claim_admin.get_readonly_fields(request, approved))

    assert set(PUBLISHED_CLAIM_READONLY_FIELDS) <= published_readonly
    assert set(GLOBAL_CLAIM_READONLY_FIELDS) <= approved_readonly
    assert set(EDITABLE_CLAIM_CONTENT_FIELDS).isdisjoint(approved_readonly)
    assert claim_admin.has_delete_permission(request, published) is False
    assert claim_admin.has_delete_permission(request, approved) is True


@pytest.mark.django_db
@pytest.mark.parametrize("workflow_state", ["draft", "in_review", "approved"])
def test_claim_admin_unpublished_records_keep_content_editable(workflow_state):
    request = make_admin_request(make_superuser())
    claim_admin = admin.site._registry[Claim]
    claim = make_claim(workflow_state=workflow_state)

    readonly = set(claim_admin.get_readonly_fields(request, claim))

    assert set(GLOBAL_CLAIM_READONLY_FIELDS) <= readonly
    assert set(EDITABLE_CLAIM_CONTENT_FIELDS).isdisjoint(readonly)
    assert claim_admin.has_delete_permission(request, claim) is True


@pytest.mark.django_db
def test_publish_approved_calls_publish_claim_instead_of_bulk_publishing():
    claim = make_claim(workflow_state="approved")
    request = make_admin_request(make_staff_user())
    modeladmin = admin.site._registry[Claim]

    with patch("knowledge.admin.publish_claim", wraps=publish_claim) as spy:
        publish_approved(modeladmin, request, Claim.objects.filter(pk=claim.pk))

    spy.assert_called_once()
    claim.refresh_from_db()
    assert claim.workflow_state == "approved"
    assert claim.published_at is None
    assert recorded_messages(request)


@pytest.mark.django_db
def test_publish_approved_reports_mixed_results_without_raising():
    valid = make_claim(workflow_state="approved")
    add_citation(valid)
    invalid = make_claim(workflow_state="approved")
    request = make_admin_request(make_staff_user())
    modeladmin = admin.site._registry[Claim]

    publish_approved(
        modeladmin,
        request,
        Claim.objects.filter(pk__in=[valid.pk, invalid.pk]).order_by("pk"),
    )

    valid.refresh_from_db()
    invalid.refresh_from_db()
    messages = recorded_messages(request)

    assert valid.workflow_state == "published"
    assert valid.published_at is not None
    assert invalid.workflow_state == "approved"
    assert invalid.published_at is None
    assert any("Published 1" in message for message in messages)
    assert any("Failed to publish 1" in message for message in messages)


@pytest.mark.django_db
def test_publish_approved_catches_permission_denied_without_raising(django_user_model):
    claim = make_claim(workflow_state="approved")
    add_citation(claim)
    request = make_admin_request(django_user_model.objects.create_user(username="reader"))
    modeladmin = admin.site._registry[Claim]

    publish_approved(modeladmin, request, Claim.objects.filter(pk=claim.pk))

    claim.refresh_from_db()
    assert claim.workflow_state == "approved"
    assert any("Failed to publish 1" in message for message in recorded_messages(request))


def test_source_admin_search_fields_exclude_json_fields():
    source_admin = admin.site._registry[Source]
    json_field_names = {
        field.name for field in Source._meta.get_fields() if isinstance(field, JSONField)
    }

    assert json_field_names
    assert json_field_names.isdisjoint(source_admin.search_fields)
    assert "creators" not in source_admin.search_fields
    assert "title" in source_admin.search_fields
    assert "canonical_url" in source_admin.search_fields


@pytest.mark.django_db
def test_claim_revision_admin_is_immutable_and_viewable():
    request = make_admin_request(make_superuser(), path="/admin/knowledge/claimrevision/")
    revision_admin = admin.site._registry[ClaimRevision]
    claim = make_claim()
    add_citation(claim)
    revision = ClaimRevision.objects.create(
        claim=claim,
        reviewer=make_staff_user(),
        from_state="approved",
        to_state="published",
        text_snapshot=claim.text,
        reason="Audit fixture",
    )
    field_names = {field.name for field in ClaimRevision._meta.fields}

    assert revision_admin.__class__ is not admin.ModelAdmin
    assert field_names <= set(revision_admin.get_readonly_fields(request, revision))
    assert revision_admin.has_add_permission(request) is False
    assert revision_admin.has_change_permission(request, revision) is False
    assert revision_admin.has_delete_permission(request, revision) is False
    assert revision_admin.has_view_permission(request, revision) is True
    assert revision_admin.has_module_permission(request) is True
