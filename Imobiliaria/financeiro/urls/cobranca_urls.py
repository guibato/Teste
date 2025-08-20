# Solução: Remover app_name duplicado do cobranca_urls.py

# financeiro/urls/cobranca_urls.py - CORRIGIDO
"""
URLs para Cobranças - VERSÃO CORRIGIDA
======================================
URLs organizadas por categoria e fluxo de trabalho
"""

from django.urls import path
from ..views.cobranca_views import (
    # Views principais (CRUD)
    CobrancaListView,
    CobrancaCreateView,
    CobrancaUpdateView,
    CobrancaDetailView,
    
    # Views de ações individuais
    cobranca_marcar_paga,
    cobranca_cancelar,
    cobranca_integrar_asaas,
    
    # Views de preview e geração em lote
    cobranca_preview_geracao,
    cobranca_revisao_integracao,
    
    # Views de integração em lote
    cobranca_integrar_lote_asaas,
    
    # APIs AJAX
    cobranca_api_preview,
    cobranca_gerar_selecionadas,
    cobranca_api_despesas_contrato,
    cobranca_dashboard_stats,
    cobranca_webhook_asaas,
    cobranca_integrar_lote_asaas,
    asaas_dashboard,
    dashboard_data,
    integrar_lote,
    asaas_dashboard_data,
    asaas_integrar_lote,
    asaas_dashboard_data_simples,
    consultar_status_asaas
)

# REMOVIDO: app_name = 'financeiro'  <- ESTA LINHA CAUSAVA O CONFLITO

urlpatterns = [
    # ==========================================
    # URLS PRINCIPAIS (CRUD) - Fluxo Tradicional
    # ==========================================
    path('', CobrancaListView.as_view(), name='cobranca_list'),
    path('nova/', CobrancaCreateView.as_view(), name='cobranca_create'),
    path('<int:pk>/', CobrancaDetailView.as_view(), name='cobranca_detail'),
    path('<int:pk>/editar/', CobrancaUpdateView.as_view(), name='cobranca_update'),
    
    # ==========================================
    # AÇÕES INDIVIDUAIS - Fluxo Tradicional
    # ==========================================
    path('<int:pk>/marcar-paga/', cobranca_marcar_paga, name='cobranca_marcar_paga'),
    path('<int:pk>/cancelar/', cobranca_cancelar, name='cobranca_cancelar'),
    path('<int:pk>/integrar-asaas/', cobranca_integrar_asaas, name='cobranca_integrar_asaas'),
    
    # ==========================================
    # FLUXO PREVIEW/REVISÃO (Novo Sistema)
    # ==========================================
    path('preview/', cobranca_preview_geracao, name='cobranca_preview_geracao'),
    path('revisao/', cobranca_revisao_integracao, name='cobranca_revisao_integracao'),
    
    # ==========================================
    # OPERAÇÕES EM LOTE
    # ==========================================
    path('integrar-lote/', cobranca_integrar_lote_asaas, name='cobranca_integrar_lote_asaas'),
    
    # ==========================================
    # APIs AJAX
    # ==========================================
    # API para preview de cobranças
    path('api/preview/', cobranca_api_preview, name='cobranca_api_preview'),
    
    # API para gerar cobranças selecionadas
    path('api/gerar-selecionadas/', cobranca_gerar_selecionadas, name='cobranca_gerar_selecionadas'),
    
    # API para buscar despesas de contrato
    path('api/despesas-contrato/<int:contrato_id>/', cobranca_api_despesas_contrato, name='cobranca_api_despesas_contrato'),
    
    # API para estatísticas do dashboard
    path('api/dashboard-stats/', cobranca_dashboard_stats, name='cobranca_dashboard_stats'),
    
    # ==========================================
    # WEBHOOKS E INTEGRAÇÕES EXTERNAS
    # ==========================================
    path('webhook/asaas/', cobranca_webhook_asaas, name='cobranca_webhook_asaas'),
    path('asaas/dashboard/', asaas_dashboard, name='asaas_dashboard'),
    path('asaas/dashboard-data/', asaas_dashboard_data, name='asaas_dashboard_data'),
    path('asaas/integrar-lote/', asaas_integrar_lote, name='asaas_integrar_lote'),
    path('cobrancas/asaas/consultar-status/', consultar_status_asaas, name='consultar_status_asaas'),
    
]

# ==========================================
# EXPLICAÇÃO DO PROBLEMA RESOLVIDO
# ==========================================
"""
PROBLEMA:
- financeiro/urls/__init__.py tinha: app_name = 'financeiro'
- financeiro/urls/cobranca_urls.py também tinha: app_name = 'financeiro'
- Isso causava conflito de namespace

SOLUÇÃO:
- Manter app_name apenas no __init__.py
- Remover app_name dos arquivos incluídos
- Agora as URLs funcionam como 'financeiro:cobranca_create'

COMO USAR:
- No código: reverse('financeiro:cobranca_create')
- No template: {% url 'financeiro:cobranca_create' %}
"""