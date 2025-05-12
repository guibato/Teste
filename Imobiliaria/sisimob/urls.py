from django.urls import path
from . import views
from .views import ListarContratosView, atualizar_indices_view
from django.conf import settings
from django.conf.urls.static import static
from .views import listar_indices_inflacao, gerar_extrato_rendimento, gerar_cobrancas_view, extrato_repasses_pdf

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
    path('editar-imovel/<int:id>/', views.editar_imovel, name='editar_imovel'),
    path('sucesso/', views.sucesso, name='sucesso'),
    path('listar_contratos/', views.ListarContratosView.as_view(), name='listar_contratos'),
    path('atualizar-indices/', atualizar_indices_view, name='atualizar_indices'),
    path('contratos/editar/<int:contrato_id>/', views.editar_contrato, name='editar_contrato'),
    path('nacionalidade-autocomplete/', views.nacionalidade_autocomplete, name='nacionalidade-autocomplete'),
    path('autocomplete/<str:model_name>/<str:field_name>/', views.autocomplete_field, name='autocomplete_field'),
    path('cobrancas/<int:pk>/update/', views.cobranca_update, name='cobranca_update'),
    path('cobranca/<int:pk>/pagar/', views.pagar_cobranca, name='pagar_cobranca'),
    path('cobranca/<int:pk>/recibo/', views.gerar_recibo_pagamento, name='gerar_recibo_pagamento'),
    path('cobranca/<int:pk>/repasse/', views.repassar_valor, name='repasse_valor'),
    path('cobrancas/<int:pk>/atualizar-datas/', views.atualizar_datas_cobranca, name='atualizar_datas_cobranca'),
    path('indices-inflacao/', listar_indices_inflacao, name='listar_indices_inflacao'),
    path('extrato-rendimento/<int:contrato_id>/', gerar_extrato_rendimento, name='gerar_extrato_rendimento'),
    path('despesa/editar/<int:pk>/', views.editar_despesa, name='editar_despesa'),
    path('dashboard/<int:id>/', views.dashboard, name='dashboard'),
    path("atualizar-indices/", atualizar_indices_view, name="atualizar_indices"),
    path('cobranca/editar/<int:pk>/', views.editar_cobranca, name='editar_cobranca'),
    path('excluir-cobranca/<int:pk>/', views.excluir_cobranca, name='excluir_cobranca'),
    path('marcar-como-recebida/<int:pk>/', views.marcar_como_recebida, name='marcar_como_recebida'),
    path('marcar-como-repassada/<int:pk>/', views.marcar_como_repassada, name='marcar_como_repassada'),
    path('atualizar-datas/<int:pk>/', views.atualizar_datas_cobranca, name='atualizar_datas_cobranca'),
    path("gerar-cobrancas/", views.gerar_cobrancas_view, name="cadastro_cobrancas"),
    path('lancar-despesa/<int:id>/', views.lancar_despesa, name='lancar_despesa'),
    path('editar-despesa/<int:id>/', views.editar_despesa, name='editar_despesa'),
    path('excluir-despesa/<int:id>/', views.excluir_despesa, name='excluir_despesa'),
    path('executar-cobrancas/', gerar_cobrancas_view, name='executar_cobrancas'),
    path('extrato/', views.extrato, name='extrato'),
    path('proprietarios/<int:proprietario_id>/extrato-repasses/pdf/', views.extrato_repasses_pdf, name='extrato_repasses_pdf'),
    path('gerar-pdf/<int:contrato_id>/', views.gerar_pdf, name='gerar_pdf'),
    path('reajustar-contratos/', views.reajustar_contratos, name='reajustar_contratos'),
    path('reajustar-contrato/<int:contrato_id>/', views.reajustar_contrato_individual, name='reajustar_contrato_individual'),
    path('mensagens-cobranca/', views.visualizar_mensagens_cobranca, name='visualizar_mensagens'),
    path('mensagens-cobranca/enviar/', views.enviar_mensagens_cobranca, name='enviar_mensagens_cobranca'),
    path('confirmar-cobrancas/', views.confirmar_cobrancas_view, name='confirmar_cobrancas'),
    path('painel/', views.painel_financeiro, name='painel_financeiro'),
    path('acao-em-lote/', views.acao_em_lote, name='acao_em_lote'),
    
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)