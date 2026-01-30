from django.urls import path
from .views import document_open

urlpatterns = [
    path("<int:pk>/open/", document_open, name="document_open"),
]