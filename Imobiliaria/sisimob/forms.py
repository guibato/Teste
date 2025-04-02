from django import forms
from .models import Cliente, Imovel, Contrato, Cobranca, Despesa
from decimal import Decimal
from datetime import datetime

class ImovelForm(forms.ModelForm):
    class Meta:
        model = Imovel
        fields = '__all__'
        labels = {
            'cep': 'CEP',
            'endereco': 'Endereço',
            'numero': 'Número',
            'complemento': 'Complemento',
            'bairro': 'Bairro',
            'cidade': 'Cidade',
            'estado': 'Estado',
            'iptu': 'IPTU',
            'comgas': 'Comgás',
            'sabesp': 'Sabesp',
            'enel': 'Enel',
        }
        widgets = {
            'cep': forms.TextInput(attrs={'placeholder': 'Ex.: 00000-000', 'class': 'cep-mask'}),
            'endereco': forms.TextInput(attrs={'placeholder': 'Ex.: Rua das Flores'}),
            'numero': forms.TextInput(attrs={'placeholder': 'Ex.: 123'}),
            'complemento': forms.TextInput(attrs={'placeholder': 'Ex.: Apto 101'}),
            'bairro': forms.TextInput(attrs={'placeholder': 'Ex.: Centro'}),
            'cidade': forms.TextInput(attrs={'placeholder': 'Ex.: São Paulo'}),
            'estado': forms.TextInput(attrs={'placeholder': 'Ex.: SP'}),
            'iptu': forms.TextInput(attrs={'placeholder': 'Ex.: xxx.xxx.xxxx-x', 'class': 'iptu-mask'}),
            'comgas': forms.NumberInput(attrs={'placeholder': 'Ex.: 50.00', 'class': 'form-control'}),
            'sabesp': forms.NumberInput(attrs={'placeholder': 'Ex.: 30.00', 'class': 'form-control'}),
            'enel': forms.NumberInput(attrs={'placeholder': 'Ex.: 70.00', 'class': 'form-control'}),
        }

