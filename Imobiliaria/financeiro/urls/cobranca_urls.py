# financeiro/urls/cobranca_urls.py
"""
URLs para Cobranças
==================
"""

from django.urls import path
from ..views.cobranca_views import (
    CobrancaListView,
    CobrancaCreateView,
    CobrancaUpdateView,
    CobrancaDetailView,
    cobranca_integrar_asaas,
    cobranca_marcar_paga,
    cobranca_cancelar,
    cobranca_gerar_lote,
    cobranca_api_despesas_contrato
)

from ..views.cobranca_preview_views import (
    cobranca_preview_geracao,
    cobranca_api_preview,
    cobranca_gerar_selecionadas,
    cobranca_revisao_integracao,
    cobranca_integrar_lote_asaas
)

urlpatterns = [
    # URLs principais (CRUD) - Fluxo Tradicional
    path('', CobrancaListView.as_view(), name='cobranca_list'),
    path('nova/', CobrancaCreateView.as_view(), name='cobranca_create'),
    path('<int:pk>/', CobrancaDetailView.as_view(), name='cobranca_detail'),
    path('<int:pk>/editar/', CobrancaUpdateView.as_view(), name='cobranca_update'),
    
    # URLs para ações especiais - Fluxo Tradicional
    path('<int:pk>/integrar-asaas/', cobranca_integrar_asaas, name='cobranca_integrar_asaas'),
    path('<int:pk>/marcar-paga/', cobranca_marcar_paga, name='cobranca_marcar_paga'),
    path('<int:pk>/cancelar/', cobranca_cancelar, name='cobranca_cancelar'),
    
    # URLs para operações em lote - Fluxo Tradicional
    path('gerar-lote/', cobranca_gerar_lote, name='cobranca_gerar_lote'),
    
    # URLs para Fluxo Preview/Revisão (Novo)
    path('preview/', cobranca_preview_geracao, name='cobranca_preview_geracao'),
    path('revisao/', cobranca_revisao_integracao, name='cobranca_revisao_integracao'),
    
    # APIs AJAX
    path('api/despesas-contrato/<int:contrato_id>/', cobranca_api_despesas_contrato, name='cobranca_api_despesas_contrato'),
    path('api/preview/', cobranca_api_preview, name='cobranca_api_preview'),
    path('api/gerar-selecionadas/', cobranca_gerar_selecionadas, name='cobranca_gerar_selecionadas'),
    path('api/integrar-lote/', cobranca_integrar_lote_asaas, name='cobranca_integrar_lote_asaas'),
]