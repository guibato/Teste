# Importações das views base
from .base import (
    home,
    logout_view,
    buscar,
    sucesso,
    autocomplete_field,
    nacionalidade_autocomplete,
    confirmar_exclusao
)

# Importações das views de Cliente
from .cliente import (
    detalhes_cliente,
    ClienteListView,
    ClienteCreateView,
    ClienteUpdateView,
    ClienteDeleteView
)

# Importações das views de Imóvel
from .imovel import (
    
    detalhes_imovel,
    
    buscar_cep,
    ImovelListView,
    ImovelCreateView,
    ImovelUpdateView,
    ImovelDeleteView
)

# Importações das views de Contrato
from .contrato import (
    cadastrar_contrato,
    listar_contratos,
    editar_contrato,
    detalhes_contrato,
    excluir_contrato,
    reajustar_contratos,
    reajustar_contrato_individual,
    calcular_fator_acumulado,
    ContratoListView,
    ContratoCreateView,
    ContratoUpdateView
)

# Lista de todas as views para facilitar importações
__all__ = [
    # Views base
    'home',
    'logout_view',
    'buscar',
    'sucesso',
    'autocomplete_field',
    'nacionalidade_autocomplete',
    'confirmar_exclusao',
    
    # Cliente - Function Based Views
    'cadastrar_cliente',
    'listar_clientes',
    'editar_cliente',
    'detalhes_cliente',
    'excluir_cliente',
    
    # Cliente - Class Based Views
    'ClienteListView',
    'ClienteCreateView',
    'ClienteUpdateView',
    'ClienteDeleteView',
    
    # Imóvel - Function Based Views
    'cadastrar_imovel',
    'listar_imoveis',
    'editar_imovel',
    'detalhes_imovel',
    'excluir_imovel',
    'buscar_cep',
    
    # Imóvel - Class Based Views
    'ImovelListView',
    'ImovelCreateView',
    'ImovelUpdateView',
    'ImovelDeleteView',
    
    # Contrato - Function Based Views
    'cadastrar_contrato',
    'listar_contratos',
    'editar_contrato',
    'detalhes_contrato',
    'excluir_contrato',
    'reajustar_contratos',
    'reajustar_contrato_individual',
    'calcular_fator_acumulado',
    
    # Contrato - Class Based Views
    'ContratoListView',
    'ContratoCreateView',
    'ContratoUpdateView',
]