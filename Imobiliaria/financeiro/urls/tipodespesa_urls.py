# financeiro/urls/tipodespesa_urls.py
"""
URLs para Tipos de Despesa - Versão Limpa
=========================================
"""

from django.urls import path
from ..views.tipodespesa_views import (
    TipoDespesaListView,
    TipoDespesaCreateView,
    TipoDespesaUpdateView,
    TipoDespesaDetailView,
    tipodespesa_toggle_status,
    tipodespesa_check_uso
)

urlpatterns = [
    path('', TipoDespesaListView.as_view(), name='tipodespesa_list'),
    path('novo/', TipoDespesaCreateView.as_view(), name='tipodespesa_create'),
    path('<int:pk>/', TipoDespesaDetailView, name='tipodespesa_detail'),
    path('<int:pk>/editar/', TipoDespesaUpdateView.as_view(), name='tipodespesa_update'),
    path('<int:pk>/toggle-status/', tipodespesa_toggle_status, name='tipodespesa_toggle_status'),
    path('<int:pk>/check-uso/', tipodespesa_check_uso, name='tipodespesa_check_uso'),
]