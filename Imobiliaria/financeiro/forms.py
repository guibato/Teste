# financeiro/forms.py
from django import forms
from django.core.exceptions import ValidationError
from datetime import date
from decimal import Decimal

from .models import (
    Cobranca, Despesa, IndiceInflacao, Repasse,
    PoliticaRepasse, AgendamentoRepasse,
    MovimentoConta, SaldoProprietario, LembreteEnviado
)


class CobrancaForm(forms.ModelForm):
    class Meta:
        model = Cobranca
        fields = [
            'contrato', 'inquilino', 'mes_referencia', 'ano_referencia',
            'descricao', 'valor_aluguel', 'data_vencimento',
            'status'
        ]
        widgets = {
            'data_vencimento': forms.SelectDateWidget(years=range(2020, 2031)),
        }

    def clean(self):
        cleaned_data = super().clean()
        mes = cleaned_data.get('mes_referencia')
        ano = cleaned_data.get('ano_referencia')
        contrato = cleaned_data.get('contrato')

        if mes and ano and contrato:
            existe = Cobranca.objects.filter(
                contrato=contrato,
                mes_referencia=mes,
                ano_referencia=ano
            ).exclude(pk=self.instance.pk).exists()
            if existe:
                raise ValidationError("Já existe uma cobrança para este contrato neste mês/ano.")

        return cleaned_data

    def clean_valor_aluguel(self):
        valor = self.cleaned_data.get('valor_aluguel')
        if valor is not None and valor < 0:
            raise ValidationError("O valor do aluguel não pode ser negativo.")
        return valor


class DespesaForm(forms.ModelForm):
    class Meta:
        model = Despesa
        fields = [
            'contrato', 'tipo', 'descricao', 'valor_total', 'paga_por',
            'numero_parcelas', 'periodicidade', 'data_inicio',
            'cobranca_referencia', 'percentual_repassado',
            'is_base_calculo_administracao', 'is_recorrente', 'is_ativa',
            'comprovante', 'observacoes'
        ]
        widgets = {
            'data_inicio': forms.SelectDateWidget(
                years=range(2020, 2031),
                empty_label=("Ano", "Mês", "Dia")
            ),
            'descricao': forms.TextInput(attrs={'class': 'form-input'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
        }


    def clean_valor_total(self):
        valor = self.cleaned_data.get('valor_total')
        if valor is not None and valor <= 0:
            raise ValidationError("O valor da despesa deve ser maior que zero.")
        return valor

    def clean_percentual_repassado(self):
        percentual = self.cleaned_data.get('percentual_repassado')
        if percentual < 0 or percentual > 100:
            raise ValidationError("O percentual deve estar entre 0% e 100%.")
        return percentual

    def clean(self):
        cleaned_data = super().clean()
        parcelas = cleaned_data.get('numero_parcelas')

        if parcelas is not None and parcelas <= 0:
            self.add_error('numero_parcelas', "O número de parcelas deve ser maior que zero.")
        
        return cleaned_data



class IndiceInflacaoForm(forms.ModelForm):
    class Meta:
        model = IndiceInflacao
        fields = ['tipo', 'valor', 'data_referencia', 'acumulado_12_meses', 'fonte']


class RepasseForm(forms.ModelForm):
    class Meta:
        model = Repasse
        fields = [
            'proprietario', 'contrato', 'cobranca',
            'valor', 'valor_desconto', 'valor_taxa_admin',
            'data_prevista', 'data_efetivacao',
            'mes_referencia', 'ano_referencia',
            'status', 'tipo', 'metodo_pagamento',
            'descricao', 'observacoes', 'comprovante'
        ]


class PoliticaRepasseForm(forms.ModelForm):
    class Meta:
        model = PoliticaRepasse
        fields = [
            'nome', 'ativa', 'periodicidade', 'dia_mes', 'dia_semana',
            'dias_apos_recebimento', 'percentual_adiantamento',
            'taxa_adiantamento', 'valor_minimo_repasse'
        ]


class AgendamentoRepasseForm(forms.ModelForm):
    class Meta:
        model = AgendamentoRepasse
        fields = [
            'proprietario', 'contrato', 'politica',
            'data_agendada', 'valor_previsto',
            'mes_referencia', 'ano_referencia',
            'status', 'detalhes_processamento'
        ]


class MovimentoContaForm(forms.ModelForm):
    class Meta:
        model = MovimentoConta
        fields = [
            'proprietario', 'contrato', 'tipo',
            'descricao', 'valor', 'data_referencia'
        ]


class SaldoProprietarioForm(forms.ModelForm):
    class Meta:
        model = SaldoProprietario
        fields = ['proprietario', 'saldo_atual']


class LembreteEnviadoForm(forms.ModelForm):
    class Meta:
        model = LembreteEnviado
        fields = [
            'cobranca', 'tipo', 'dias_antes_vencimento',
            'status', 'observacao'
        ]
