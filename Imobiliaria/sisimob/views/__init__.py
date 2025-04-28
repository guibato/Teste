# Import all views from their respective modules
from .cliente_views import *
from .imovel_views import *
from .contrato_views import *
from .cobranca_views import *
from .core_views import *

# This allows importing views directly from sisimob.views
# Example: from sisimob.views import cadastrar_cliente, listar_imoveis

__all__ = [
    # Cliente views
    'cadastrar_cliente', 'listar_clientes', 'editar_cliente', 'nacionalidade_autocomplete',

    # Imovel views
    'cadastrar_imovel', 'listar_imoveis', 'editar_imovel',

    # Contrato views
    'ListarContratosView', 'cadastrar_contrato', 'editar_contrato', 'dashboard',
    'gerar_pdf', 'gerar_extrato_rendimento',

    # Cobranca views
    'lista_cobrancas', 'gerar_cobrancas_view', 'editar_cobranca', 'excluir_cobranca',
    'marcar_como_recebida', 'marcar_como_repassada', 'cobranca_update', 'pagar_cobranca',
    'repassar_valor', 'atualizar_datas_cobranca', 'gerar_recibo_pagamento',

    # Core views
    'home', 'logout_view', 'buscar', 'sucesso', 'autocomplete_field', 'confirmar_exclusao',
    'atualizar_indices_view', 'extrato', 'extrato_repasses_pdf',
]
