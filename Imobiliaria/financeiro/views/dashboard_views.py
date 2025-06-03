# financeiro/views/dashboard_views.py
"""
Views do Dashboard Financeiro - Versão Limpa
============================================
"""

from django.shortcuts import render
from ..models import TipoDespesa


def dashboard_view(request):
    """
    Dashboard principal do módulo financeiro
    """
    context = {
        'titulo': 'Dashboard Financeiro',
        'total_tipos_despesa': TipoDespesa.objects.filter(ativo=True).count(),
    }
    return render(request, 'financeiro/dashboard.html', context)