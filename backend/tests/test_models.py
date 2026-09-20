import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from knowledge.models import Citation, Edition, HistoricalTimeSpan, Source


@pytest.mark.django_db
def test_time_span_rejects_reversed_range():
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            HistoricalTimeSpan.objects.create(
                start_year=1600,
                end_year=1500,
                precision="range",
                display_text="1600–1500",
            )


@pytest.mark.django_db
def test_citation_requires_locator_or_url():
    source = Source.objects.create(
        title="Synthetic test source",
        kind="book",
        license_status="metadata_only",
    )
    edition = Edition.objects.create(source=source, label="Test edition")
    citation = Citation(edition=edition, locator="", stable_url="")

    with pytest.raises(ValidationError):
        citation.full_clean()
