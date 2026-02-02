from django.urls import path
from . import views
from .views import document_open

urlpatterns = [
    path("<int:pk>/open/", document_open, name="document_open"),
    path("chained_filter/documents/SubTask/task/documents/Task/id/<str:value>/", 
         views.chained_filter, 
         {'app': 'documents', 'model': 'SubTask', 'field': 'task', 'foreign_key_app_name': 'documents', 'foreign_key_model_name': 'Task', 'foreign_key_field_name': 'id'},
         name="document_chained_filter"),
]