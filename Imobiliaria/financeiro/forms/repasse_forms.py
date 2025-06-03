# financeiro/forms/repasse_forms.py
from django import forms
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import date, timedelta

from ..models.repasse import Repasse, PoliticaRepasse, AgendamentoRepasse


class RepasseForm(forms.ModelForm):
    class Meta:
        model = Repasse
        fields = [
            'proprietario', 'contrato', 'cobranca', 'valor', 'valor_desconto',
            'valor_taxa_admin', 'data_prevista', 'mes_referencia', 'ano_referencia',
            'tipo', 'metodo_pagamento', 'descricao', 'observacoes'
        ]
        widgets = {
            'proprietario': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500'
            }),
            'contrato': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500'
            }),
            'cobranca': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500'
            }),
            'valor': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500',
                'step': '0.01',
                'min': '0'
            }),
            'valor_desconto': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500',
                'step': '0.01',
                'min': '0'
            }),
            'valor_taxa_admin': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500',
                'step': '0.01',
                'min': '0'
            }),
            'data_prevista': forms.DateInput(attrs={
                'type': 'date',
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500'
            }),
            'mes_referencia': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500',
                'min': '1',
                'max': '12'
            }),
            'ano_referencia': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500',
                'min': '2020'
            }),
            'tipo': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500'
            }),
            'metodo_pagamento': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500'
            }),
            'descricao': forms.Textarea(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500',
                'rows': 3
            }),
            'observacoes': forms.Textarea(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500',
                'rows': 3
            }),
        }

    def clean_valor(self):
        valor = self.cleaned_data.get('valor')
        if valor and valor <= 0:
            raise ValidationError("O valor deve ser maior que zero.")
        return valor

    def clean_data_prevista(self):
        data_prevista = self.cleaned_data.get('data_prevista')
        if data_prevista and data_prevista < date.today() - timedelta(days=30):
            raise ValidationError("Data prevista não pode ser muito antiga.")
        return data_prevista

    def clean(self):
        cleaned_data = super().clean()
        valor = cleaned_data.get('valor', Decimal('0'))
        valor_desconto = cleaned_data.get('valor_desconto', Decimal('0'))
        valor_taxa_admin = cleaned_data.get('valor_taxa_admin', Decimal('0'))

        if valor_desconto + valor_taxa_admin >= valor:
            raise ValidationError("A soma dos descontos não pode ser maior ou igual ao valor total.")

        mes = cleaned_data.get('mes_referencia')
        ano = cleaned_data.get('ano_referencia')
        if mes and (mes < 1 or mes > 12):
            raise ValidationError("Mês de referência deve estar entre 1 e 12.")
        
        if ano and ano < 2020:
            raise ValidationError("Ano de referência deve ser válido.")

        return cleaned_data


class ProcessarRepasseForm(forms.Form):
    metodo_pagamento = forms.ChoiceField(
        choices=Repasse.METODO_PAGAMENTO_CHOICES,
        widget=forms.Select(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500'
        }),
        label='Método de Pagamento'
    )
    
    observacoes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500',
            'rows': 3,
            'placeholder': 'Observações sobre o processamento...'
        }),
        label='Observações'
    )
    
    comprovante = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'mt-1 block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100',
            'accept': '.pdf,.jpg,.jpeg,.png'
        }),
        label='Comprovante'
    )

    def clean_comprovante(self):
        comprovante = self.cleaned_data.get('comprovante')
        if comprovante:
            # Validar tamanho (5MB max)
            if comprovante.size > 5 * 1024 * 1024:
                raise ValidationError("Arquivo muito grande. Máximo 5MB.")
            
            # Validar tipo
            allowed_types = ['application/pdf', 'image/jpeg', 'image/png', 'image/jpg']
            if comprovante.content_type not in allowed_types:
                raise ValidationError("Tipo de arquivo não permitido. Use PDF, JPG ou PNG.")
        
        return comprovante


