import pytest
from django.core.management import call_command

from knowledge.models import Region, Topic

EXPECTED_REGIONS = [
    ("east-asia", "东亚", 10),
    ("west-asia-north-africa", "西亚与北非", 20),
    ("europe", "欧洲", 30),
    ("americas", "美洲", 40),
]
EXPECTED_TOPICS = {
    "politics": "政治",
    "economy": "经济",
    "society": "社会",
    "technology": "科技",
    "culture": "文化",
}


@pytest.mark.django_db
def test_reference_data_command_is_idempotent():
    call_command("load_reference_data")
    call_command("load_reference_data")

    assert Region.objects.filter(parent=None).count() == 4
    for slug, name, sort_order in EXPECTED_REGIONS:
        region = Region.objects.get(slug=slug)
        assert region.name == name
        assert region.sort_order == sort_order
        assert region.parent is None

    assert set(Topic.objects.values_list("slug", "name")) == set(EXPECTED_TOPICS.items())


@pytest.mark.django_db
def test_reference_data_regions_are_top_level_when_reloaded():
    parent = Region.objects.create(slug="parent", name="Parent")
    Region.objects.create(slug="europe", name="Nested Europe", parent=parent)

    call_command("load_reference_data")

    assert Region.objects.get(slug="europe").parent is None
