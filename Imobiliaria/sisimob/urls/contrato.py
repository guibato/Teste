from django.urls import path
from sisimob.views.contrato import (
    detalhes_contrato,
    excluir_contrato,
    reajustar_contratos,
    reajustar_contrato_individual,
    ContratoListView,
    ContratoCreateView,
    ContratoUpdateView,
    dashboard_contrato
)


urlpatterns_cbv = [
    path('cadastrar/', ContratoCreateView.as_view(), name='cadastrar_contrato'),
    path('listar/', ContratoListView.as_view(), name='listar_contratos'),
    path('editar/<int:contrato_id>/', ContratoUpdateView.as_view(), name='editar_contrato'),
    path('detalhes/<int:contrato_id>/', detalhes_contrato, name='detalhes_contrato'),
    path('excluir/<int:contrato_id>/', excluir_contrato, name='excluir_contrato'),
    path('reajustar/', reajustar_contratos, name='reajustar_contratos'),
    path('reajustar/<int:contrato_id>/', reajustar_contrato_individual, name='reajustar_contrato_individual'),
    path('dashboard/<int:id>/', dashboard_contrato, name='dashboard'),
]

# Use as FBV por padrão (descomente as CBV se preferir usar as Class Based Views)
urlpatterns = urlpatterns_cbv