class PoliticaRepasseForm(forms.ModelForm):
    class Meta:
        model = PoliticaRepasse
        fields = [
            'nome', 'ativa', 'periodicidade', 'dia_mes', 'dia_semana',
            'dias_apos_recebimento', 'percentual_adiantamento', 'taxa_adiantamento',
            'valor_minimo_repasse'
        ]
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500',
                'placeholder': 'Ex: Repasse Mensal Padrão'
            }),
            'ativa': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded'
            }),
            'periodicidade': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500'
            }),
            'dia_mes': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500',
                'min': '1',
                'max': '31',
                'placeholder': 'Ex: 5 (dia 5 do mês)'
            }),
            'dia_semana': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500'
            }),
            'dias_apos_recebimento': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500',
                'min': '0',
                'max': '30'
            }),
            'percentual_adiantamento': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500',
                'step': '0.01',
                'min': '0',
                'max': '100'
            }),
            'taxa_adiantamento': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500',
                'step': '0.01',
                'min': '0'
            }),
            'valor_minimo_repasse': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500',
                'step': '0.01',
                'min': '0'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Mostrar campos condicionalmente via JavaScript
        self.fields['dia_mes'].required = False
        self.fields['dia_semana'].required = False

    def clean(self):
        cleaned_data = super().clean()
        periodicidade = cleaned_data.get('periodicidade')
        dia_mes = cleaned_data.get('dia_mes')
        dia_semana = cleaned_data.get('dia_semana')

        if periodicidade == 'mensal' and not dia_mes:
            raise ValidationError("Para periodicidade mensal, é necessário informar o dia do mês.")
        
        if periodicidade == 'semanal' and not dia_semana:
            raise ValidationError("Para periodicidade semanal, é necessário informar o dia da semana.")

        if dia_mes and (dia_mes < 1 or dia_mes > 31):
            raise ValidationError("Dia do mês deve estar entre 1 e 31.")

        percentual = cleaned_data.get('percentual_adiantamento', Decimal('0'))
        if percentual > 100:
            raise ValidationError("Percentual de adiantamento não pode ser maior que 100%.")

        return cleaned_data


class FiltroRepasseForm(forms.Form):
    status = forms.ChoiceField(
        choices=[('', 'Todos')] + Repasse.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
        })
    )
    
    proprietario = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm',
            'placeholder': 'Buscar proprietário...'
        })
    )
    
    mes_referencia = forms.ChoiceField(
        choices=[('', 'Todos')] + [(i, f'{i:02d}') for i in range(1, 13)],
        required=False,
        widget=forms.Select(attrs={
            'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
        })
    )
    
    ano_referencia = forms.ChoiceField(
        required=False,
        widget=forms.Select(attrs={
            'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
        })
    )
    
    data_inicio = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
        })
    )
    
    data_fim = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Gerar opções de ano dinamicamente
        current_year = date.today().year
        year_choices = [('', 'Todos')] + [(year, str(year)) for year in range(current_year - 2, current_year + 2)]
        self.fields['ano_referencia'].choices = year_choices


class AgendamentoRepasseForm(forms.ModelForm):
    class Meta:
        model = AgendamentoRepasse
        fields = [
            'proprietario', 'contrato', 'politica', 'data_agendada',
            'valor_previsto', 'mes_referencia', 'ano_referencia'
        ]
        widgets = {
            'proprietario': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500'
            }),
            'contrato': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500'
            }),
            'politica': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500'
            }),
            'data_agendada': forms.DateInput(attrs={
                'type': 'date',
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500'
            }),
            'valor_previsto': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500',
                'step': '0.01',
                'min': '0'
            }),
            'mes_referencia': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500',
                'min': '1',
                'max': '12'
            }),
            'ano_referencia': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500',
                'min': '2020'
            }),
        }

    def clean_data_agendada(self):
        data = self.cleaned_data.get('data_agendada')
        if data and data < date.today():
            raise ValidationError("Data agendada não pode ser no passado.")
        return data

    def clean_valor_previsto(self):
        valor = self.cleaned_data.get('valor_previsto')
        if valor and valor <= 0:
            raise ValidationError("Valor previsto deve ser maior que zero.")
        return valor