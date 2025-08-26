from django import forms
from django_select2.forms import Select2MultipleWidget
from decimal import Decimal
from core.models import Contrato, Cliente


class ContratoForm(forms.ModelForm):
    """
    Formulário para cadastro e edição de contratos
    """
    
    class Meta:
        model = Contrato
        fields = '__all__'
        labels = {
            'tipo': 'Tipo',
            'ativo': 'Ativo',
            'tipo_contrato': 'Tipo de Contrato',
            'proprietario': 'Proprietário',
            'inquilino': 'Inquilino',
            'imovel': 'Imóvel',
            'data_inicio': 'Data de Início',
            'data_fim': 'Data de Fim',
            'carencia_dias': 'Carência (dias)',
            'fator_reajuste': 'Fator de Reajuste',
            'multa_contratual': 'Multa Contratual',
            'tipo_pagamento': 'Tipo de Aluguel',
            'valor_base': 'Valor Base',
            'tipo_taxa': 'Tipo de Taxa',
            'valor_taxa_administracao_percentual': 'Adm - %',
            'valor_taxa_administracao_fixo': 'Adm - R$',
            'dia_pagamento': 'Dia de Pagamento',
            'garantia': 'Garantia',
            'fiador': 'Fiador',
            'valor_caucao': 'Valor Caução',
            'seguradora': 'Seguradora',
            'apolice': 'Apólice',
            'valor_seguro_incendio': 'Valor do Seguro',
            'vencimento_seguro_incendio': 'Vencimento do Seguro',
            'documentos': 'Documentos',
        }
        widgets = {
            'data_inicio': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'data_fim': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'fator_reajuste': forms.Select(attrs={'class': 'form-control'}),
            'multa_contratual': forms.Select(attrs={'class': 'form-control'}),
            'carencia_dias': forms.NumberInput(attrs={'class': 'form-control'}),
            'valor_base': forms.NumberInput(attrs={'step': '0.01', 'class': 'form-control'}),
            'tipo_pagamento': forms.Select(attrs={
                'onchange': 'toggleAluguelFields()', 
                'class': 'form-control'
            }),
            'tipo_taxa': forms.Select(attrs={'class': 'form-control'}),
            'valor_taxa_administracao_percentual': forms.NumberInput(attrs={
                'step': '0.01', 
                'class': 'form-control'
            }),
            'valor_taxa_administracao_fixo': forms.NumberInput(attrs={
                'step': '0.01', 
                'class': 'form-control'
            }),
            'dia_pagamento': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '31'
            }),
            'garantia': forms.Select(attrs={'class': 'form-control'}),
            'valor_caucao': forms.NumberInput(attrs={'step': '0.01', 'class': 'form-control'}),
            'valor_seguro_incendio': forms.NumberInput(attrs={'step': '0.01', 'class': 'form-control'}),
            'vencimento_seguro_incendio': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'documentos': forms.ClearableFileInput(attrs={'class': 'form-control-file'}),
            'proprietario': Select2MultipleWidget,
            'inquilino': Select2MultipleWidget,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Configura campos específicos
        self.fields['valor_base'].widget.attrs['class'] = 'despesas-field form-control'
        
        # Filtra queryset por tipo de cliente
        self.fields['proprietario'].queryset = Cliente.objects.filter(tipo='Proprietario')
        self.fields['inquilino'].queryset = Cliente.objects.filter(tipo='Inquilino')
        self.fields['fiador'].queryset = Cliente.objects.filter(tipo='Fiador')
        
        # Inicializa histórico se não existir
        self.fields['historico_aluguel'].required = False
        self.initial['historico_aluguel'] = {}

    def clean(self):
        """Validações customizadas do formulário"""
        cleaned_data = super().clean()
        tipo_pagamento = cleaned_data.get('tipo_pagamento')
        
        # Validação baseada no tipo de pagamento
        if tipo_pagamento == 'pacote':
            valor_base = cleaned_data.get('valor_base')
            if valor_base is None or valor_base <= 0:
                self.add_error('valor_base', 'Este campo é obrigatório para tipo pacote.')
        elif tipo_pagamento == 'despesas_separadas':
            valor_base = cleaned_data.get('valor_base')
            if valor_base is None or valor_base <= 0:
                self.add_error('valor_base', 'Este campo é obrigatório.')
        
        # Validação de taxa de administração
        tipo_taxa = cleaned_data.get('tipo_taxa')
        if tipo_taxa == 'percentual':
            if not cleaned_data.get('valor_taxa_administracao_percentual'):
                self.add_error('valor_taxa_administracao_percentual', 'Informe o percentual')
            cleaned_data['valor_taxa_administracao_fixo'] = None
        elif tipo_taxa == 'fixo':
            if not cleaned_data.get('valor_taxa_administracao_fixo'):
                self.add_error('valor_taxa_administracao_fixo', 'Informe o valor fixo')
            cleaned_data['valor_taxa_administracao_percentual'] = None
        
        return cleaned_data

    def clean_carencia_dias(self):
        """Validação da carência"""
        carencia = self.cleaned_data.get('carencia_dias')
        if carencia is None:
            return 0
        return carencia
    
    def clean_valor_base(self):
        """Validação do valor base"""
        valor = self.cleaned_data.get('valor_base')
        if valor is None:
            return Decimal('0.00')
        return valor

    def clean_dia_pagamento(self):
        """Validação do dia de pagamento"""
        dia = self.cleaned_data.get('dia_pagamento')
        if dia and (dia < 1 or dia > 31):
            raise forms.ValidationError("Dia deve estar entre 1 e 31.")
        return dia


class ContratoFiltroForm(forms.Form):
    """
    Formulário para filtrar contratos na listagem
    """
    STATUS_CHOICES = [
        ('', '-- Todos --'),
        ('ativo', 'Ativos'),
        ('inativo', 'Inativos'),
    ]
    
    buscar = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Buscar por proprietário, inquilino ou endereço...'
        })
    )
    
    filtro_tipo = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )


class ReajusteContratosForm(forms.Form):
    """
    Formulário para reajuste de contratos
    """
    data_inicio = forms.DateField(
        label="Data de Início do Reajuste", 
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    valor_manual = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        label="Valor Manual de Reajuste (%)",
        required=False,
        widget=forms.NumberInput(attrs={'step': '0.01', 'class': 'form-control'})
    )

    def clean(self):
        """Validações do formulário de reajuste"""
        cleaned_data = super().clean()
        data_inicio = cleaned_data.get('data_inicio')
        valor_manual = cleaned_data.get('valor_manual')

        if not data_inicio:
            self.add_error('data_inicio', "Informe a data de início do reajuste.")

        if valor_manual is not None and valor_manual < 0:
            self.add_error('valor_manual', "O valor manual de reajuste não pode ser negativo.")

        return cleaned_data