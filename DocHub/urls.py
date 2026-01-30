from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path("chaining/", include("smart_selects.urls")),
    path('documents/', include('documents.urls')),
    # path('users/', include('users.urls'))
]
