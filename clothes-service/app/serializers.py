from rest_framework import serializers
from .models import ClothesProduct, ClothesVariant


class ClothesProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClothesProduct
        fields = "__all__"


class ClothesVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClothesVariant
        fields = "__all__"

