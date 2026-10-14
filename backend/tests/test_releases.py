import pytest
from django.core.exceptions import PermissionDenied
from django.urls import reverse

from knowledge.services.publication import publish_claim, withdraw_claim
from knowledge.services.releases import publish_release, withdraw_release
from tests.factories import add_citation, make_claim, make_staff_user


@pytest.mark.django_db
def test_publish_release_requires_staff(django_user_model):
    reviewer = django_user_model.objects.create_user(username="reader")

    with pytest.raises(PermissionDenied):
        publish_release(reviewer=reviewer, note="Not allowed")


@pytest.mark.django_db
def test_package_delta_removes_withdrawn_claim(client):
    reviewer = make_staff_user()
    first = make_claim()
    first.text = "第一条已发布陈述"
    first.save(update_fields=["text"])
    add_citation(first)
    publish_claim(claim=first, reviewer=reviewer, reason="Verified")
    second = make_claim()
    second.text = "第二条已发布陈述"
    second.save(update_fields=["text"])
    add_citation(second)
    publish_claim(claim=second, reviewer=reviewer, reason="Verified")
    first_release = publish_release(reviewer=reviewer, note="Initial")

    withdraw_claim(claim=second, reviewer=reviewer, reason="Citation contradicted")
    second_release = publish_release(reviewer=reviewer, note="Correction")

    version = client.get(reverse("knowledge_api:content-version"))
    package = client.get(
        reverse("knowledge_api:content-package"),
        {"since": first_release.version},
    )

    assert version.status_code == 200
    assert version.json()["version"] == second_release.version
    assert package.status_code == 200
    payload = package.json()
    assert payload["full"] is False
    assert payload["removed_claim_ids"] == [second.id]
    assert [item["id"] for item in payload["claims"]] == []


@pytest.mark.django_db
def test_withdrawing_current_release_restores_previous_package(client):
    reviewer = make_staff_user()
    claim = make_claim()
    add_citation(claim)
    publish_claim(claim=claim, reviewer=reviewer, reason="Verified")
    first_release = publish_release(reviewer=reviewer, note="Initial")
    withdraw_claim(claim=claim, reviewer=reviewer, reason="Needs revision")
    second_release = publish_release(reviewer=reviewer, note="Empty correction")

    withdraw_release(release=second_release, reviewer=reviewer, reason="Rollback")
    response = client.get(reverse("knowledge_api:content-package"))

    assert response.status_code == 200
    payload = response.json()
    assert payload["version"] == first_release.version
    assert payload["full"] is True
    assert [item["id"] for item in payload["claims"]] == [claim.id]


@pytest.mark.django_db
def test_unknown_since_version_returns_full_package(client):
    reviewer = make_staff_user()
    claim = make_claim()
    add_citation(claim)
    publish_claim(claim=claim, reviewer=reviewer, reason="Verified")
    publish_release(reviewer=reviewer, note="Initial")

    response = client.get(reverse("knowledge_api:content-package"), {"since": 99})

    assert response.status_code == 200
    assert response.json()["full"] is True
    assert response.json()["claims"][0]["text"] == claim.text
