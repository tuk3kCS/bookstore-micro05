from django.urls import path
from .views import (
    ProductListCreate,
    ProductDetail,
    VariantListCreate,
    VariantDetail,
    ProductVariants,
)

urlpatterns = [
    path("products/", ProductListCreate.as_view()),
    path("products/<int:pk>/", ProductDetail.as_view()),
    path("variants/", VariantListCreate.as_view()),
    path("variants/<int:pk>/", VariantDetail.as_view()),
    path("products/<int:pk>/variants/", ProductVariants.as_view()),
]

