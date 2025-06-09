# financeiro/admin.py
from django.contrib import admin
from .models import (
    Cobranca, Despesa, IndiceInflacao, Repasse,
    PoliticaRepasseContrato, PoliticaRepasseGlobal, AgendamentoRepasse,
    MovimentoConta, SaldoProprietario, LembreteEnviado
)

@admin.register(Cobranca)
class CobrancaAdmin(admin.ModelAdmin):
    list_display = ('contrato', 'mes_referencia', 'ano_referencia', 'valor_total', 'status', 'data_vencimento')
    list_filter = ('status', 'mes_referencia', 'ano_referencia')
    search_fields = ('contrato__id', 'inquilino__nome')

@admin.register(Despesa)
class DespesaAdmin(admin.ModelAdmin):
    list_display = ('tipo', 'contrato', 'valor_total', 'paga_por', 'numero_parcelas', 'data_inicio', 'is_ativa')
    list_filter = ('tipo', 'paga_por', 'is_ativa')
    search_fields = ('contrato__id', 'descricao')

@admin.register(IndiceInflacao)
class IndiceInflacaoAdmin(admin.ModelAdmin):
    list_display = ('tipo', 'data_referencia', 'valor', 'acumulado_12_meses', 'fonte')
    list_filter = ('tipo',)
    search_fields = ('fonte',)

@admin.register(Repasse)
class RepasseAdmin(admin.ModelAdmin):
    list_display = ('proprietario', 'valor', 'valor_taxa_admin', 'status', 'data_prevista')
    list_filter = ('status', 'tipo', 'metodo_pagamento')
    search_fields = ('proprietario__nome', 'descricao')

@admin.register(PoliticaRepasseGlobal)
class PoliticaRepasseAdmin(admin.ModelAdmin):
    list_display = ('nome', 'periodicidade', 'dia_mes', 'dia_semana', 'ativa')
    list_filter = ('periodicidade', 'ativa')
    search_fields = ('nome',)

@admin.register(AgendamentoRepasse)
class AgendamentoRepasseAdmin(admin.ModelAdmin):
    list_display = ('proprietario', 'data_agendada', 'valor_previsto', 'status')
    list_filter = ('status',)
    search_fields = ('proprietario__nome',)

@admin.register(MovimentoConta)
class MovimentoContaAdmin(admin.ModelAdmin):
    list_display = ('proprietario', 'tipo', 'valor', 'data', 'descricao')
    list_filter = ('tipo',)
    search_fields = ('descricao', 'proprietario__nome')

@admin.register(SaldoProprietario)
class SaldoProprietarioAdmin(admin.ModelAdmin):
    list_display = ('proprietario', 'saldo_atual', 'ultima_atualizacao')

@admin.register(LembreteEnviado)
class LembreteEnviadoAdmin(admin.ModelAdmin):
    list_display = ('cobranca', 'tipo', 'dias_antes_vencimento', 'data_envio', 'status')
    list_filter = ('tipo', 'status')
    search_fields = ('cobranca__contrato__id', 'cobranca__inquilino__nome')



