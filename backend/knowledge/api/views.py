from rest_framework.response import Response
from rest_framework.views import APIView

from knowledge.api.serializers import ClaimSerializer, YearSliceQuerySerializer
from knowledge.services.year_slice import select_year_slice


class YearSliceView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        query = YearSliceQuerySerializer(
            data={
                "year": request.query_params.get("year"),
                "region": request.query_params.getlist("region"),
                "topic": request.query_params.getlist("topic"),
            }
        )
        query.is_valid(raise_exception=True)
        values = query.validated_data
        claims = select_year_slice(
            year=values["year"],
            region_ids=values["region"],
            topic_slugs=values["topic"],
        )
        requested_region_ids = set(values["region"])

        grouped = {}
        for claim in claims:
            serialized_claim = ClaimSerializer(claim).data
            for region in claim.regions.all():
                if requested_region_ids and region.id not in requested_region_ids:
                    continue
                region_group = grouped.setdefault(
                    region.id,
                    {
                        "id": region.id,
                        "slug": region.slug,
                        "name": region.name,
                        "sort_order": region.sort_order,
                        "claims": [],
                    },
                )
                region_group["claims"].append(serialized_claim)

        regions = sorted(
            grouped.values(),
            key=lambda item: (item["sort_order"], item["name"]),
        )
        for region in regions:
            region.pop("sort_order")
        return Response({"year": values["year"], "regions": regions})
