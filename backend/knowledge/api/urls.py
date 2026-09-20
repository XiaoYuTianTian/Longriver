from django.urls import path

from knowledge.api.views import YearSliceView

app_name = "knowledge_api"
urlpatterns = [
    path(
        "timeline/year-slice/",
        YearSliceView.as_view(),
        name="year-slice",
    ),
]
