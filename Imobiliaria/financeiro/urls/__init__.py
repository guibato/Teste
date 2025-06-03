# financeiro/urls/__init__.py - VERSÃO CORRIGIDA
"""
URLs principais do app financeiro
================================
"""

from django.urls import path, include

app_name = 'financeiro'

urlpatterns = [
    # Dashboard financeiro
    path('', include('financeiro.urls.dashboard_urls')),
    
    # URLs dos tipos de despesa
    path('tipos-despesa/', include('financeiro.urls.tipodespesa_urls')),
    
    # URLs das despesas
    path('despesas/', include('financeiro.urls.despesa_urls')),
    
    # URLs das cobranças
    path('cobrancas/', include('financeiro.urls.cobranca_urls')),
    
    # URLs dos índices
    path('indices/', include('financeiro.urls.indices_urls')),

    # URLs dos reajustes
    path('reajustes/', include('financeiro.urls.reajustes_urls')),

    # URLs dos repasses
    path('repasses/', include('financeiro.urls.repasse_urls')),

    # URLs dos lembretes - NOVO
    path('lembretes/', include('financeiro.urls.lembretes_urls')),

    # URLs dos movimentos - NOVO
    path('movimentos/', include('financeiro.urls.movimentos_urls')),
]