from django.contrib import admin
from django.urls import path, include
from core import settings
from django.conf.urls.static import static
from .views import home

urlpatterns = [
    # frontend url
    path('',home , name="home"),
    # admin url
    path('admin/', admin.site.urls),
    # api url
    path('api/v1/locations/', include("properties.urls"))
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
