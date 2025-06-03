from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('sisimob.urls')),
    path('financeiro/', include('financeiro.urls')),  # Isso vai para financeiro/urls/__init__.py
]