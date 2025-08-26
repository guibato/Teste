from django.urls import path, include

app_name = 'core'

urlpatterns = [
    # Página inicial e views básicas
    path('', include('core.urls.base_urls')),
    
    # URLs de clientes
    path('clientes/', include('core.urls.cliente')),
    
    # URLs de imóveis
    path('imoveis/', include('core.urls.imovel')),
    
    # URLs de contratos
    path('contratos/', include('core.urls.contrato')),
]