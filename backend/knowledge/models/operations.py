from django.conf import settings
from django.db import models

from .enums import FeedbackStatus, ReleaseStatus


class KnowledgeRelease(models.Model):
    version = models.PositiveIntegerField(unique=True)
    status = models.CharField(max_length=24, choices=ReleaseStatus.choices)
    manifest = models.JSONField()
    note = models.TextField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="knowledge_releases",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-version"]

    def __str__(self):
        return f"Release {self.version} ({self.status})"


class ContentFeedback(models.Model):
    claim = models.ForeignKey(
        "Claim",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="feedback",
    )
    message = models.TextField()
    status = models.CharField(
        max_length=24,
        choices=FeedbackStatus.choices,
        default=FeedbackStatus.OPEN,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return self.message[:80]
