from django.conf import settings
from django.db import models

from .enums import ClaimCertainty, SnapshotDimension, WorkflowState


class Topic(models.Model):
    name = models.CharField(max_length=128)
    slug = models.SlugField(max_length=128, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Person(models.Model):
    name = models.CharField(max_length=160)
    alternate_names = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["name", "id"]

    def __str__(self):
        return self.name


class Event(models.Model):
    title = models.CharField(max_length=256)
    timespan = models.ForeignKey(
        "HistoricalTimeSpan",
        on_delete=models.PROTECT,
        related_name="events",
    )
    regions = models.ManyToManyField("Region", related_name="events")
    polities = models.ManyToManyField("Polity", related_name="events", blank=True)
    people = models.ManyToManyField(Person, related_name="events", blank=True)
    topics = models.ManyToManyField(Topic, related_name="events", blank=True)

    class Meta:
        ordering = ["timespan__start_year", "title", "id"]

    def __str__(self):
        return self.title


class Snapshot(models.Model):
    label = models.CharField(max_length=256)
    region = models.ForeignKey("Region", on_delete=models.PROTECT, related_name="snapshots")
    polity = models.ForeignKey(
        "Polity",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="snapshots",
    )
    timespan = models.ForeignKey(
        "HistoricalTimeSpan",
        on_delete=models.PROTECT,
        related_name="snapshots",
    )
    dimension = models.CharField(max_length=24, choices=SnapshotDimension.choices)

    class Meta:
        ordering = ["timespan__start_year", "region__sort_order", "dimension", "id"]

    def __str__(self):
        return self.label


class Claim(models.Model):
    text = models.TextField()
    timespan = models.ForeignKey(
        "HistoricalTimeSpan",
        on_delete=models.PROTECT,
        related_name="claims",
    )
    certainty = models.CharField(max_length=24, choices=ClaimCertainty.choices)
    workflow_state = models.CharField(
        max_length=24,
        choices=WorkflowState.choices,
        default=WorkflowState.DRAFT,
    )
    ai_generated = models.BooleanField(default=False)
    regions = models.ManyToManyField("Region", related_name="claims")
    polities = models.ManyToManyField("Polity", related_name="claims", blank=True)
    topics = models.ManyToManyField(Topic, related_name="claims", blank=True)
    event = models.ForeignKey(
        Event,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="claims",
    )
    snapshot = models.ForeignKey(
        Snapshot,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="claims",
    )
    citations = models.ManyToManyField("Citation", related_name="claims")
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["timespan__start_year", "id"]

    def __str__(self):
        return self.text[:80]


class ClaimRevision(models.Model):
    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name="revisions")
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="claim_revisions",
    )
    from_state = models.CharField(max_length=24, choices=WorkflowState.choices)
    to_state = models.CharField(max_length=24, choices=WorkflowState.choices)
    text_snapshot = models.TextField()
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.claim_id}: {self.from_state} -> {self.to_state}"
