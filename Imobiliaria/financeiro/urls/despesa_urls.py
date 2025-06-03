# financeiro/urls/despesa_urls.py
"""
URLs para Despesas
=================
"""

from django.urls import path
from ..views.despesa_views import (
    DespesaListView,
    DespesaCreateView,
    DespesaUpdateView,
    DespesaDetailView,
    despesa_toggle_status,
    despesa_duplicar
)

urlpatterns = [
    # URLs principais (CRUD)
    path('', DespesaListView.as_view(), name='despesa_list'),
    path('nova/', DespesaCreateView.as_view(), name='despesa_create'),
    path('<int:pk>/', DespesaDetailView.as_view(), name='despesa_detail'),
    path('<int:pk>/editar/', DespesaUpdateView.as_view(), name='despesa_update'),
    
    # URLs para ações especiais
    path('<int:pk>/toggle-status/', despesa_toggle_status, name='despesa_toggle_status'),
    path('<int:pk>/duplicar/', despesa_duplicar, name='despesa_duplicar'),
]