from django.db import models


class ClothesProduct(models.Model):
    name = models.CharField(max_length=255)
    brand = models.CharField(max_length=255, blank=True, default="")
    description = models.TextField(blank=True, default="")
    catalog_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class ClothesVariant(models.Model):
    product = models.ForeignKey(ClothesProduct, related_name="variants", on_delete=models.CASCADE)
    sku = models.CharField(max_length=64, unique=True)
    color = models.CharField(max_length=64, blank=True, default="")
    size = models.CharField(max_length=32, blank=True, default="")
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.product.name} ({self.size}/{self.color})"

