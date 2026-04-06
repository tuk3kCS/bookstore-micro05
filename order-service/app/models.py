from django.db import models

class Order(models.Model):
    customer_id = models.IntegerField()
    status = models.CharField(max_length=50, default='pending')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    # Backward-compatible field for older clients (books only).
    book_id = models.IntegerField(null=True, blank=True)
    # New generalized reference (book or clothes variant).
    item_type = models.CharField(max_length=20, default="book")
    item_id = models.IntegerField(null=True, blank=True)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
