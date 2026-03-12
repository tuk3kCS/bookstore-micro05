from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Catalog
from .serializers import CatalogSerializer

class CatalogListCreate(APIView):
    def get(self, request):
        catalogs = Catalog.objects.all()
        serializer = CatalogSerializer(catalogs, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = CatalogSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CatalogDetail(APIView):
    def get(self, request, pk):
        try:
            catalog = Catalog.objects.get(pk=pk)
        except Catalog.DoesNotExist:
            return Response({"error": "Catalog not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = CatalogSerializer(catalog)
        return Response(serializer.data)

    def put(self, request, pk):
        try:
            catalog = Catalog.objects.get(pk=pk)
        except Catalog.DoesNotExist:
            return Response({"error": "Catalog not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = CatalogSerializer(catalog, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            catalog = Catalog.objects.get(pk=pk)
        except Catalog.DoesNotExist:
            return Response({"error": "Catalog not found"}, status=status.HTTP_404_NOT_FOUND)
        catalog.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
