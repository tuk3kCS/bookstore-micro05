from django.contrib import admin
from .models import ClothesProduct, ClothesVariant


@admin.register(ClothesProduct)
class ClothesProductAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "brand", "catalog_id", "created_at")
    search_fields = ("name", "brand")


@admin.register(ClothesVariant)
class ClothesVariantAdmin(admin.ModelAdmin):
    list_display = ("id", "sku", "product", "size", "color", "price", "stock")
    search_fields = ("sku", "product__name")
    list_filter = ("size", "color")

