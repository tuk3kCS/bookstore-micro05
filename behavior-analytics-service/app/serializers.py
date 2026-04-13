from rest_framework import serializers
from .models import BehaviorEvent


class BehaviorEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = BehaviorEvent
        fields = [
            "id",
            "customer_id",
            "session_id",
            "correlation_id",
            "event_type",
            "page",
            "referrer",
            "item_type",
            "item_id",
            "metadata",
            "user_agent",
            "ip",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

