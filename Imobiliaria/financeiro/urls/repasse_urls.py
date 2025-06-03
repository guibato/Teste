# financeiro/urls.py (adicionar ao existente)
from django.urls import path, include
from financeiro.views import repasse_views

app_name = 'financeiro'

# URLs de Repasses
repasse_patterns = [
    path('', repasse_views.RepasseListView.as_view(), name='repasse_list'),
    path('novo/', repasse_views.RepasseCreateView.as_view(), name='repasse_create'),
    path('<int:pk>/', repasse_views.RepasseDetailView.as_view(), name='repasse_detail'),
    path('<int:pk>/editar/', repasse_views.RepasseUpdateView.as_view(), name='repasse_update'),
    path('<int:repasse_id>/processar/', repasse_views.processar_repasse_view, name='processar_repasse'),
    path('<int:repasse_id>/cancelar/', repasse_views.cancelar_repasse_view, name='cancelar_repasse'),
    path('extrato/<int:proprietario_id>/', repasse_views.extrato_proprietario_view, name='extrato_proprietario'),
    path('dashboard/ajax/', repasse_views.dashboard_repasses_ajax, name='dashboard_repasses_ajax'),
    path('gerar-automatico/', repasse_views.gerar_repasse_automatico, name='gerar_repasse_automatico'),
    
    # Políticas de Repasse
    path('politicas/', repasse_views.PoliticaRepasseListView.as_view(), name='politica_list'),
    path('politicas/nova/', repasse_views.PoliticaRepasseCreateView.as_view(), name='politica_create'),
    path('politicas/<int:pk>/editar/', repasse_views.PoliticaRepasseUpdateView.as_view(), name='politica_update'),
    
    # Agendamentos
    path('agendamentos/', repasse_views.AgendamentoListView.as_view(), name='agendamento_list'),
    path('agendamentos/<int:pk>/processar/', repasse_views.processar_agendamento_view, name='processar_agendamento'),
]

urlpatterns = [
    # ... outras URLs existentes
    path('repasses/', include(repasse_patterns)),
]