class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = '__all__'
        labels = {
            'tipo': 'Tipo',
            'nome': 'Nome',
            'nacionalidade': 'Nacionalidade',
            'profissao': 'Profissão',
            'estado_civil': 'Estado Civil',
            'regime_casamento': 'Regime de Casamento',
            'anuente': 'Anuente',
            'CPF': 'CPF',
            'rg_rne': 'RG/RNE',
            'telefone': 'Telefone',
            'codigo_internacional_celular': 'Código Internacional (Celular)',
            'celular': 'Celular',
            'email': 'E-mail',
            'pix_modalidade': 'Modalidade PIX',
            'chave_pix': 'Chave PIX',
            'banco': 'Banco',
            'agencia': 'Agência',
            'conta_corrente': 'Conta Corrente',
            'poupanca': 'Poupança',
            'cep': 'CEP',
            'endereco': 'Endereço',
            'numero': 'Número',
            'complemento': 'Complemento',
            'bairro': 'Bairro',
            'cidade': 'Cidade',
            'estado': 'Estado',
            'documento': 'Documento',
        }
        widgets = {
            'tipo': forms.Select(attrs={'onchange': 'toggleFields()', 'class': 'form-control'}),
            'anuente': forms.Select(attrs={'class': 'form-control'}),
            'estado_civil': forms.Select(attrs={'onchange': 'toggleRegimeCasamento()', 'class': 'form-control'}),
            'pix_modalidade': forms.Select(attrs={'class': 'form-control'}),
            'nacionalidade': forms.TextInput(attrs={'class': 'form-control'}),
            'profissao': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_rg_rne(self):
        rg_rne = self.cleaned_data.get('rg_rne')
        if rg_rne and Cliente.objects.filter(rg_rne=rg_rne).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Este RG/RNE já está cadastrado.')
        return rg_rne

class ContratoForm(forms.ModelForm):
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
            'valor_aluguel': 'Valor do Aluguel',
            'valor_pacote': 'Valor do Pacote',
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
            'valor_iptu': forms.NumberInput(attrs={'step': '0.01', 'class': 'form-control'}),
            'tipo_pagamento': forms.Select(attrs={'onchange': 'toggleAluguelFields()', 'class': 'form-control'}),
            'documentos': forms.ClearableFileInput(attrs={'class': 'form-control-file'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['valor_aluguel'].widget.attrs['class'] = 'despesas-field form-control'
        self.fields['valor_pacote'].widget.attrs['class'] = 'pacote-field form-control'
        
        self.fields['proprietario'].queryset = Cliente.objects.filter(tipo='Proprietario')
        self.fields['inquilino'].queryset = Cliente.objects.filter(tipo='Inquilino')
        self.fields['fiador'].queryset = Cliente.objects.filter(tipo='Fiador')
        self.fields['historico_aluguel'].required = False
        self.initial['historico_aluguel'] = {}

    def clean(self):
        cleaned_data = super().clean()
        tipo_pagamento = cleaned_data.get('tipo_pagamento')
        
        if tipo_pagamento == 'pacote':
            valor_pacote = cleaned_data.get('valor_pacote')
            if valor_pacote is None or valor_pacote <= 0:
                self.add_error('valor_pacote', 'Este campo é obrigatório.')
            cleaned_data['valor_aluguel'] = 0.00
        elif tipo_pagamento == 'despesas_separadas':
            valor_aluguel = cleaned_data.get('valor_aluguel')
            if valor_aluguel is None or valor_aluguel <= 0:
                self.add_error('valor_aluguel', 'Este campo é obrigatório.')
            cleaned_data['valor_pacote'] = 0.00
        
        return cleaned_data

    def clean_carencia_dias(self):
        carencia = self.cleaned_data.get('carencia_dias')
        if carencia is None:
            return 0
        return carencia
    
    def clean_valor(self, field_name):
        valor = self.cleaned_data.get(field_name)
        if valor is None:
            return Decimal('0.00')
        return valor

    def clean_carencia_dias(self):
        carencia = self.cleaned_data.get('carencia_dias')
        if carencia is None:
            return 0
        return carencia
    
    def clean_valor(self, field_name):
        valor = self.cleaned_data.get(field_name)
        if valor is None:
            return Decimal('0.00')
        return valor
    
    def clean(self):
        cleaned_data = super().clean()
        tipo_taxa = cleaned_data.get('tipo_taxa')
        
        if tipo_taxa == Contrato.valor_taxa_administracao_percentual:
            if not cleaned_data.get('valor_taxa_administracao_percentual'):
                self.add_error('valor_taxa_administracao_percentual', 'Informe o percentual')
            cleaned_data['valor_taxa_administracao_fixo'] = None
        elif tipo_taxa == Contrato.valor_taxa_administracao_fixo:
            if not cleaned_data.get('valor_taxa_administracao_fixo'):
                self.add_error('valor_taxa_administracao_fixo', 'Informe o valor fixo')
            cleaned_data['valor_taxa_administracao_percentual'] = None
        
        return cleaned_data

class GerarCobrancasForm(forms.Form):
    mes = forms.ChoiceField(
        choices=[(i, datetime(2023, i, 1).strftime('%B')) for i in range(1, 13)],
        label="Mês de Referência"
    )
    ano = forms.IntegerField(
        label="Ano de Referência",
        initial=datetime.now().year,
        min_value=2000,
        max_value=2100
    )

class BaseAutocompleteForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        autocomplete_fields = {
            'Cliente': ['nacionalidade', 'profissao', 'fiador'],
            'Imovel': ['endereco', 'bairro', 'cidade'],
            'Contrato': ['tipo', 'garantia', 'seguradora'],
        }
        
        model_name = self._meta.model.__name__
        if model_name in autocomplete_fields:
            for field_name in autocomplete_fields[model_name]:
                if field_name in self.fields:
                    self.fields[field_name].widget.attrs.update({
                        'class': 'autocomplete',
                        'data-model': model_name.lower(),
                        'data-field': field_name,
                    })

class CobrancaForm(forms.ModelForm):
    class Meta:
        model = Despesa
        fields = '__all__'
        labels = {
            'tipo': 'Tipo de Despesa',
            'descricao': 'Descrição',
            'valor_total': 'Valor Total',
            'numero_parcelas': 'Número de Parcelas',
            'data_inicio': 'Data de Início',
            'data_fim': 'Data de Término',
        }
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'valor_total': forms.NumberInput(attrs={'step': '0.01', 'class': 'form-control'}),
            'numero_parcelas': forms.NumberInput(attrs={'class': 'form-control'}),
            'data_inicio': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'data_fim': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }

from django.core.exceptions import ValidationError

from django import forms
from decimal import Decimal, ROUND_HALF_UP
from .models import Despesa, Contrato

class DespesaForm(forms.ModelForm):
    valor_total = forms.CharField(
        label='Valor Total',
        widget=forms.TextInput(attrs={'placeholder': 'R$ 0,00'})
    )

    class Meta:
        model = Despesa
        exclude = ['contrato']  # Excluir o campo contrato do formulário

    def __init__(self, *args, **kwargs):
        contrato = kwargs.pop('contrato', None)  # Obtém o contrato dos kwargs
        super().__init__(*args, **kwargs)
        if contrato:
            self.instance.contrato = contrato  # Associa o contrato à instância

    def clean_valor_total(self):
        valor_total = self.cleaned_data.get('valor_total')
        try:
            # Remove formatação e converte para decimal
            valor_limpo = valor_total.replace('R$', '').replace(' ', '').strip()
            # Substitui ponto por vazio (para milhares) e vírgula por ponto (para decimais)
            valor_limpo = valor_limpo.replace('.', '').replace(',', '.')
            valor_decimal = Decimal(valor_limpo)
            return valor_decimal.quantize(Decimal('0.00'))
        except Exception as e:
            raise forms.ValidationError(f"Valor inválido: {str(e)}")