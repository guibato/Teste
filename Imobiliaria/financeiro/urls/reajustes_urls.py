# financeiro/urls/reajustes_urls.py

from django.urls import path
from financeiro.views import reajuste_views

urlpatterns = [
    # Dashboard principal
    path('dashboard/', reajuste_views.dashboard_reajustes, name='dashboard_reajustes'),
    
    # Listagem e visualização
    path('', reajuste_views.lista_reajustes, name='reajustes_list'),
    path('sugestoes/', reajuste_views.sugestoes_reajustes, name='sugestoes_reajustes'),
    path('historico/<int:contrato_id>/', reajuste_views.historico_contrato, name='historico_contrato'),
    
    # Formulários e ações
    path('novo/', reajuste_views.form_reajuste, name='form_reajuste'),
    path('novo/<int:contrato_id>/', reajuste_views.form_reajuste, name='form_reajuste_contrato'),
    path('novo/<int:contrato_id>/<str:sugestao_data>/', reajuste_views.form_reajuste, name='form_reajuste_sugestao'),
    path('processar-lote/', reajuste_views.processar_reajustes_lote, name='processar_reajustes_lote'),
    
    # APIs
    path('api/calcular/', reajuste_views.api_calcular_reajuste, name='api_calcular_reajuste'),
    path('api/sugestao/<int:contrato_id>/', reajuste_views.api_sugestao_contrato, name='api_sugestao_contrato'),
    path('api/buscar-contratos/', reajuste_views.api_buscar_contratos, name='api_buscar_contratos'),
    path('api/excluir/<int:reajuste_id>/', reajuste_views.excluir_reajuste, name='excluir_reajuste'),
]