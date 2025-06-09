from django.urls import path
from sisimob.views.imovel import (  # Importar views de IMÓVEL, não cliente
    detalhes_imovel,
    ImovelListView,
    ImovelCreateView,
    ImovelUpdateView,
    ImovelDeleteView,
    buscar_cep
)

# URLs usando Class Based Views (CBV) para IMÓVEIS
urlpatterns_cbv = [
    path('cadastrar/', ImovelCreateView.as_view(), name='cadastrar_imovel'),
    path('listar/', ImovelListView.as_view(), name='listar_imoveis'),
    path('editar/<int:pk>/', ImovelUpdateView.as_view(), name='editar_imovel'),
    path('detalhes/<int:id>/', detalhes_imovel, name='detalhes_imovel'),
    path('excluir/<int:pk>/', ImovelDeleteView.as_view(), name='excluir_imovel'),
    path('buscar-cep/', buscar_cep, name='buscar_cep'),  # URL para AJAX do CEP
]

urlpatterns = urlpatterns_cbv