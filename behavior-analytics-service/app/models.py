from django.db import models


class BehaviorEvent(models.Model):
    """
    Minimal, future-proof event record.
    - customer_id: link to customer-service entity (int in this codebase)
    - session_id: browser session (string) for anonymous/temporal grouping
    - correlation_id: for tracing across services
    - item reference: generalized item_type/item_id (book or clothes variant, etc.)
    """

    customer_id = models.IntegerField(null=True, blank=True, db_index=True)
    session_id = models.CharField(max_length=128, blank=True, db_index=True)
    correlation_id = models.CharField(max_length=128, blank=True, db_index=True)

    event_type = models.CharField(max_length=64, db_index=True)
    page = models.CharField(max_length=255, blank=True)
    referrer = models.CharField(max_length=255, blank=True)

    item_type = models.CharField(max_length=20, blank=True)
    item_id = models.IntegerField(null=True, blank=True)

    metadata = models.JSONField(default=dict, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["customer_id", "created_at"]),
            models.Index(fields=["session_id", "created_at"]),
            models.Index(fields=["event_type", "created_at"]),
        ]

