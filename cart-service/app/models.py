from django.db import models


class Cart(models.Model):
    customer_id = models.IntegerField()


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)
    # Backward-compatible field for older clients (books only).
    book_id = models.IntegerField(null=True, blank=True)
    # New generalized reference (book or clothes variant).
    item_type = models.CharField(max_length=20, default="book")
    item_id = models.IntegerField(null=True, blank=True)
    quantity = models.IntegerField()
