# projeto/urls.py (seu arquivo principal)
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # URLs base (home, logout, buscar)
    path('', include('sisimob.urls.base_urls')),
    
    # URLs específicas de cada módulo
    path('clientes/', include('sisimob.urls.cliente')),
    path('imoveis/', include('sisimob.urls.imovel')),
    path('contratos/', include('sisimob.urls.contrato')),
    
    # URLs do financeiro
    path('financeiro/', include('financeiro.urls')),
]