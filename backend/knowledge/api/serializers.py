from rest_framework import serializers

from knowledge.models import Citation, Claim, Topic


class SearchQuerySerializer(serializers.Serializer):
    q = serializers.CharField(min_length=1, max_length=100, trim_whitespace=True)


class FeedbackSerializer(serializers.Serializer):
    message = serializers.CharField(min_length=1, max_length=4000, trim_whitespace=True)
    claim_id = serializers.IntegerField(min_value=1, required=False, allow_null=True, default=None)

    def validate_claim_id(self, value):
        if value is None:
            return None
        if not Claim.objects.filter(pk=value, workflow_state="published").exists():
            raise serializers.ValidationError("只能纠正已发布的陈述。")
        return value


class YearSliceQuerySerializer(serializers.Serializer):
    year = serializers.IntegerField(min_value=-10000, max_value=3000)
    region = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        default=list,
    )
    topic = serializers.ListField(
        child=serializers.SlugField(),
        required=False,
        default=list,
    )


class TopicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Topic
        fields = ["slug", "name"]


class CitationSerializer(serializers.ModelSerializer):
    source_title = serializers.CharField(source="edition.source.title")
    edition_label = serializers.CharField(source="edition.label")

    class Meta:
        model = Citation
        fields = [
            "id",
            "source_title",
            "edition_label",
            "locator",
            "quotation",
            "stable_url",
        ]


class ClaimSerializer(serializers.ModelSerializer):
    time_label = serializers.CharField(source="timespan.display_text")
    topics = TopicSerializer(many=True)
    citations = CitationSerializer(many=True)

    class Meta:
        model = Claim
        fields = [
            "id",
            "text",
            "certainty",
            "time_label",
            "topics",
            "citations",
            "event_id",
            "snapshot_id",
        ]
