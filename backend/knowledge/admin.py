from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError

from knowledge.models import (
    Citation,
    Claim,
    ClaimRevision,
    ContentFeedback,
    Edition,
    Event,
    HistoricalTimeSpan,
    KnowledgeRelease,
    MediaAsset,
    Person,
    Polity,
    Region,
    Snapshot,
    Source,
    Topic,
)
from knowledge.models.enums import FeedbackStatus, ReleaseStatus, WorkflowState
from knowledge.services.publication import publish_claim, withdraw_claim
from knowledge.services.releases import publish_release, withdraw_release


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
    list_display = ["id", "short_text", "certainty", "workflow_state", "review_batch", "published_at"]
    list_filter = ["review_batch", "certainty", "workflow_state", "ai_generated", "topics"]
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
    list_display = ["name", "slug", "level", "parent", "sort_order"]
    list_filter = ["level"]
    search_fields = ["name", "slug", "wikidata_id"]
    raw_id_fields = ["parent", "image"]


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
    list_display = ["name", "birth_year", "death_year", "primary_region", "wikidata_id"]
    list_filter = ["primary_region__level"]
    search_fields = ["name", "wikidata_id"]
    raw_id_fields = ["primary_region", "image"]


@admin.register(MediaAsset)
class MediaAssetAdmin(admin.ModelAdmin):
    list_display = ["commons_title", "license", "author"]
    list_filter = ["license"]
    search_fields = ["commons_title", "author"]


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


@admin.action(description="Withdraw selected published claims")
def withdraw_published(modeladmin, request, queryset):
    withdrawn_count = 0
    failed_count = 0
    for claim in queryset.filter(workflow_state=WorkflowState.PUBLISHED):
        try:
            withdraw_claim(
                claim=claim, reviewer=request.user, reason="Withdrawn through admin action."
            )
        except (ValidationError, PermissionDenied):
            failed_count += 1
            continue
        withdrawn_count += 1
    if withdrawn_count:
        modeladmin.message_user(
            request, f"Withdrew {withdrawn_count} claims.", level=messages.SUCCESS
        )
    if failed_count:
        modeladmin.message_user(
            request, f"Failed to withdraw {failed_count} claims.", level=messages.ERROR
        )


ClaimAdmin.actions = [move_to_review, approve_reviewed, publish_approved, withdraw_published]


@admin.action(description="Publish a knowledge release from current claims")
def publish_current_release(modeladmin, request, queryset):
    try:
        release = publish_release(reviewer=request.user, note="Published through admin action.")
    except (ValidationError, PermissionDenied) as error:
        modeladmin.message_user(request, str(error), level=messages.ERROR)
        return
    modeladmin.message_user(
        request, f"Published release {release.version}.", level=messages.SUCCESS
    )


@admin.action(description="Withdraw selected current release")
def withdraw_current_release(modeladmin, request, queryset):
    failed = 0
    withdrawn = 0
    for release in queryset.filter(status=ReleaseStatus.PUBLISHED):
        try:
            withdraw_release(
                release=release, reviewer=request.user, reason="Withdrawn through admin."
            )
        except (ValidationError, PermissionDenied):
            failed += 1
            continue
        withdrawn += 1
    if withdrawn:
        modeladmin.message_user(request, f"Withdrew {withdrawn} releases.", level=messages.SUCCESS)
    if failed:
        modeladmin.message_user(
            request, f"Failed to withdraw {failed} releases.", level=messages.ERROR
        )


@admin.register(KnowledgeRelease)
class KnowledgeReleaseAdmin(admin.ModelAdmin):
    list_display = ["version", "status", "created_by", "created_at"]
    list_filter = ["status"]
    search_fields = ["note"]
    readonly_fields = ["version", "status", "manifest", "note", "created_by", "created_at"]
    actions = [publish_current_release, withdraw_current_release]

    def has_add_permission(self, request):
        return False


@admin.action(description="Mark selected feedback resolved")
def resolve_feedback(_modeladmin, _request, queryset):
    queryset.filter(status=FeedbackStatus.OPEN).update(status=FeedbackStatus.RESOLVED)


@admin.register(ContentFeedback)
class ContentFeedbackAdmin(admin.ModelAdmin):
    list_display = ["id", "claim", "status", "created_at"]
    list_filter = ["status"]
    search_fields = ["message"]
    readonly_fields = ["claim", "message", "created_at"]
    actions = [resolve_feedback]
