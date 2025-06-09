# financeiro/urls.py (versão consolidada)
from django.urls import path, include
from financeiro.views import repasse_views



# URLs de Repasses Consolidadas
urlpatterns = [
    # ==================== URLS PRINCIPAIS (CRUD) ====================
    path('', repasse_views.RepasseListView.as_view(), name='lista_repasses'),
    path('lista/', repasse_views.RepasseListView.as_view(), name='lista_repasses_alt'),  # URL alternativa
    path('novo/', repasse_views.RepasseCreateView.as_view(), name='repasse_create'),
    path('<int:pk>/', repasse_views.RepasseDetailView.as_view(), name='repasse_detail'),
    path('<int:pk>/editar/', repasse_views.RepasseUpdateView.as_view(), name='repasse_update'),
    
    # ==================== URLS DE PROCESSAMENTO ====================
    path('<int:repasse_id>/processar/', repasse_views.processar_repasse_view, name='processar_repasse'),
    path('<int:repasse_id>/cancelar/', repasse_views.cancelar_repasse_view, name='cancelar_repasse'),
    path('gerar-automatico/', repasse_views.gerar_repasse_automatico, name='gerar_repasse_automatico'),
    
    # ==================== URLS DE POLÍTICAS POR CONTRATO ====================
    path('politicas/contrato/', repasse_views.PoliticaContratoListView.as_view(), name='politica_contrato_list'),
    path('politicas/contrato/nova/', repasse_views.PoliticaContratoCreateView.as_view(), name='politica_contrato_create'),
    path('politicas/contrato/<int:pk>/editar/', repasse_views.PoliticaContratoUpdateView.as_view(), name='politica_contrato_update'),
    path('politicas/contrato/<int:pk>/toggle/', repasse_views.toggle_politica_contrato_view, name='toggle_politica_contrato'),
    path('politicas/contrato/<int:pk>/testar/', repasse_views.testar_politica_contrato_view, name='testar_politica_contrato'),
    
    # ==================== URLS DE POLÍTICAS GLOBAIS ====================
    path('politicas/global/', repasse_views.PoliticaGlobalListView.as_view(), name='politica_global_list'),
    path('politicas/global/nova/', repasse_views.PoliticaGlobalCreateView.as_view(), name='politica_global_create'),
    path('politicas/global/<int:pk>/editar/', repasse_views.PoliticaGlobalUpdateView.as_view(), name='politica_global_update'),
    
    # ==================== URLS DE CONTRATOS ====================
    path('contratos/sem-politica/', repasse_views.ContratosSemPoliticaView.as_view(), name='contratos_sem_politica'),
    path('contratos/aplicar-politica-lote/', repasse_views.aplicar_politica_em_lote, name='aplicar_politica_lote'),
    
    # ==================== URLS DE AGENDAMENTOS ====================
    path('agendamentos/', repasse_views.AgendamentoListView.as_view(), name='agendamento_list'),
    path('agendamentos/<int:pk>/processar/', repasse_views.processar_agendamento_view, name='processar_agendamento'),
    path('agendamentos/processar-vencidos/', repasse_views.processar_agendamentos_vencidos, name='processar_agendamentos_vencidos'),
    
    # ==================== URLS DE DASHBOARD E CONFIGURAÇÕES ====================
    path('dashboard/', repasse_views.DashboardFinanceiroView.as_view(), name='dashboard_financeiro'),
    path('configuracoes/', repasse_views.ConfiguracaoRepasseView.as_view(), name='configuracao_repasse'),
    
    # ==================== URLS DE HISTÓRICO E EXTRATOS ====================
    path('historico/<int:proprietario_id>/', repasse_views.repasse_historico_proprietario, name='historico_proprietario'),
    path('extrato/<int:proprietario_id>/', repasse_views.extrato_proprietario_view, name='extrato_proprietario'),
    
    # ==================== URLS DE RELATÓRIOS ====================
    path('relatorio/', repasse_views.relatorio_repasses_view, name='relatorio_repasses'),
    path('relatorio/exportar/', repasse_views.exportar_relatorio_repasses, name='exportar_relatorio_repasses'),
    
    # ==================== APIS AJAX ====================
    path('ajax/dashboard/', repasse_views.dashboard_repasses_ajax, name='dashboard_repasses_ajax'),
    path('ajax/search/', repasse_views.repasse_ajax_search, name='repasse_ajax_search'),
    path('ajax/cobrancas/', repasse_views.cobranca_ajax_search, name='cobranca_ajax_search'),
    path('ajax/calcular-valores/', repasse_views.calcular_valores_repasse, name='calcular_valores_repasse'),
    
    # ==================== URLS DE UTILITÁRIOS ====================
    path('migrar-politicas/', repasse_views.migrar_politicas_antigas, name='migrar_politicas'),

    path('automacao/dashboard/', repasse_views.DashboardAutomacaoView.as_view(), name='dashboard_automacao'),
path('automacao/diagnostico/', repasse_views.diagnostico_automacao, name='diagnostico_automacao'),
path('automacao/processar/', repasse_views.gerar_repasse_automatico, name='processar_automatico'),
path('ajax/automacao/dashboard/', repasse_views.dashboard_automacao_ajax, name='dashboard_automacao_ajax'),
path('ajax/repasse/<int:repasse_id>/processar/', repasse_views.processar_repasse_unico, name='processar_repasse_unico'),
]



