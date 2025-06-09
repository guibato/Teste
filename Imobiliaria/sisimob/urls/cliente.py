from django.urls import path
from sisimob.views.cliente import (
    
    detalhes_cliente,
    
    ClienteListView,
    ClienteCreateView,
    ClienteUpdateView,
    ClienteDeleteView
)

# URLs usando Function Based Views (FBV)


# URLs usando Class Based Views (CBV) - alternativa moderna
urlpatterns_cbv = [
    path('cadastrar/', ClienteCreateView.as_view(), name='cadastro_cliente'),
    path('listar/', ClienteListView.as_view(), name='listar_clientes'),
    path('editar/<int:pk>/', ClienteUpdateView.as_view(), name='editar_cliente'),
    path('detalhes/<int:id>/', detalhes_cliente, name='detalhes_cliente'),
    path('excluir/<int:pk>/', ClienteDeleteView.as_view(), name='excluir_cliente'),
]

# Use as FBV por padrão (descomente as CBV se preferir usar as Class Based Views)

urlpatterns = urlpatterns_cbv