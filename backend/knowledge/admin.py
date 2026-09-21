from django.contrib import admin, messages

from knowledge.models import (
    Citation,
    Claim,
    ClaimRevision,
    Edition,
    Event,
    HistoricalTimeSpan,
    Person,
    Polity,
    Region,
    Snapshot,
    Source,
    Topic,
)
from knowledge.models.enums import WorkflowState
from knowledge.services.publication import publish_claim


@admin.action(description="Move selected claims to review")
def move_to_review(_modeladmin, _request, queryset):
    queryset.filter(workflow_state=WorkflowState.DRAFT).update(
        workflow_state=WorkflowState.IN_REVIEW
    )


@admin.action(description="Approve selected reviewed claims")
def approve_reviewed(_modeladmin, _request, queryset):
    queryset.filter(workflow_state=WorkflowState.IN_REVIEW).update(
        workflow_state=WorkflowState.APPROVED
    )


@admin.action(description="Publish selected approved claims")
def publish_approved(modeladmin, request, queryset):
    published_count = 0
    for claim in queryset.filter(workflow_state=WorkflowState.APPROVED):
        publish_claim(
            claim=claim,
            reviewer=request.user,
            reason="Published through reviewed admin action.",
        )
        published_count += 1
    modeladmin.message_user(
        request,
        f"Published {published_count} claims.",
        level=messages.SUCCESS,
    )


@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = ["id", "short_text", "certainty", "workflow_state", "published_at"]
    list_filter = ["certainty", "workflow_state", "ai_generated", "topics", "regions"]
    search_fields = ["text"]
    filter_horizontal = ["regions", "polities", "topics", "citations"]
    readonly_fields = ["workflow_state", "published_at", "created_at", "updated_at"]
    actions = [move_to_review, approve_reviewed, publish_approved]

    @admin.display(description="Claim")
    def short_text(self, obj):
        return obj.text[:80]


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ["title", "kind", "license_status", "accessed_on"]
    list_filter = ["kind", "license_status"]
    search_fields = ["title", "creators", "canonical_url"]


@admin.register(Citation)
class CitationAdmin(admin.ModelAdmin):
    list_display = ["edition", "locator", "stable_url"]
    list_filter = ["edition__source__kind", "edition__source__license_status"]
    search_fields = ["edition__source__title", "locator", "quotation", "stable_url"]


@admin.register(Edition)
class EditionAdmin(admin.ModelAdmin):
    list_display = ["label", "source", "publisher", "publication_year"]
    list_filter = ["source__kind", "source__license_status", "publication_year"]
    search_fields = ["label", "publisher", "isbn", "external_id", "source__title"]


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ["title", "timespan"]
    list_filter = ["topics", "regions"]
    search_fields = ["title"]
    filter_horizontal = ["regions", "polities", "people", "topics"]


@admin.register(Snapshot)
class SnapshotAdmin(admin.ModelAdmin):
    list_display = ["label", "region", "polity", "dimension", "timespan"]
    list_filter = ["dimension", "region"]
    search_fields = ["label", "region__name", "region__slug"]


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "parent", "sort_order"]
    list_filter = ["parent"]
    search_fields = ["name", "slug"]


@admin.register(Polity)
class PolityAdmin(admin.ModelAdmin):
    list_display = ["name", "slug"]
    list_filter = ["regions"]
    search_fields = ["name", "slug"]
    filter_horizontal = ["regions"]


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ["name", "slug"]
    list_filter = ["slug"]
    search_fields = ["name", "slug"]


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ["name"]
    list_filter = ["events"]
    search_fields = ["name"]


admin.site.register([ClaimRevision, HistoricalTimeSpan])
