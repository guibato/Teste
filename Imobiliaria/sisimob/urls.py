from django.urls import path
from . import views
from .views import ListarContratosView
from .views import atualizar_indices_view  # Importe a função aqui
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.home, name='home'),  # Rota para a página inicial
    path('logout/', views.logout_view, name='logout'),  # Rota para o logout
    path('buscar/', views.buscar, name='buscar'),
    path('cadastrar-cliente/', views.cadastrar_cliente, name='cadastro_cliente'),
    path('cadastrar-imovel/', views.cadastrar_imovel, name='cadastro_imovel'),
    path('cadastrar-contrato/', views.cadastrar_contrato, name='cadastro_contrato'),
    path('listar-clientes/', views.listar_clientes, name='listar_clientes'),
    path('listar-imoveis/', views.listar_imoveis, name='listar_imoveis'),
    path('editar-cliente/<int:id>/', views.editar_cliente, name='editar_cliente'),
    path('confirmar-exclusao/<str:model_name>/<int:id>/', views.confirmar_exclusao, name='confirmar_exclusao'),
    path('cadastrar-imovel/', views.cadastrar_imovel, name='cadastro_imovel'),
    path('editar-imovel/<int:id>/', views.editar_imovel, name='editar_imovel'),
    path('listar-imoveis/', views.listar_imoveis, name='listar_imoveis'),
    path('sucesso/', views.sucesso, name='sucesso'),
    path('listar_contratos/', views.ListarContratosView.as_view(), name='listar_contratos'),
    path('atualizar-indices/', atualizar_indices_view, name='atualizar_indices'),
    path('dashboard/<int:contrato_id>/', views.dashboard, name='dashboard'),
    path('contratos/editar/<int:contrato_id>/', views.editar_contrato, name='editar_contrato'),
    path('listar-clientes/', views.listar_clientes, name='listar_clientes'),
    path('listar-imoveis/', views.listar_imoveis, name='listar_imoveis'),
    path('listar-contratos/', ListarContratosView.as_view(), name='listar_contratos'),
    path('nacionalidade-autocomplete/', views.nacionalidade_autocomplete, name='nacionalidade-autocomplete'),
    path('autocomplete/<str:model_name>/<str:field_name>/', views.autocomplete_field, name='autocomplete_field'),
    path(
        'cobrancas/<int:pk>/update/',
        views.cobranca_update,
        name='cobranca_update'  # Nome da URL deve ser EXATAMENTE 'cobranca_update'
    ),
    path('cobranca/<int:pk>/pagar/', views.pagar_cobranca, name='pagar_cobranca'),
    path('cobranca/<int:pk>/recibo/', views.gerar_recibo_pagamento, name='gerar_recibo_pagamento'),
    path('cobranca/<int:pk>/repasse/', views.repassar_valor, name='repasse_valor'),
    path('contrato/<int:contrato_id>/', views.detalhes_contrato, name='detalhes_contrato'),


]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)