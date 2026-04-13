from django.urls import path
from .views import Health, IngestKB, RetrieveKB

urlpatterns = [
    path("health/", Health.as_view()),
    path("kb/ingest/", IngestKB.as_view()),
    path("kb/retrieve/", RetrieveKB.as_view()),
]

