# Importações dos formulários de Cliente
from .cliente import (
    ClienteForm,
    ClienteFiltroForm,
    ClienteBuscaForm
)

# Importações dos formulários de Imóvel
from .imovel import (
    ImovelForm,
    ImovelFiltroForm,
    ImovelBuscaForm
)

# Importações dos formulários de Contrato
from .contrato import (
    ContratoForm,
    ContratoFiltroForm,
    ReajusteContratosForm
)



# Lista de todos os formulários para facilitar importações
__all__ = [
    # Cliente
    'ClienteForm',
    'ClienteFiltroForm', 
    'ClienteBuscaForm',
    
    # Imóvel
    'ImovelForm',
    'ImovelFiltroForm',
    'ImovelBuscaForm',
    
    # Contrato
    'ContratoForm',
    'ContratoFiltroForm',
    'ReajusteContratosForm',
    ]