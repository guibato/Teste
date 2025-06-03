# financeiro/urls/movimentos_urls.py
from django.urls import path
from financeiro.views import movimento_views

urlpatterns = [
    path('dashboard/', movimento_views.dashboard_financeiro, name='dashboard_financeiro'),
    path('saldos/', movimento_views.lista_saldos, name='lista_saldos'),
    path('extrato/<int:proprietario_id>/', movimento_views.extrato_proprietario, name='extrato_proprietario'),
    path('lancamento/<int:proprietario_id>/', movimento_views.lancamento_manual, name='lancamento_manual'),
    path('ajuste/<int:proprietario_id>/', movimento_views.ajuste_saldo, name='ajuste_saldo'),
    path('exportar/<int:proprietario_id>/', movimento_views.exportar_extrato, name='exportar_extrato'),
    path('conciliacao/<int:proprietario_id>/', movimento_views.conciliacao_bancaria, name='conciliacao_bancaria'),
    path('api/contratos/<int:proprietario_id>/', movimento_views.contratos_proprietario_api, name='contratos_proprietario_api'),
]