# financeiro/urls/lembretes_urls.py
from django.urls import path
from financeiro.views import lembrete_views

urlpatterns = [
    path('', lembrete_views.lembrete_list, name='lembrete_list'),
    path('<int:pk>/', lembrete_views.lembrete_detail, name='lembrete_detail'),
    path('configuracao/', lembrete_views.configuracao_lembretes, name='configuracao_lembretes'),
    path('envio-manual/', lembrete_views.envio_manual, name='envio_manual'),
    path('dashboard/', lembrete_views.dashboard_lembretes, name='dashboard_lembretes'),
    path('api/cobrancas-pendentes/', lembrete_views.cobrancas_pendentes_api, name='cobrancas_pendentes_api'),
    path('envio-programado/', lembrete_views.envio_programado, name='envio_programado'),
]