from django.urls import path, include

app_name = 'sisimob'

urlpatterns = [
    # Página inicial e views básicas
    path('', include('sisimob.urls.base_urls')),
    
    # URLs de clientes
    path('clientes/', include('sisimob.urls.cliente')),
    
    # URLs de imóveis
    path('imoveis/', include('sisimob.urls.imovel')),
    
    # URLs de contratos
    path('contratos/', include('sisimob.urls.contrato')),
]