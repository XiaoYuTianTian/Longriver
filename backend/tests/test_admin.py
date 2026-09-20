from django.contrib import admin

from knowledge.admin import publish_approved
from knowledge.models import Citation, Claim, Event, Region, Snapshot, Source


def test_core_models_are_registered_in_admin():
    for model in [Claim, Citation, Source, Event, Snapshot, Region]:
        assert model in admin.site._registry

    claim_admin = admin.site._registry[Claim]
    assert "workflow_state" in claim_admin.readonly_fields
    assert publish_approved in claim_admin.actions
