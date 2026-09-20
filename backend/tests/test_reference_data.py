import pytest
from django.core.management import call_command

from knowledge.models import Region, Topic


@pytest.mark.django_db
def test_reference_data_command_is_idempotent():
    call_command("load_reference_data")
    call_command("load_reference_data")

    assert Region.objects.filter(parent=None).count() == 4
    assert set(Topic.objects.values_list("slug", flat=True)) == {
        "politics",
        "economy",
        "society",
        "technology",
        "culture",
    }


@pytest.mark.django_db
def test_reference_data_regions_are_top_level_when_reloaded():
    parent = Region.objects.create(slug="parent", name="Parent")
    Region.objects.create(slug="europe", name="Nested Europe", parent=parent)

    call_command("load_reference_data")

    assert Region.objects.get(slug="europe").parent is None
