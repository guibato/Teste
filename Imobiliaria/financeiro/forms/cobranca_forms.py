# financeiro/forms/cobranca_forms.py
"""
Formulários para Cobranças
==========================
"""

from django import forms
from django.core.exceptions import ValidationError
from datetime import date, timedelta
from decimal import Decimal

from ..models import Cobranca


class CobrancaForm(forms.ModelForm):
    """
    Formulário para criação e edição de cobranças
    """
    
    # Campo adicional para incluir despesas automaticamente
    incluir_despesas = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'w-4 h-4 text-blue-600 bg-gray-700 border-gray-600 rounded focus:ring-blue-500 focus:ring-2'
        }),
        label='Incluir Despesas do Contrato',
        help_text='Incluir automaticamente as despesas ativas do contrato no valor total'
    )
    
    # Campo para escolher quais despesas incluir (será populado via JavaScript)
    despesas_selecionadas = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
        help_text='IDs das despesas selecionadas (separadas por vírgula)'
    )
    
    # Campo para gerar automaticamente a descrição
    gerar_descricao_automatica = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'w-4 h-4 text-blue-600 bg-gray-700 border-gray-600 rounded focus:ring-blue-500 focus:ring-2'
        }),
        label='Gerar Descrição Automática',
        help_text='Gerar automaticamente a descrição com detalhes do aluguel e despesas'
    )
    
    class Meta:
        model = Cobranca  
        fields = [
            'contrato', 'inquilino', 'mes_referencia', 'ano_referencia',
            'valor_aluguel', 'valor_total', 'data_vencimento',
            'descricao', 'observacoes'
        ]
        
        widgets = {
            'contrato': forms.Select(attrs={
                'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500',
                'required': True
            }),
            'inquilino': forms.Select(attrs={
                'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500',
                'required': True
            }),
            'mes_referencia': forms.Select(attrs={
                'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500'
            }),
            'ano_referencia': forms.NumberInput(attrs={
                'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500',
                'min': '2020',
                'max': '2030'
            }),
            'valor_aluguel': forms.NumberInput(attrs={
                'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg pl-12 pr-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500',
                'step': '0.01',
                'min': '0',
                'placeholder': '0,00'
            }),
            'valor_total': forms.NumberInput(attrs={
                'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg pl-12 pr-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500',
                'step': '0.01',
                'min': '0',
                'placeholder': '0,00',
                'readonly': True  # Será calculado automaticamente
            }),
            'data_vencimento': forms.DateInput(attrs={
                'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500',
                'type': 'date',
                'required': True
            }),
            'descricao': forms.Textarea(attrs={
                'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500',
                'rows': 4,
                'placeholder': 'Detalhamento da cobrança...'
            }),
            'observacoes': forms.Textarea(attrs={
                'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500',
                'rows': 3,
                'placeholder': 'Observações internas...'
            })
        }
        
        labels = {
            'contrato': 'Contrato',
            'inquilino': 'Inquilino',
            'mes_referencia': 'Mês de Referência',
            'ano_referencia': 'Ano de Referência', 
            'valor_aluguel': 'Valor do Aluguel (R$)',
            'valor_total': 'Valor Total (R$)',
            'data_vencimento': 'Data de Vencimento',
            'descricao': 'Descrição da Cobrança',
            'observacoes': 'Observações'
        }
        
        help_texts = {
            'contrato': 'Selecione o contrato para esta cobrança',
            'inquilino': 'Inquilino responsável pelo pagamento',
            'mes_referencia': 'Mês ao qual se refere esta cobrança',
            'ano_referencia': 'Ano de referência da cobrança',
            'valor_aluguel': 'Valor base do aluguel do contrato',
            'valor_total': 'Valor total incluindo aluguel e despesas (calculado automaticamente)',
            'data_vencimento': 'Data limite para pagamento',
            'descricao': 'Descrição detalhada que aparecerá na cobrança',
            'observacoes': 'Observações internas (não aparecem na cobrança)'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Configurar campo contrato
        try:
            from sisimob.models import Contrato
            # Apenas contratos ativos
            self.fields['contrato'].queryset = Contrato.objects.filter(
                ativo=True
            ).order_by('-data_inicio')
        except ImportError:
            pass
        
        # Configurar campo inquilino
        try:
            from sisimob.models import Cliente
            # Apenas clientes do tipo inquilino
            self.fields['inquilino'].queryset = Cliente.objects.filter(
                tipo='inquilino'
            ).order_by('nome')
        except ImportError:
            pass
        
        # Configurar opções de mês
        meses_choices = [
            (1, 'Janeiro'), (2, 'Fevereiro'), (3, 'Março'), (4, 'Abril'),
            (5, 'Maio'), (6, 'Junho'), (7, 'Julho'), (8, 'Agosto'),
            (9, 'Setembro'), (10, 'Outubro'), (11, 'Novembro'), (12, 'Dezembro')
        ]
        self.fields['mes_referencia'] = forms.ChoiceField(
            choices=meses_choices,
            widget=forms.Select(attrs=self.fields['mes_referencia'].widget.attrs)
        )
        
        # Valores padrão para nova cobrança
        if not self.instance.pk:
            hoje = date.today()
            self.fields['mes_referencia'].initial = hoje.month
            self.fields['ano_referencia'].initial = hoje.year
            # Data de vencimento padrão: dia 10 do próximo mês
            if hoje.month == 12:
                vencimento = date(hoje.year + 1, 1, 10)
            else:
                vencimento = date(hoje.year, hoje.month + 1, 10)
            self.fields['data_vencimento'].initial = vencimento
    
    def clean(self):
        """Validação geral do formulário"""
        cleaned_data = super().clean()
        
        contrato = cleaned_data.get('contrato')
        mes_referencia = cleaned_data.get('mes_referencia')
        ano_referencia = cleaned_data.get('ano_referencia')
        valor_aluguel = cleaned_data.get('valor_aluguel')
        data_vencimento = cleaned_data.get('data_vencimento')
        
        # Verificar duplicata de cobrança
        if contrato and mes_referencia and ano_referencia:
            queryset = Cobranca.objects.filter(
                contrato=contrato,
                mes_referencia=mes_referencia,
                ano_referencia=ano_referencia
            )
            
            if self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            
            if queryset.exists():
                raise ValidationError({
                    'mes_referencia': f'Já existe uma cobrança para {contrato} em {mes_referencia}/{ano_referencia}'
                })
        
        # Validar data de vencimento
        if data_vencimento:
            if data_vencimento < date.today():
                raise ValidationError({
                    'data_vencimento': 'Data de vencimento não pode ser anterior a hoje.'
                })
        
        # Validar valor do aluguel
        if valor_aluguel is not None and valor_aluguel <= 0:
            raise ValidationError({
                'valor_aluguel': 'Valor do aluguel deve ser maior que zero.'
            })
        
        # Se tem contrato, pré-carregar valor do aluguel se não foi informado
        if contrato and not valor_aluguel:
            if hasattr(contrato, 'valor_aluguel') and contrato.valor_aluguel:
                cleaned_data['valor_aluguel'] = contrato.valor_aluguel
        
        # Calcular valor total se incluir despesas
        incluir_despesas = cleaned_data.get('incluir_despesas', False)
        if incluir_despesas and contrato:
            valor_total = cleaned_data.get('valor_aluguel', Decimal('0.00'))
            
            # Buscar despesas ativas do contrato
            from ..models import Despesa
            from datetime import date
            
            data_referencia = date(ano_referencia or date.today().year, 
                                 mes_referencia or date.today().month, 1)
            
            despesas = Despesa.objects.filter(
                contrato=contrato,
                is_ativa=True,
                paga_por='inquilino'  # Apenas despesas pagas pelo inquilino
            )
            
            valor_despesas = Decimal('0.00')
            for despesa in despesas:
                if despesa.parcela_ativa_em_data(data_referencia):
                    valor_despesas += despesa.calcular_valor_parcela()
            
            valor_total += valor_despesas
            cleaned_data['valor_total'] = valor_total
        
        return cleaned_data
    
    def clean_mes_referencia(self):
        """Validar mês de referência"""
        mes = self.cleaned_data.get('mes_referencia')
        if mes and (mes < 1 or mes > 12):
            raise ValidationError('Mês deve estar entre 1 e 12.')
        return mes
    
    def clean_ano_referencia(self):
        """Validar ano de referência"""
        ano = self.cleaned_data.get('ano_referencia')
        if ano and (ano < 2020 or ano > 2030):
            raise ValidationError('Ano deve estar entre 2020 e 2030.')
        return ano


class CobrancaFiltroForm(forms.Form):
    """
    Formulário para filtros na listagem de cobranças
    """
    
    STATUS_CHOICES = [
        ('todos', 'Todos'),
        ('pendente', 'Pendentes'),
        ('paga', 'Pagas'),
        ('atrasada', 'Atrasadas'),
        ('cancelada', 'Canceladas'),
    ]
    
    MES_CHOICES = [('', 'Todos os meses')] + [
        (i, f'{i:02d}') for i in range(1, 13)
    ]
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        initial='pendente',
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500',
            'onchange': 'this.form.submit();'
        }),
        label='Status'
    )
    
    mes_referencia = forms.ChoiceField(
        choices=MES_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500',
            'onchange': 'this.form.submit();'
        }),
        label='Mês'
    )
    
    ano_referencia = forms.CharField(
        max_length=4,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500',
            'placeholder': 'Ano...',
            'min': '2020',
            'max': '2030'
        }),
        label='Ano'
    )
    
    contrato = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500',
            'placeholder': 'Buscar por contrato...'
        }),
        label='Contrato'
    )
    
    inquilino = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500',
            'placeholder': 'Buscar por inquilino...'
        }),
        label='Inquilino'
    )


