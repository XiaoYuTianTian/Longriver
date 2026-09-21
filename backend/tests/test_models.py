import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError

from knowledge.models import Citation, Edition, HistoricalTimeSpan, Polity, Region, Source


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
def test_citation_requires_locator_or_url_on_full_clean():
    source = Source.objects.create(
        title="Synthetic test source",
        kind="book",
        license_status="metadata_only",
    )
    edition = Edition.objects.create(source=source, label="Test edition")
    citation = Citation(edition=edition, locator="", stable_url="")

    with pytest.raises(ValidationError):
        citation.full_clean()


@pytest.mark.django_db
def test_citation_rejects_empty_locator_and_url_on_create():
    source = Source.objects.create(
        title="Synthetic test source",
        kind="book",
        license_status="metadata_only",
    )
    edition = Edition.objects.create(source=source, label="Test edition")

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Citation.objects.create(edition=edition, locator="", stable_url="")


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("locator", "stable_url"),
    [("   ", ""), ("", "   "), (" \t", "  ")],
)
def test_citation_rejects_whitespace_only_locator_and_url_on_create(locator, stable_url):
    source = Source.objects.create(
        title="Synthetic test source",
        kind="book",
        license_status="metadata_only",
    )
    edition = Edition.objects.create(source=source, label="Test edition")

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Citation.objects.create(edition=edition, locator=locator, stable_url=stable_url)


def test_citation_locator_constraint_requires_non_whitespace_regex():
    constraint = next(
        item
        for item in Citation._meta.constraints
        if item.name == "knowledge_citation_locator_or_url"
    )
    lookups = []

    def collect(q_object):
        for child in q_object.children:
            if isinstance(child, tuple):
                lookups.append(child[0])
            else:
                collect(child)

    collect(constraint.condition)
    assert "locator__regex" in lookups
    assert "stable_url__regex" in lookups


@pytest.mark.django_db
def test_citation_clean_rejects_metadata_only_quotation_over_limit():
    from knowledge.models.source import MAX_METADATA_ONLY_QUOTATION_LENGTH

    source = Source.objects.create(
        title="Metadata-only source",
        kind="book",
        license_status="metadata_only",
    )
    edition = Edition.objects.create(source=source, label="Test edition")
    citation = Citation(
        edition=edition,
        locator="p. 1",
        quotation="x" * (MAX_METADATA_ONLY_QUOTATION_LENGTH + 1),
    )

    with pytest.raises(ValidationError):
        citation.full_clean()


@pytest.mark.django_db
def test_citation_clean_accepts_metadata_only_quotation_at_limit():
    from knowledge.models.source import MAX_METADATA_ONLY_QUOTATION_LENGTH

    source = Source.objects.create(
        title="Metadata-only source",
        kind="book",
        license_status="metadata_only",
    )
    edition = Edition.objects.create(source=source, label="Test edition")
    citation = Citation(
        edition=edition,
        locator="p. 1",
        quotation="x" * MAX_METADATA_ONLY_QUOTATION_LENGTH,
    )

    citation.full_clean()


@pytest.mark.django_db
@pytest.mark.parametrize("license_status", ["public_domain", "open", "authorized"])
def test_citation_clean_accepts_open_license_quotation_over_limit(license_status):
    from knowledge.models.source import MAX_METADATA_ONLY_QUOTATION_LENGTH

    source = Source.objects.create(
        title="Licensed source",
        kind="book",
        license_status=license_status,
    )
    edition = Edition.objects.create(source=source, label="Test edition")
    citation = Citation(
        edition=edition,
        locator="p. 1",
        quotation="x" * (MAX_METADATA_ONLY_QUOTATION_LENGTH + 1),
    )

    citation.full_clean()


def test_metadata_only_quotation_length_constant_is_2000():
    from knowledge.models.source import MAX_METADATA_ONLY_QUOTATION_LENGTH

    assert MAX_METADATA_ONLY_QUOTATION_LENGTH == 2000


@pytest.mark.django_db
def test_region_parent_hierarchy_protects_parent_delete():
    parent = Region.objects.create(name="Parent", slug="parent-region")
    Region.objects.create(name="Child", slug="child-region", parent=parent)

    with pytest.raises(ProtectedError):
        parent.delete()


@pytest.mark.django_db
def test_polity_can_be_created_and_linked_to_regions():
    region = Region.objects.create(name="East Asia", slug="polity-east-asia")
    polity = Polity.objects.create(name="Ming", slug="ming")
    polity.regions.add(region)

    assert list(polity.regions.all()) == [region]
    assert list(region.polities.all()) == [polity]
