from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import ClothesProduct, ClothesVariant
from .serializers import ClothesProductSerializer, ClothesVariantSerializer


class ProductListCreate(APIView):
    def get(self, request):
        qs = ClothesProduct.objects.all().order_by("-id")
        return Response(ClothesProductSerializer(qs, many=True).data)

    def post(self, request):
        ser = ClothesProductSerializer(data=request.data)
        if ser.is_valid():
            ser.save()
            return Response(ser.data, status=status.HTTP_201_CREATED)
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)


class ProductDetail(APIView):
    def get(self, request, pk):
        try:
            obj = ClothesProduct.objects.get(pk=pk)
        except ClothesProduct.DoesNotExist:
            return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(ClothesProductSerializer(obj).data)

    def put(self, request, pk):
        try:
            obj = ClothesProduct.objects.get(pk=pk)
        except ClothesProduct.DoesNotExist:
            return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)
        ser = ClothesProductSerializer(obj, data=request.data, partial=True)
        if ser.is_valid():
            ser.save()
            return Response(ser.data)
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            obj = ClothesProduct.objects.get(pk=pk)
        except ClothesProduct.DoesNotExist:
            return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class VariantListCreate(APIView):
    def get(self, request):
        qs = ClothesVariant.objects.select_related("product").all().order_by("-id")
        return Response(ClothesVariantSerializer(qs, many=True).data)

    def post(self, request):
        ser = ClothesVariantSerializer(data=request.data)
        if ser.is_valid():
            ser.save()
            return Response(ser.data, status=status.HTTP_201_CREATED)
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)


class VariantDetail(APIView):
    def get(self, request, pk):
        try:
            obj = ClothesVariant.objects.select_related("product").get(pk=pk)
        except ClothesVariant.DoesNotExist:
            return Response({"error": "Variant not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(ClothesVariantSerializer(obj).data)

    def put(self, request, pk):
        try:
            obj = ClothesVariant.objects.get(pk=pk)
        except ClothesVariant.DoesNotExist:
            return Response({"error": "Variant not found"}, status=status.HTTP_404_NOT_FOUND)
        ser = ClothesVariantSerializer(obj, data=request.data, partial=True)
        if ser.is_valid():
            ser.save()
            return Response(ser.data)
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            obj = ClothesVariant.objects.get(pk=pk)
        except ClothesVariant.DoesNotExist:
            return Response({"error": "Variant not found"}, status=status.HTTP_404_NOT_FOUND)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProductVariants(APIView):
    def get(self, request, pk):
        try:
            product = ClothesProduct.objects.get(pk=pk)
        except ClothesProduct.DoesNotExist:
            return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)
        qs = product.variants.all().order_by("id")
        return Response(ClothesVariantSerializer(qs, many=True).data)

