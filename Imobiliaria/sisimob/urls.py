from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),  # Rota para a página inicial
    path('logout/', views.logout_view, name='logout'),  # Rota para o logout
    path('buscar/', views.buscar, name='buscar'),
    path('cadastrar-cliente/', views.cadastrar_cliente, name='cadastro_cliente'),
    path('cadastrar-imovel/', views.cadastrar_imovel, name='cadastro_imovel'),
    path('cadastrar-contrato/', views.cadastrar_contrato, name='cadastro_contrato'),
    
    path('listar-clientes/', views.listar_clientes, name='listar_clientes'),
    path('listar-imoveis/', views.listar_imoveis, name='listar_imoveis'),
    path('listar-contratos/', views.listar_contratos, name='listar_contratos'),
    path('editar-cliente/<int:id>/', views.editar_cliente, name='editar_cliente'),
    path('confirmar-exclusao/<str:model_name>/<int:id>/', views.confirmar_exclusao, name='confirmar_exclusao'),
    path('cadastrar-imovel/', views.cadastrar_imovel, name='cadastro_imovel'),
    path('editar-imovel/<int:id>/', views.editar_imovel, name='editar_imovel'),
    path('listar-imoveis/', views.listar_imoveis, name='listar_imoveis'),
    path('sucesso/', views.sucesso, name='sucesso'),

]