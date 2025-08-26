# projeto/urls.py (seu arquivo principal)
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('financeiro/', include('financeiro.urls')),
]