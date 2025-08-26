# financeiro/forms/movimento_forms.py
from django import forms
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import date
from financeiro.models.movimento import MovimentoConta
from core.models import Contrato


class MovimentoManualForm(forms.Form):
    """Formulário para lançamento manual de movimentos"""
    
    TIPO_CHOICES = [
        ('credito', 'Crédito'),
        ('debito', 'Débito'),
        ('repasse', 'Repasse'),
    ]
    
    tipo = forms.ChoiceField(
        choices=TIPO_CHOICES,
        widget=forms.RadioSelect(attrs={
            'class': 'space-y-2'
        }),
        label='Tipo de Movimento'
    )
    
    valor = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal('0.01'),
        widget=forms.NumberInput(attrs={
            'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500',
            'placeholder': '0,00',
            'step': '0.01'
        }),
        label='Valor'
    )
    
    descricao = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500',
            'placeholder': 'Descrição do movimento...'
        }),
        label='Descrição'
    )
    
    contrato = forms.ModelChoiceField(
        queryset=Contrato.objects.none(),  # Será definido no __init__
        required=False,
        empty_label="Selecione um contrato (opcional)",
        widget=forms.Select(attrs={
            'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500'
        }),
        label='Contrato Relacionado'
    )
    
    data_referencia = forms.DateField(
        required=False,
        initial=date.today,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500'
        }),
        label='Data de Referência',
        help_text='Data que o movimento se refere (opcional)'
    )
    
    permitir_negativo = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500'
        }),
        label='Permitir saldo negativo',
        help_text='Marque apenas se necessário para débitos que deixem o saldo negativo'
    )
    
    def __init__(self, *args, **kwargs):
        self.proprietario = kwargs.pop('proprietario', None)
        super().__init__(*args, **kwargs)
        
        if self.proprietario:
            # Carregar apenas contratos ativos do proprietário
            self.fields['contrato'].queryset = Contrato.objects.filter(
                proprietario=self.proprietario,
                status='ativo'
            ).select_related('imovel', 'inquilino')
    
    def clean_valor(self):
        valor = self.cleaned_data.get('valor')
        if valor and valor <= 0:
            raise ValidationError('O valor deve ser maior que zero.')
        return valor
    
    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get('tipo')
        valor = cleaned_data.get('valor')
        permitir_negativo = cleaned_data.get('permitir_negativo')
        
        # Validar se débito sem permitir negativo não vai deixar saldo negativo
        if tipo == 'debito' and not permitir_negativo and self.proprietario:
            from financeiro.models.movimento import SaldoProprietario
            try:
                saldo_obj = SaldoProprietario.objects.get(proprietario=self.proprietario)
                if saldo_obj.saldo_atual < valor:
                    raise ValidationError(
                        'Saldo insuficiente para este débito. '
                        'Marque "Permitir saldo negativo" se necessário.'
                    )
            except SaldoProprietario.DoesNotExist:
                if valor > 0:
                    raise ValidationError(
                        'Não há saldo disponível. '
                        'Marque "Permitir saldo negativo" se necessário.'
                    )
        
        return cleaned_data


class AjusteSaldoForm(forms.Form):
    """Formulário para ajuste de saldo"""
    
    novo_saldo = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500',
            'placeholder': '0,00',
            'step': '0.01'
        }),
        label='Novo Saldo'
    )
    
    motivo = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500',
            'placeholder': 'Motivo do ajuste...'
        }),
        label='Motivo do Ajuste',
        help_text='Descreva o motivo do ajuste de saldo'
    )


class FiltroMovimentoForm(forms.Form):
    """Formulário para filtros do extrato"""
    
    data_inicio = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500'
        }),
        label='Data Início'
    )
    
    data_fim = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500'
        }),
        label='Data Fim'
    )
    
    tipo = forms.ChoiceField(
        choices=[('', 'Todos os tipos')] + MovimentoConta.TIPO_MOVIMENTO,
        required=False,
        widget=forms.Select(attrs={
            'class': 'block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500'
        }),
        label='Tipo'
    )
    
    contrato = forms.ModelChoiceField(
        queryset=Contrato.objects.none(),  # Será definido no __init__ se necessário
        required=False,
        empty_label="Todos os contratos",
        widget=forms.Select(attrs={
            'class': 'block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500'
        }),
        label='Contrato'
    )
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500',
            'placeholder': 'Buscar por descrição ou endereço...'
        }),
        label='Buscar'
    )
    
    def __init__(self, *args, **kwargs):
        self.proprietario = kwargs.pop('proprietario', None)
        super().__init__(*args, **kwargs)
        
        if self.proprietario:
            self.fields['contrato'].queryset = Contrato.objects.filter(
                proprietario=self.proprietario
            ).select_related('imovel', 'inquilino')


class ImportacaoExtratoForm(forms.Form):
    """Formulário para importação de extrato bancário"""
    
    arquivo = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100',
            'accept': '.csv,.txt,.xlsx'
        }),
        label='Arquivo do Extrato',
        help_text='Formatos aceitos: CSV, TXT, XLSX'
    )
    
    formato = forms.ChoiceField(
        choices=[
            ('csv', 'CSV'),
            ('txt', 'TXT'),
            ('xlsx', 'Excel'),
            ('ofx', 'OFX'),
        ],
        widget=forms.Select(attrs={
            'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500'
        }),
        label='Formato do Arquivo'
    )
    
    banco = forms.ChoiceField(
        choices=[
            ('bradesco', 'Bradesco'),
            ('itau', 'Itaú'),
            ('santander', 'Santander'),
            ('bb', 'Banco do Brasil'),
            ('caixa', 'Caixa Econômica'),
            ('nubank', 'Nubank'),
            ('inter', 'Banco Inter'),
            ('generico', 'Formato Genérico'),
        ],
        widget=forms.Select(attrs={
            'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500'
        }),
        label='Banco'
    )
    
    periodo_inicio = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500'
        }),
        label='Período Início',
        help_text='Período que o extrato compreende'
    )
    
    periodo_fim = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500'
        }),
        label='Período Fim'
    )
    
    def clean(self):
        cleaned_data = super().clean()
        periodo_inicio = cleaned_data.get('periodo_inicio')
        periodo_fim = cleaned_data.get('periodo_fim')
        
        if periodo_inicio and periodo_fim and periodo_inicio > periodo_fim:
            raise ValidationError('A data de início deve ser anterior à data de fim.')
        
        return cleaned_data


class ConciliacaoForm(forms.Form):
    """Formulário para conciliação bancária"""
    
    saldo_banco = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500',
            'placeholder': '0,00',
            'step': '0.01'
        }),
        label='Saldo no Banco',
        help_text='Saldo atual conforme extrato bancário'
    )
    
    data_conciliacao = forms.DateField(
        initial=date.today,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500'
        }),
        label='Data da Conciliação'
    )
    
    observacoes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500',
            'rows': 4,
            'placeholder': 'Observações sobre a conciliação...'
        }),
        label='Observações'
    )
    
    criar_ajuste_automatico = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500'
        }),
        label='Criar ajuste automático se necessário',
        help_text='Se marcado, criará um movimento de ajuste caso haja diferença'
    )