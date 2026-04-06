from django.db import models

class Review(models.Model):
    customer_id = models.IntegerField()
    # Backward-compatible field for older clients (books only).
    book_id = models.IntegerField(null=True, blank=True)
    # New generalized reference (book or clothes variant).
    item_type = models.CharField(max_length=20, default="book")
    item_id = models.IntegerField(null=True, blank=True)
    rating = models.IntegerField()
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
