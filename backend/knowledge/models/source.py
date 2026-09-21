from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from .enums import LicenseStatus, SourceKind

MAX_METADATA_ONLY_QUOTATION_LENGTH = 2000


class Source(models.Model):
    title = models.CharField(max_length=512)
    kind = models.CharField(max_length=24, choices=SourceKind.choices)
    creators = models.JSONField(default=list, blank=True)
    canonical_url = models.URLField(blank=True)
    license_status = models.CharField(
        max_length=24,
        choices=LicenseStatus.choices,
    )
    license_note = models.TextField(blank=True)
    accessed_on = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["title", "id"]

    def __str__(self):
        return self.title


class Edition(models.Model):
    source = models.ForeignKey(Source, on_delete=models.PROTECT, related_name="editions")
    label = models.CharField(max_length=256)
    publisher = models.CharField(max_length=256, blank=True)
    publication_year = models.IntegerField(null=True, blank=True)
    isbn = models.CharField(max_length=32, blank=True)
    external_id = models.CharField(max_length=128, blank=True)

    class Meta:
        ordering = ["source__title", "publication_year", "id"]

    def __str__(self):
        return f"{self.source.title} — {self.label}"


class Citation(models.Model):
    edition = models.ForeignKey(Edition, on_delete=models.PROTECT, related_name="citations")
    locator = models.CharField(max_length=256, blank=True)
    quotation = models.TextField(blank=True)
    stable_url = models.URLField(blank=True)

    class Meta:
        ordering = ["edition_id", "locator", "id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(locator__regex=r"\S") | Q(stable_url__regex=r"\S"),
                name="knowledge_citation_locator_or_url",
            )
        ]

    def clean(self):
        super().clean()
        if not self.locator.strip() and not self.stable_url.strip():
            raise ValidationError("Citation requires a locator or stable URL.")
        if (
            self.edition_id
            and self.edition.source.license_status == LicenseStatus.METADATA_ONLY
            and len(self.quotation) > MAX_METADATA_ONLY_QUOTATION_LENGTH
        ):
            raise ValidationError(
                "Metadata-only sources may not store quotations longer than "
                f"{MAX_METADATA_ONLY_QUOTATION_LENGTH} characters."
            )

    def __str__(self):  # noqa: DJ012
        return f"{self.edition}: {self.locator or self.stable_url}"
