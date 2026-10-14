from rest_framework.response import Response

from knowledge.api.reading import PublicReadView
from knowledge.api.serializers import FeedbackSerializer
from knowledge.models import ContentFeedback


class FeedbackView(PublicReadView):
    def post(self, request):
        serializer = FeedbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        feedback = ContentFeedback.objects.create(
            claim_id=serializer.validated_data["claim_id"],
            message=serializer.validated_data["message"].strip(),
        )
        return Response({"id": feedback.id, "status": feedback.status}, status=201)
