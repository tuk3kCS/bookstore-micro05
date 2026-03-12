from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Recommendation
from .serializers import RecommendationSerializer
from .engine import generate_recommendations

class RecommendationList(APIView):
    def get(self, request):
        recs = Recommendation.objects.all()
        serializer = RecommendationSerializer(recs, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = RecommendationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class RecommendationDetail(APIView):
    def get(self, request, pk):
        try:
            rec = Recommendation.objects.get(pk=pk)
        except Recommendation.DoesNotExist:
            return Response({"error": "Recommendation not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = RecommendationSerializer(rec)
        return Response(serializer.data)

    def put(self, request, pk):
        try:
            rec = Recommendation.objects.get(pk=pk)
        except Recommendation.DoesNotExist:
            return Response({"error": "Recommendation not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = RecommendationSerializer(rec, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            rec = Recommendation.objects.get(pk=pk)
        except Recommendation.DoesNotExist:
            return Response({"error": "Recommendation not found"}, status=status.HTTP_404_NOT_FOUND)
        rec.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RecommendationByCustomer(APIView):
    def get(self, request, customer_id):
        recs = Recommendation.objects.filter(customer_id=customer_id)
        serializer = RecommendationSerializer(recs, many=True)
        return Response(serializer.data)


class GenerateRecommendations(APIView):
    """
    POST /recommendations/generate/<customer_id>/
    Runs the AI engine, replaces old recommendations, returns the new ones.
    """
    def post(self, request, customer_id):
        try:
            results = generate_recommendations(customer_id)
        except Exception as e:
            return Response(
                {"error": f"AI engine error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        Recommendation.objects.filter(customer_id=customer_id).delete()

        saved = []
        for item in results:
            rec = Recommendation.objects.create(
                customer_id=item["customer_id"],
                book_id=item["book_id"],
                score=item["score"],
                reason=item["reason"],
            )
            saved.append(rec)

        serializer = RecommendationSerializer(saved, many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
