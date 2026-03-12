from django.urls import path
from .views import CartCreate, AddCartItem, CartItemDetail, CartInfo, ViewCart

urlpatterns = [
    path('carts/', CartCreate.as_view()),
    path('cart-items/', AddCartItem.as_view()),
    path('cart-items/<int:pk>/', CartItemDetail.as_view()),
    path('carts/info/<int:customer_id>/', CartInfo.as_view()),
    path('carts/<int:customer_id>/', ViewCart.as_view()),
]
