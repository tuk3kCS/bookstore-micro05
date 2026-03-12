from django.urls import path
from .views import CustomerListCreate, CustomerDetail, CustomerLogin

urlpatterns = [
    path('customers/', CustomerListCreate.as_view()),
    path('customers/login/', CustomerLogin.as_view()),
    path('customers/<int:pk>/', CustomerDetail.as_view()),
]
