import pytest
from django.urls import reverse

from knowledge.models import Event, Person, Topic
from knowledge.services.publication import publish_claim
from knowledge.services.search import search_published
from tests.factories import add_citation, make_claim, make_staff_user


@pytest.mark.django_db
def test_search_returns_only_published_text_matches():
    reviewer = make_staff_user()
    matched = make_claim()
    matched.text = "宗教改革在欧洲展开"
    matched.save(update_fields=["text"])
    add_citation(matched)
    publish_claim(claim=matched, reviewer=reviewer, reason="Verified")
    hidden = make_claim(workflow_state="draft")
    hidden.text = "宗教改革草稿"
    hidden.save(update_fields=["text"])

    assert list(search_published(query="宗教改革")) == [matched]


@pytest.mark.django_db
def test_search_matches_related_person_name():
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

    assert list(search_published(query="路德")) == [claim]


@pytest.mark.django_db
def test_search_api_rejects_blank_query(client):
    response = client.get(reverse("knowledge_api:search"), {"q": " "})

    assert response.status_code == 400


@pytest.mark.django_db
def test_search_api_returns_published_claim(client):
    reviewer = make_staff_user()
    claim = make_claim()
    topic = Topic.objects.create(name="文化", slug="culture-test")
    claim.topics.add(topic)
    claim.text = "明世宗即位"
    claim.save(update_fields=["text"])
    add_citation(claim)
    publish_claim(claim=claim, reviewer=reviewer, reason="Verified")

    response = client.get(reverse("knowledge_api:search"), {"q": "世宗"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "世宗"
    assert payload["claims"][0]["id"] == claim.id
    assert payload["claims"][0]["start_year"] == 1520
