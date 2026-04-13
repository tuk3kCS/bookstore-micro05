from django.urls import path
from .views import EventIngest, CustomerProfile, Health, ModelTrain, ModelInfer

urlpatterns = [
    path("health/", Health.as_view()),
    path("events/", EventIngest.as_view()),
    path("profiles/<int:customer_id>/", CustomerProfile.as_view()),
    path("model/train/", ModelTrain.as_view()),
    path("model/infer/", ModelInfer.as_view()),
]

