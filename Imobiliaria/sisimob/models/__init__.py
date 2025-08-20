# Importações dos modelos base
from .base import TimestampedModel

# Importações dos modelos principais
from .cliente import Cliente
from .imovel import Imovel
from sisimob.models.contrato import Contrato


# Lista de todos os modelos para facilitar importações
__all__ = [
    
    'TimestampedModel',
    'Cliente',
    'Imovel',
    'Contrato',
]