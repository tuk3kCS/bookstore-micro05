from django.urls import path
from .views import StaffListCreate, StaffDetail, StaffLogin, StaffManageBooks

urlpatterns = [
    path('staffs/', StaffListCreate.as_view()),
    path('staffs/<int:pk>/', StaffDetail.as_view()),
    path('staffs/login/', StaffLogin.as_view()),
    path('staffs/books/', StaffManageBooks.as_view()),
]
