from rest_framework import serializers
from .models import Recommendation

class RecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recommendation
        fields = '__all__'

    def validate(self, attrs):
        # Backward compatibility: if book_id is provided, mirror into item_type/item_id.
        if attrs.get("book_id") is not None and attrs.get("item_id") is None:
            attrs["item_type"] = "book"
            attrs["item_id"] = attrs["book_id"]
        if attrs.get("item_id") is None:
            raise serializers.ValidationError({"item_id": "item_id is required (or provide book_id)."})
        if attrs.get("item_type") not in ("book", "clothes"):
            raise serializers.ValidationError({"item_type": "item_type must be 'book' or 'clothes'."})
        return attrs
