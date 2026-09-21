import pytest

from knowledge.models import Topic
from knowledge.services.publication import publish_claim
from knowledge.services.year_slice import select_year_slice
from tests.factories import add_citation, make_claim, make_staff_user


@pytest.mark.django_db
def test_selector_returns_only_published_claims_active_in_year():
    reviewer = make_staff_user()
    published = make_claim()
    add_citation(published)
    publish_claim(claim=published, reviewer=reviewer, reason="Verified")
    make_claim(workflow_state="draft")

    result = list(select_year_slice(year=1520))

    assert result == [published]


@pytest.mark.django_db
def test_selector_filters_by_region_and_topic():
    reviewer = make_staff_user()
    claim = make_claim()
    topic = Topic.objects.create(name="政治", slug="politics")
    claim.topics.add(topic)
    add_citation(claim)
    publish_claim(claim=claim, reviewer=reviewer, reason="Verified")
    region_id = claim.regions.get().id

    assert list(
        select_year_slice(
            year=1520,
            region_ids=[region_id],
            topic_slugs=["politics"],
        )
    ) == [claim]
    assert list(select_year_slice(year=1519, region_ids=[region_id])) == []


@pytest.mark.django_db
def test_selector_includes_start_and_end_year_boundaries():
    reviewer = make_staff_user()
    claim = make_claim()
    claim.timespan.start_year = 1500
    claim.timespan.end_year = 1600
    claim.timespan.display_text = "1500–1600"
    claim.timespan.save()
    add_citation(claim)
    publish_claim(claim=claim, reviewer=reviewer, reason="Verified")

    assert list(select_year_slice(year=1500)) == [claim]
    assert list(select_year_slice(year=1600)) == [claim]
    assert list(select_year_slice(year=1499)) == []
    assert list(select_year_slice(year=1601)) == []


@pytest.mark.django_db
@pytest.mark.parametrize("workflow_state", ["draft", "in_review", "approved", "withdrawn"])
def test_selector_excludes_all_non_published_workflow_states(workflow_state):
    make_claim(workflow_state=workflow_state)

    assert list(select_year_slice(year=1520)) == []
