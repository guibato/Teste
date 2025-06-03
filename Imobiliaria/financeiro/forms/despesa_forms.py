# financeiro/forms/despesa_forms.py - VERSÃO MELHORADA
"""
Formulários para Despesas - Versão com Recorrentes e Valor por Parcela
=====================================================================
"""

from django import forms
from django.core.exceptions import ValidationError
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

from ..models import Despesa, TipoDespesa


class DespesaForm(forms.ModelForm):
    """
    Formulário para criação e edição de despesas
    Com suporte a despesas recorrentes e valor por parcela
    """
    
    # Campos adicionais não salvos no modelo
    tipo_valor = forms.ChoiceField(
        choices=[
            ('total', 'Valor Total'),
            ('parcela', 'Valor por Parcela')
        ],
        initial='total',
        widget=forms.RadioSelect(attrs={
            'class': 'form-radio text-blue-600 bg-gray-700 border-gray-600 focus:ring-blue-500'
        }),
        label='Tipo de Valor',
        help_text='Escolha se está informando o valor total ou o valor de cada parcela'
    )
    
    valor_parcela = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg pl-12 pr-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500',
            'step': '0.01',
            'min': '0',
            'placeholder': '0,00'
        }),
        label='Valor por Parcela (R$)',
        help_text='Valor de cada parcela individual'
    )
    
    gerar_recorrentes = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'w-4 h-4 text-blue-600 bg-gray-700 border-gray-600 rounded focus:ring-blue-500 focus:ring-2'
        }),
        label='Gerar Despesas Recorrentes',
        help_text='Marca para criar automaticamente despesas futuras (ex: Condomínio todo mês)'
    )
    
    quantidade_recorrentes = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=60,
        initial=12,
        widget=forms.NumberInput(attrs={
            'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500',
            'min': '1',
            'max': '60'
        }),
        label='Quantidade de Recorrências',
        help_text='Quantas despesas recorrentes criar (máximo 60)'
    )
    
    class Meta:
        model = Despesa
        fields = [
            'contrato', 'tipo', 'descricao', 'valor_total', 
            'paga_por', 'numero_parcelas', 'periodicidade', 
            'data_inicio', 'is_ativa', 'observacoes'
        ]
        
        widgets = {
            'contrato': forms.Select(attrs={
                'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500',
                'required': True
            }),
            'tipo': forms.Select(attrs={
                'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500',
                'required': True
            }),
            'descricao': forms.TextInput(attrs={
                'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Descrição da despesa (opcional)...'
            }),
            'valor_total': forms.NumberInput(attrs={
                'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg pl-12 pr-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500',
                'step': '0.01',
                'min': '0',
                'placeholder': '0,00',
                'required': True
            }),
            'paga_por': forms.Select(attrs={
                'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500'
            }),
            'numero_parcelas': forms.NumberInput(attrs={
                'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500',
                'min': '1',
                'value': '1'
            }),
            'periodicidade': forms.Select(attrs={
                'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500'
            }),
            'data_inicio': forms.DateInput(attrs={
                'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500',
                'type': 'date',
                'required': True
            }),
            'is_ativa': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-blue-600 bg-gray-700 border-gray-600 rounded focus:ring-blue-500 focus:ring-2'
            }),
            'observacoes': forms.Textarea(attrs={
                'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500',
                'rows': 3,
                'placeholder': 'Observações adicionais...'
            })
        }
        
        labels = {
            'contrato': 'Contrato',
            'tipo': 'Tipo de Despesa',
            'descricao': 'Descrição',
            'valor_total': 'Valor Total (R$)',
            'paga_por': 'Paga Por',
            'numero_parcelas': 'Número de Parcelas',
            'periodicidade': 'Periodicidade',
            'data_inicio': 'Data de Início',
            'is_ativa': 'Ativa',
            'observacoes': 'Observações'
        }
        
        help_texts = {
            'contrato': 'Selecione o contrato ao qual esta despesa se refere',
            'tipo': 'Selecione o tipo de despesa',
            'valor_total': 'Valor total da despesa (será dividido pelas parcelas)',
            'paga_por': 'Quem será responsável pelo pagamento',
            'numero_parcelas': 'Em quantas parcelas será dividida',
            'periodicidade': 'Frequência das parcelas',
            'data_inicio': 'Data de início da primeira parcela',
            'is_ativa': 'Desmarque para inativar a despesa',
            'observacoes': 'Informações adicionais sobre a despesa'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filtrar apenas tipos ativos
        self.fields['tipo'].queryset = TipoDespesa.objects.filter(ativo=True).order_by('nome')
        
        # Configurar campo contrato
        try:
            from sisimob.models import Contrato
            self.fields['contrato'].queryset = Contrato.objects.filter(
                ativo=True
            ).order_by('-data_inicio')
        except ImportError:
            pass
        
        # Campo is_ativa marcado por padrão para novos registros
        if not self.instance.pk:
            self.fields['is_ativa'].initial = True
        
        # Se está editando, desabilitar campos de recorrência
        if self.instance.pk:
            self.fields['gerar_recorrentes'].widget.attrs['disabled'] = True
            self.fields['quantidade_recorrentes'].widget.attrs['disabled'] = True
            self.fields['gerar_recorrentes'].help_text = 'Recorrência só pode ser configurada na criação'
    
    def clean(self):
        """Validação geral do formulário"""
        cleaned_data = super().clean()
        
        tipo_valor = cleaned_data.get('tipo_valor')
        valor_total = cleaned_data.get('valor_total')
        valor_parcela = cleaned_data.get('valor_parcela')
        numero_parcelas = cleaned_data.get('numero_parcelas', 1)
        gerar_recorrentes = cleaned_data.get('gerar_recorrentes')
        quantidade_recorrentes = cleaned_data.get('quantidade_recorrentes')
        
        # Validar campos de valor
        if tipo_valor == 'parcela':
            if not valor_parcela or valor_parcela <= 0:
                raise ValidationError({
                    'valor_parcela': 'Valor por parcela é obrigatório quando selecionado.'
                })
            # Calcular valor total baseado na parcela
            cleaned_data['valor_total'] = valor_parcela * numero_parcelas
        else:
            if not valor_total or valor_total <= 0:
                raise ValidationError({
                    'valor_total': 'Valor total é obrigatório quando selecionado.'
                })
        
        # Validar recorrência
        if gerar_recorrentes:
            if not quantidade_recorrentes or quantidade_recorrentes < 1:
                cleaned_data['quantidade_recorrentes'] = 12  # Padrão
            
            # Verificar se o tipo de despesa é adequado para recorrência
            tipo_despesa = cleaned_data.get('tipo')
            if tipo_despesa:
                tipos_recorrentes = ['condomínio', 'condominio', 'iptu', 'água', 'agua', 'luz', 'energia']
                if not any(palavra in tipo_despesa.nome.lower() for palavra in tipos_recorrentes):
                    # Avisar mas não bloquear
                    pass
        
        # Validar data de início
        data_inicio = cleaned_data.get('data_inicio')
        if data_inicio:
            data_limite = date.today() - timedelta(days=365*2)  # 2 anos atrás
            if data_inicio < data_limite:
                raise ValidationError({
                    'data_inicio': 'Data de início não pode ser anterior a 2 anos.'
                })
        
        return cleaned_data
    
    def clean_valor_total(self):
        """Valida o valor total"""
        valor = self.cleaned_data.get('valor_total')
        tipo_valor = self.data.get('tipo_valor', 'total')
        
        # Se está usando valor por parcela, não validar aqui
        if tipo_valor == 'parcela':
            return valor
        
        if valor is None or valor <= 0:
            raise ValidationError('O valor deve ser maior que zero.')
        
        return valor
    
    def clean_valor_parcela(self):
        """Valida o valor por parcela"""
        valor_parcela = self.cleaned_data.get('valor_parcela')
        tipo_valor = self.data.get('tipo_valor', 'total')
        
        if tipo_valor == 'parcela':
            if valor_parcela is None or valor_parcela <= 0:
                raise ValidationError('O valor por parcela deve ser maior que zero.')
        
        return valor_parcela
    
    def clean_numero_parcelas(self):
        """Valida número de parcelas"""
        parcelas = self.cleaned_data.get('numero_parcelas')
        
        if parcelas is None or parcelas < 1:
            raise ValidationError('Número de parcelas deve ser maior que zero.')
        
        if parcelas > 360:  # Máximo 30 anos
            raise ValidationError('Número de parcelas não pode ser maior que 360.')
        
        return parcelas