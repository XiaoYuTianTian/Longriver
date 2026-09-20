from django.contrib.auth import get_user_model

from knowledge.models import (
    Citation,
    Claim,
    Edition,
    HistoricalTimeSpan,
    Region,
    Source,
)


def make_staff_user(username="editor"):
    return get_user_model().objects.create_user(
        username=username,
        password="test-password",
        is_staff=True,
    )


def make_claim(*, workflow_state="approved"):
    span = HistoricalTimeSpan.objects.create(
        start_year=1520,
        end_year=1520,
        precision="year",
        display_text="1520",
    )
    region, _ = Region.objects.get_or_create(
        slug="test-region",
        defaults={"name": "Test Region"},
    )
    claim = Claim.objects.create(
        text="Synthetic historical claim for automated tests.",
        timespan=span,
        certainty="verified",
        workflow_state=workflow_state,
    )
    claim.regions.add(region)
    return claim


def add_citation(claim):
    source = Source.objects.create(
        title="Synthetic source for automated tests",
        kind="book",
        license_status="metadata_only",
    )
    edition = Edition.objects.create(source=source, label="Test edition")
    citation = Citation.objects.create(
        edition=edition,
        locator="p. 1",
        stable_url="https://example.test/source",
    )
    claim.citations.add(citation)
    return citation
