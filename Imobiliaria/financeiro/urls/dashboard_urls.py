# financeiro/urls/dashboard_urls.py
"""
URLs do dashboard financeiro - Versão Limpa
===========================================
"""

from django.urls import path
from ..views.dashboard_views import dashboard_view

urlpatterns = [
    path('', dashboard_view, name='dashboard'),
]