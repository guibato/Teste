# financeiro/views/__init__.py
"""
Views do app financeiro
======================

Importa e organiza todas as views dos sub-módulos.
"""

# Importar views do dashboard
from .dashboard_views import dashboard_view

# Importar views dos tipos de despesa
from .tipodespesa_views import (
    TipoDespesaListView,
    TipoDespesaCreateView,
    TipoDespesaUpdateView,
    TipoDespesaDetailView,
    tipodespesa_toggle_status,
    tipodespesa_check_uso
)

# Fazer as views disponíveis quando importar o módulo views
__all__ = [
    # Dashboard
    'dashboard_view',
    
    # Tipo Despesa
    'TipoDespesaListView',
    'TipoDespesaCreateView', 
    'TipoDespesaUpdateView',
    'TipoDespesaDetailView',
    'tipodespesa_toggle_status',
    'tipodespesa_check_uso',
]

# ============================================================================