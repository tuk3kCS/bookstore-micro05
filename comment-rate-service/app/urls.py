from django.urls import path
from .views import ReviewListCreate, ReviewDetail, ReviewsByBook
urlpatterns = [
    path('reviews/', ReviewListCreate.as_view()),
    path('reviews/<int:pk>/', ReviewDetail.as_view()),
    path('reviews/book/<int:book_id>/', ReviewsByBook.as_view()),
]
