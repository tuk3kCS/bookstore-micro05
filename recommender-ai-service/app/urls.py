from django.urls import path
from .views import (
    RecommendationList, RecommendationDetail,
    RecommendationByCustomer, GenerateRecommendations,
)
urlpatterns = [
    path('recommendations/', RecommendationList.as_view()),
    path('recommendations/detail/<int:pk>/', RecommendationDetail.as_view()),
    path('recommendations/generate/<int:customer_id>/', GenerateRecommendations.as_view()),
    path('recommendations/<int:customer_id>/', RecommendationByCustomer.as_view()),
]
