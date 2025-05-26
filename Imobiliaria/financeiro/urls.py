from django.urls import path
from . import views


urlpatterns = [
    path('cobrancas/', views.listar_cobrancas, name='listar_cobrancas'),
    path('cobrancas/nova/', views.criar_cobranca, name='criar_cobranca'),
    path('cobrancas/<int:pk>/', views.detalhe_cobranca, name='detalhe_cobranca'),
    path('cobrancas/<int:pk>/editar/', views.editar_cobranca, name='editar_cobranca'),
    path('cobrancas/<int:pk>/excluir/', views.excluir_cobranca, name='excluir_cobranca'),
    path('cobrancas/<int:pk>/pagar/', views.registrar_pagamento, name='registrar_pagamento'),
    path('cobrancas/<int:pk>/recibo/', views.gerar_recibo_pagamento, name='gerar_recibo_pagamento'),
    path('cobrancas/<int:pk>/lembretes/', views.lembretes_enviados_por_cobranca, name='lembretes_por_cobranca'),
    path('cobrancas/gerar/', views.gerar_cobrancas, name='cadastro_cobrancas'),
    path('despesas/cadastrar/', views.cadastrar_despesa, name='cadastrar_despesa'),
    path('despesas/cadastrar/<int:contrato_id>/', views.cadastrar_despesa, name='cadastrar_despesa'),
    path('despesas/', views.listar_despesas, name='listar_despesas'),
    path('despesas/editar/<int:pk>/', views.editar_despesa, name='editar_despesa'),
    path('despesas/excluir/<int:pk>/', views.excluir_despesa, name='excluir_despesa'),
    path('tipos-despesa/', views.listar_tipos_despesa, name='listar_tipos_despesa'),
    path('tipos-despesa/novo/', views.cadastrar_tipo_despesa, name='cadastrar_tipo_despesa'),
    path('tipos-despesa/<int:pk>/editar/', views.editar_tipo_despesa, name='editar_tipo_despesa'),
    path('reajustes/', views.listar_contratos_para_reajuste, name='listar_reajustes'),
    path('reajuste/<int:contrato_id>/', views.reajustar_contrato, name='reajustar_contrato'),
    path('atualizar-indices/', views.atualizar_indices_view, name='atualizar_indices'),
]
