import pytest
from django.urls import reverse

from knowledge.models import Region, Topic
from knowledge.services.publication import publish_claim
from tests.factories import add_citation, make_claim, make_staff_user


@pytest.mark.django_db
def test_year_slice_api_groups_claims_by_region(client):
    claim = make_claim()
    topic = Topic.objects.create(name="政治", slug="politics")
    claim.topics.add(topic)
    add_citation(claim)
    publish_claim(
        claim=claim,
        reviewer=make_staff_user(),
        reason="Verified",
    )

    response = client.get(
        reverse("knowledge_api:year-slice"),
        {"year": "1520", "topic": "politics"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["year"] == 1520
    assert payload["regions"][0]["name"] == "Test Region"
    assert payload["regions"][0]["claims"][0]["text"] == claim.text
    assert payload["regions"][0]["claims"][0]["citations"][0]["locator"] == "p. 1"


@pytest.mark.django_db
@pytest.mark.parametrize("query", [{}, {"year": "not-a-year"}, {"year": "12000"}])
def test_year_slice_api_rejects_invalid_year(client, query):
    response = client.get(reverse("knowledge_api:year-slice"), query)

    assert response.status_code == 400


@pytest.mark.django_db
def test_year_slice_api_accepts_repeated_region_and_topic_filters(client):
    reviewer = make_staff_user()
    first_topic = Topic.objects.create(name="政治", slug="politics")
    second_topic = Topic.objects.create(name="经济", slug="economy")
    first_claim = make_claim()
    first_claim.topics.add(first_topic)
    first_region = first_claim.regions.get()
    add_citation(first_claim)
    publish_claim(claim=first_claim, reviewer=reviewer, reason="Verified")
    second_region = Region.objects.create(
        name="Second Region",
        slug="second-region",
        sort_order=10,
    )
    second_claim = make_claim()
    second_claim.regions.set([second_region])
    second_claim.topics.add(second_topic)
    add_citation(second_claim)
    publish_claim(claim=second_claim, reviewer=reviewer, reason="Verified")

    response = client.get(
        reverse("knowledge_api:year-slice"),
        {
            "year": "1520",
            "region": [str(first_region.id), str(second_region.id)],
            "topic": ["politics", "economy"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert [region["slug"] for region in payload["regions"]] == [
        "test-region",
        "second-region",
    ]
    assert [
        region["claims"][0]["text"] for region in payload["regions"]
    ] == [
        first_claim.text,
        second_claim.text,
    ]


@pytest.mark.django_db
def test_year_slice_api_region_filter_limits_grouped_regions(client):
    topic = Topic.objects.create(name="政治", slug="politics")
    claim = make_claim()
    requested_region = claim.regions.get()
    unrequested_region = Region.objects.create(
        name="Unrequested Region",
        slug="unrequested-region",
        sort_order=10,
    )
    claim.regions.add(unrequested_region)
    claim.topics.add(topic)
    add_citation(claim)
    publish_claim(
        claim=claim,
        reviewer=make_staff_user(),
        reason="Verified",
    )

    response = client.get(
        reverse("knowledge_api:year-slice"),
        {
            "year": "1520",
            "region": [str(requested_region.id), str(requested_region.id)],
            "topic": ["politics", "politics"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert [region["slug"] for region in payload["regions"]] == ["test-region"]
    assert [claim["id"] for claim in payload["regions"][0]["claims"]] == [claim.id]


@pytest.mark.django_db
def test_year_slice_api_groups_regions_in_deterministic_order(client):
    claim = make_claim()
    low_priority_region = claim.regions.get()
    low_priority_region.sort_order = 20
    low_priority_region.name = "Z Region"
    low_priority_region.save()
    high_priority_region = Region.objects.create(
        name="A Region",
        slug="a-region",
        sort_order=10,
    )
    claim.regions.add(high_priority_region)
    add_citation(claim)
    publish_claim(
        claim=claim,
        reviewer=make_staff_user(),
        reason="Verified",
    )

    response = client.get(reverse("knowledge_api:year-slice"), {"year": "1520"})

    assert response.status_code == 200
    assert [region["slug"] for region in response.json()["regions"]] == [
        "a-region",
        "test-region",
    ]
