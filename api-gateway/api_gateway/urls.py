from django.contrib import admin
from django.urls import path
from . import views, shop_views

urlpatterns = [
    # Customer Portal (root)
    path('', shop_views.shop_home, name='shop_home'),
    path('login/', shop_views.shop_login, name='shop_login'),
    path('register/', shop_views.shop_register, name='shop_register'),
    path('logout/', shop_views.shop_logout, name='shop_logout'),
    path('books/', shop_views.shop_books, name='shop_books'),
    path('books/<int:pk>/', shop_views.shop_book_detail, name='shop_book_detail'),
    path('clothes/', shop_views.shop_clothes, name='shop_clothes'),
    path('clothes/<int:pk>/', shop_views.shop_clothes_detail, name='shop_clothes_detail'),
    path('cart/', shop_views.shop_cart, name='shop_cart'),
    path('checkout/', shop_views.shop_checkout, name='shop_checkout'),
    path('orders/', shop_views.shop_orders, name='shop_orders'),
    path('reviews/', shop_views.shop_reviews, name='shop_reviews'),
    path('account/', shop_views.shop_account, name='shop_account'),

    # Admin / Staff Dashboard
    path('admin/', admin.site.urls),
    path('dashboard/login/', views.dashboard_login, name='dashboard_login'),
    path('dashboard/logout/', views.dashboard_logout, name='dashboard_logout'),
    path('dashboard/', views.home, name='home'),
    path('dashboard/books/', views.book_list, name='book_list'),
    path('dashboard/clothes/products/', views.clothes_product_list, name='clothes_product_list'),
    path('dashboard/clothes/variants/', views.clothes_variant_list, name='clothes_variant_list'),
    path('dashboard/customers/', views.customer_list, name='customer_list'),
    path('dashboard/staffs/', views.staff_list, name='staff_list'),
    path('dashboard/managers/', views.manager_list, name='manager_list'),
    path('dashboard/catalogs/', views.catalog_list, name='catalog_list'),
    path('dashboard/orders/', views.order_list, name='order_list'),
    path('dashboard/shipments/', views.shipment_list, name='shipment_list'),
    path('dashboard/payments/', views.payment_list, name='payment_list'),
    path('dashboard/reviews/', views.review_list, name='review_list'),
]
