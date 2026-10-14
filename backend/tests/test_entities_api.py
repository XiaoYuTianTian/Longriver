import pytest
from django.urls import reverse

from knowledge.models import Event, Person, Polity, Snapshot
from knowledge.services.publication import publish_claim
from tests.factories import add_citation, make_claim, make_staff_user


@pytest.mark.django_db
def test_event_detail_includes_published_claims_only(client):
    reviewer = make_staff_user()
    claim = make_claim()
    person = Person.objects.create(name="马丁·路德")
    event = Event.objects.create(title="公布论纲", timespan=claim.timespan)
    event.people.add(person)
    event.regions.add(claim.regions.get())
    claim.event = event
    claim.save(update_fields=["event"])
    add_citation(claim)
    publish_claim(claim=claim, reviewer=reviewer, reason="Verified")
    draft = make_claim(workflow_state="draft")
    draft.event = event
    draft.save(update_fields=["event"])

    response = client.get(reverse("knowledge_api:event-detail", args=[event.id]))

    assert response.status_code == 200
    payload = response.json()
    assert payload["title"] == "公布论纲"
    assert payload["people"][0]["name"] == "马丁·路德"
    assert [item["id"] for item in payload["claims"]] == [claim.id]


@pytest.mark.django_db
def test_event_detail_hides_events_without_published_claims(client):
    claim = make_claim(workflow_state="draft")
    event = Event.objects.create(title="未发布事件", timespan=claim.timespan)
    claim.event = event
    claim.save(update_fields=["event"])

    response = client.get(reverse("knowledge_api:event-detail", args=[event.id]))

    assert response.status_code == 404


@pytest.mark.django_db
def test_snapshot_detail_returns_region_state(client):
    reviewer = make_staff_user()
    claim = make_claim()
    region = claim.regions.get()
    snapshot = Snapshot.objects.create(
        label="宗教改革展开",
        region=region,
        timespan=claim.timespan,
        dimension="culture",
    )
    claim.snapshot = snapshot
    claim.save(update_fields=["snapshot"])
    add_citation(claim)
    publish_claim(claim=claim, reviewer=reviewer, reason="Verified")

    response = client.get(reverse("knowledge_api:snapshot-detail", args=[snapshot.id]))

    assert response.status_code == 200
    assert response.json()["label"] == "宗教改革展开"
    assert response.json()["region"]["id"] == region.id


@pytest.mark.django_db
def test_person_and_polity_details_are_public_when_published(client):
    reviewer = make_staff_user()
    claim = make_claim()
    person = Person.objects.create(name="苏莱曼一世")
    polity = Polity.objects.create(name="奥斯曼帝国", slug="ottoman-test")
    event = Event.objects.create(title="苏莱曼即位", timespan=claim.timespan)
    event.people.add(person)
    event.regions.add(claim.regions.get())
    claim.event = event
    claim.polities.add(polity)
    claim.save(update_fields=["event"])
    add_citation(claim)
    publish_claim(claim=claim, reviewer=reviewer, reason="Verified")

    person_response = client.get(reverse("knowledge_api:person-detail", args=[person.id]))
    polity_response = client.get(reverse("knowledge_api:polity-detail", args=[polity.id]))

    assert person_response.status_code == 200
    assert person_response.json()["claims"][0]["id"] == claim.id
    assert polity_response.status_code == 200
    assert polity_response.json()["name"] == "奥斯曼帝国"
