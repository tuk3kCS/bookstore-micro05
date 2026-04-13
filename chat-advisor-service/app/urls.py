from django.urls import path
from .views import Health, AdvisorChat

urlpatterns = [
    path("health/", Health.as_view()),
    path("advisor/chat/", AdvisorChat.as_view()),
]

