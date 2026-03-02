from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path('admin/', admin.site.urls),
    path("chaining/", include("smart_selects.urls")),
    path('documents/', include('documents.urls')),
    path('correspondence/', include('correspondence.urls')),
    # path('users/', include('users.urls'))
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
