from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError

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
    failed_count = 0
    for claim in queryset.filter(workflow_state=WorkflowState.APPROVED):
        try:
            publish_claim(
                claim=claim,
                reviewer=request.user,
                reason="Published through reviewed admin action.",
            )
        except (ValidationError, PermissionDenied):
            failed_count += 1
            continue
        published_count += 1
    if published_count:
        modeladmin.message_user(
            request,
            f"Published {published_count} claims.",
            level=messages.SUCCESS,
        )
    if failed_count:
        modeladmin.message_user(
            request,
            f"Failed to publish {failed_count} claims.",
            level=messages.ERROR,
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

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if obj is not None and obj.workflow_state == WorkflowState.PUBLISHED:
            for field in [
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
            ]:
                if field not in readonly:
                    readonly.append(field)
        return readonly

    def has_delete_permission(self, request, obj=None):
        if obj is not None and obj.workflow_state == WorkflowState.PUBLISHED:
            return False
        return super().has_delete_permission(request, obj)

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions

    def delete_queryset(self, request, queryset):
        super().delete_queryset(
            request,
            queryset.exclude(workflow_state=WorkflowState.PUBLISHED),
        )


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ["title", "kind", "license_status", "accessed_on"]
    list_filter = ["kind", "license_status"]
    search_fields = ["title", "canonical_url"]


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


@admin.register(ClaimRevision)
class ClaimRevisionAdmin(admin.ModelAdmin):
    list_display = ["id", "claim", "reviewer", "from_state", "to_state", "created_at"]
    list_filter = ["from_state", "to_state"]
    search_fields = ["reason", "text_snapshot"]
    readonly_fields = [field.name for field in ClaimRevision._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(HistoricalTimeSpan)
