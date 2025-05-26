# financeiro/forms.py
from django import forms
from django.core.exceptions import ValidationError
from datetime import date
from decimal import Decimal
from .models.despesa import TipoDespesa

from .models import (
    Cobranca, Despesa, IndiceInflacao, Repasse,
    PoliticaRepasse, AgendamentoRepasse,
    MovimentoConta, SaldoProprietario, LembreteEnviado, TipoDespesa, ReajusteAluguel
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
            'data_inicio': forms.DateInput(attrs={'type': 'date'}),
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

class TipoDespesaForm(forms.ModelForm):
    class Meta:
        model = TipoDespesa
        fields = [
            'nome', 'descricao', 'ativo'
        ]
        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 1}),
            
        }

class ReajusteAluguelForm(forms.ModelForm):
    class Meta:
        model = ReajusteAluguel
        fields = [
            'data_reajuste', 'fator_aplicado', 'indice_utilizado', 'observacao'
        ]

    def __init__(self, *args, contrato=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.contrato = contrato

        if contrato:
            ultimo_reajuste = contrato.reajustes.order_by('-data_reajuste').first()
            valor_anterior = ultimo_reajuste.valor_reajustado if ultimo_reajuste else contrato.valor_base
            self.initial['valor_anterior'] = valor_anterior

            # Sugestão automática (exemplo com 6%)
            sugestao = valor_anterior * Decimal('1.06')
            self.initial['fator_aplicado'] = Decimal('6.00')
            self.initial['valor_reajustado'] = sugestao.quantize(Decimal('0.01'))

    valor_anterior = forms.DecimalField(label="Valor Anterior", disabled=True)
    valor_reajustado = forms.DecimalField(label="Novo Valor Reajustado")

    def clean_valor_reajustado(self):
        valor = self.cleaned_data['valor_reajustado']
        if valor <= 0:
            raise forms.ValidationError("O valor reajustado deve ser maior que zero.")
        return valor

    def save(self, commit=True):
        reajuste = super().save(commit=False)
        reajuste.contrato = self.contrato
        reajuste.valor_anterior = self.initial.get('valor_anterior')
        if commit:
            reajuste.save()
        return reajuste

class ReajusteAluguelForm(forms.ModelForm):
    class Meta:
        model = ReajusteAluguel
        fields = ['valor_anterior', 'valor_reajustado', 'fator_aplicado', 'indice_utilizado', 'data_reajuste', 'observacao']
        widgets = {
            'data_reajuste': forms.DateInput(attrs={'type': 'date'}),
            'observacao': forms.Textarea(attrs={'rows': 3}),
        }