from django.contrib import admin
from .models import Cobranca

@admin.register(Cobranca)
class CobrancaAdmin(admin.ModelAdmin):
    list_display = (
        'contrato', 
        'mes_referencia', 
        'ano_referencia', 
        'valor', 
        'status', 
        'status_repasse', 
        'data_pagamento', 
        'data_repasse'
    )
    list_filter = ('status', 'status_repasse', 'data_vencimento')
    search_fields = ('contrato__imovel__endereco',)