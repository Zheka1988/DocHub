from django.urls import path
from .views import incoming_document_open, outgoing_document_open


urlpatterns = [
    path('incoming/<int:pk>/open/', incoming_document_open, name='incoming_document_open'),
    path('outgoing/<int:pk>/open/', outgoing_document_open, name='outgoing_document_open'),
]


