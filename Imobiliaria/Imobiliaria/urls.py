# projeto/urls.py (seu arquivo principal)
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # URLs base (home, logout, buscar)
    path('', include('core.urls.base_urls')),
    
    # URLs específicas de cada módulo
    path('clientes/', include('core.urls.cliente')),
    path('imoveis/', include('core.urls.imovel')),
    path('contratos/', include('core.urls.contrato')),
    
    # URLs do financeiro
    path('financeiro/', include('financeiro.urls')),
]