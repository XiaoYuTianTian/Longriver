from django.urls import path

from knowledge.api.feedback import FeedbackView
from knowledge.api.reading import (
    EventDetailView,
    PersonDetailView,
    PolityDetailView,
    RegionDetailView,
    SnapshotDetailView,
)
from knowledge.api.sync import ContentPackageView, ContentVersionView, SearchView
from knowledge.api.views import YearSliceView

app_name = "knowledge_api"
urlpatterns = [
    path("timeline/year-slice/", YearSliceView.as_view(), name="year-slice"),
    path("search/", SearchView.as_view(), name="search"),
    path("entities/events/<int:pk>/", EventDetailView.as_view(), name="event-detail"),
    path("entities/snapshots/<int:pk>/", SnapshotDetailView.as_view(), name="snapshot-detail"),
    path("entities/people/<int:pk>/", PersonDetailView.as_view(), name="person-detail"),
    path("entities/polities/<int:pk>/", PolityDetailView.as_view(), name="polity-detail"),
    path("entities/regions/<int:pk>/", RegionDetailView.as_view(), name="region-detail"),
    path("content/version/", ContentVersionView.as_view(), name="content-version"),
    path("content/packages/", ContentPackageView.as_view(), name="content-package"),
    path("feedback/", FeedbackView.as_view(), name="feedback"),
]