# ==================== URLS PARA REFERÊNCIA RÁPIDA ====================
"""
ESTRUTURA DE URLs ORGANIZADAS:

1. REPASSES BÁSICOS:
   - /repasses/ → Lista de repasses
   - /repasses/novo/ → Criar novo repasse
   - /repasses/{id}/ → Detalhes do repasse
   - /repasses/{id}/editar/ → Editar repasse
   - /repasses/{id}/processar/ → Processar repasse
   - /repasses/{id}/cancelar/ → Cancelar repasse

2. POLÍTICAS POR CONTRATO:
   - /repasses/politicas/contrato/ → Lista políticas por contrato
   - /repasses/politicas/contrato/nova/ → Nova política para contrato
   - /repasses/politicas/contrato/{id}/editar/ → Editar política de contrato
   - /repasses/politicas/contrato/{id}/toggle/ → Ativar/desativar política
   - /repasses/politicas/contrato/{id}/testar/ → Testar política

3. POLÍTICAS GLOBAIS:
   - /repasses/politicas/global/ → Lista políticas globais
   - /repasses/politicas/global/nova/ → Nova política global
   - /repasses/politicas/global/{id}/editar/ → Editar política global

4. CONTRATOS:
   - /repasses/contratos/sem-politica/ → Contratos sem política
   - /repasses/contratos/aplicar-politica-lote/ → Aplicar política em lote

5. AGENDAMENTOS:
   - /repasses/agendamentos/ → Lista agendamentos
   - /repasses/agendamentos/{id}/processar/ → Processar agendamento
   - /repasses/agendamentos/processar-vencidos/ → Processar vencidos

6. DASHBOARD E RELATÓRIOS:
   - /repasses/dashboard/ → Dashboard financeiro
   - /repasses/configuracoes/ → Configurações gerais
   - /repasses/relatorio/ → Página de relatórios
   - /repasses/relatorio/exportar/ → Exportar relatório

7. HISTÓRICO:
   - /repasses/historico/{proprietario_id}/ → Histórico do proprietário
   - /repasses/extrato/{proprietario_id}/ → Extrato do proprietário

8. AJAX APIs:
   - /repasses/ajax/dashboard/ → Dados para gráficos
   - /repasses/ajax/search/ → Busca autocomplete
   - /repasses/ajax/cobrancas/ → Busca cobranças
   - /repasses/ajax/calcular-valores/ → Cálculo de valores

NAVEGAÇÃO RECOMENDADA:
1. Comece pelo dashboard: /repasses/dashboard/
2. Configure políticas: /repasses/politicas/contrato/
3. Veja contratos sem política: /repasses/contratos/sem-politica/
4. Gerencie repasses: /repasses/
5. Monitore agendamentos: /repasses/agendamentos/
"""