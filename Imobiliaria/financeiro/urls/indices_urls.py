# financeiro/urls/indices_urls.py
"""
URLs para Índices de Inflação
============================
"""

from django.urls import path
from ..views.indice_views import (
    IndiceListView,
    IndiceCreateView,
    IndiceUpdateView,
    atualizar_indices_api
)

urlpatterns = [
    # URLs principais (CRUD)
    path('', IndiceListView.as_view(), name='indice_list'),
    path('novo/', IndiceCreateView.as_view(), name='indice_create'),
    path('<int:pk>/editar/', IndiceUpdateView.as_view(), name='indice_update'),
    
    # API
    path('atualizar-api/', atualizar_indices_api, name='atualizar_indices_api'),
]