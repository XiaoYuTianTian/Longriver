from rest_framework.response import Response

from knowledge.api.reading import PublicReadView
from knowledge.api.serializers import SearchQuerySerializer
from knowledge.services.catalog import serialize_claim
from knowledge.services.releases import build_package, current_release
from knowledge.services.search import search_published


class SearchView(PublicReadView):
    def get(self, request):
        query = SearchQuerySerializer(data={"q": request.query_params.get("q", "")})
        query.is_valid(raise_exception=True)
        claims = search_published(query=query.validated_data["q"])
        return Response(
            {
                "query": query.validated_data["q"],
                "claims": [serialize_claim(claim) for claim in claims],
            }
        )


class ContentVersionView(PublicReadView):
    def get(self, request):
        release = current_release()
        return Response({"version": 0 if release is None else release.version})


class ContentPackageView(PublicReadView):
    def get(self, request):
        raw_since = request.query_params.get("since")
        since = None
        if raw_since not in (None, ""):
            try:
                since = int(raw_since)
            except ValueError:
                return Response({"since": "版本号必须是整数。"}, status=400)
        return Response(build_package(since=since))