class CobrancaIntegracaoAsaasForm(forms.Form):
    """
    Formulário para integração com Asaas
    """
    
    FORMAS_PAGAMENTO = [
        ('BOLETO', 'Boleto Bancário'),
        ('PIX', 'PIX'),
        ('CREDIT_CARD', 'Cartão de Crédito'),
        ('DEBIT_CARD', 'Cartão de Débito'),
    ]
    
    formas_pagamento = forms.MultipleChoiceField(
        choices=FORMAS_PAGAMENTO,
        initial=['BOLETO', 'PIX'],
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-checkbox text-blue-600 bg-gray-700 border-gray-600 rounded focus:ring-blue-500'
        }),
        label='Formas de Pagamento',
        help_text='Selecione as formas de pagamento disponíveis para esta cobrança'
    )
    
    enviar_por_email = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'w-4 h-4 text-blue-600 bg-gray-700 border-gray-600 rounded focus:ring-blue-500 focus:ring-2'
        }),
        label='Enviar por E-mail',
        help_text='Enviar cobrança automaticamente por e-mail'
    )
    
    enviar_por_whatsapp = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'w-4 h-4 text-blue-600 bg-gray-700 border-gray-600 rounded focus:ring-blue-500 focus:ring-2'
        }),
        label='Enviar por WhatsApp',
        help_text='Enviar cobrança automaticamente por WhatsApp'
    )
    
    observacoes_cobranca = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500',
            'rows': 3,
            'placeholder': 'Observações que aparecerão na cobrança...'
        }),
        label='Observações da Cobrança',
        help_text='Texto adicional que aparecerá na cobrança enviada ao cliente'
    )