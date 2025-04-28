from django import forms
from .models import Cliente, Imovel, Contrato, Cobranca, Despesa
from decimal import Decimal
from datetime import datetime
from djmoney.forms.fields import MoneyField
from djmoney.forms.widgets import MoneyWidget
from djmoney.money import Money

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
        exclude = ['asaas_id']
        
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
            'tipo_pessoa': forms.Select(attrs={'onchange': 'togglePessoaFields()', 'class': 'form-control'}),
        }

    def clean_rg_rne(self):
        rg_rne = self.cleaned_data.get('rg_rne')
        if rg_rne and Cliente.objects.filter(rg_rne=rg_rne).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Este RG/RNE já está cadastrado.')
        return rg_rne

class ContratoForm(forms.ModelForm):
    valor_aluguel = MoneyField(label='Valor do Aluguel', required=False)
    valor_pacote = MoneyField(label='Valor do Pacote', required=False)
    valor_taxa_administracao_fixo = MoneyField(label='Adm - R$', required=False)
    valor_caucao = MoneyField(label='Valor Caução', required=False)
    valor_segfi = MoneyField(label='Valor Seguro Fiança', required=False)
    valor_cap = MoneyField(label='Valor Capitalização', required=False)

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
            'valor_segfi': 'Valor Seguro Fiança',
            'valor_caucao': 'Valor Caução',
            'seguradora': 'Seguradora',
            'apolice': 'Apólice',
            'valor_seguro_incendio': 'Valor do Seguro',
            'vencimento_seguro_incendio': 'Vencimento do Seguro',
            'documentos': 'Documentos',
        }
        widgets = {
            'data_inicio': forms.DateInput(attrs={'type': 'date', 'class': 'input input-bordered'}),
            'data_fim': forms.DateInput(attrs={'type': 'date', 'class': 'input input-bordered'}),
            'tipo': forms.Select(attrs={'class': 'select select-bordered'}),
            'fator_reajuste': forms.Select(attrs={'class': 'select select-bordered'}),
            'multa_contratual': forms.Select(attrs={'class': 'select select-bordered'}),
            'carencia_dias': forms.NumberInput(attrs={'class': 'input input-bordered'}),
            'tipo_pagamento': forms.Select(attrs={
                'onchange': 'toggleAluguelFields()',
                'class': 'select select-bordered'
            }),
            'documentos': forms.ClearableFileInput(attrs={'class': 'file-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Filtros nos campos relacionados a Cliente
        self.fields['proprietario'].queryset = Cliente.objects.filter(tipo='Proprietario')
        self.fields['inquilino'].queryset = Cliente.objects.filter(tipo='Inquilino')

        if 'fiador' in self.fields:
            self.fields['fiador'].queryset = Cliente.objects.filter(tipo='Fiador(a)')

        if 'anuente' in self.fields:
            self.fields['anuente'].queryset = Cliente.objects.filter(tipo='Anuente')

        # Aplica Tailwind aos campos comuns
        for field_name, field in self.fields.items():
            if isinstance(field.widget, (forms.TextInput, forms.NumberInput, forms.DateInput, forms.Select)):
                field.widget.attrs['class'] = 'input input-bordered'

        # Substitui o widget dos campos monetários para exibir corretamente com moeda BRL
        money_fields = [
            'valor_aluguel', 'valor_pacote', 'valor_taxa_administracao_fixo',
            'valor_caucao', 'valor_segfi', 'valor_cap'
        ]

        for field_name in money_fields:
            if field_name in self.fields:
                self.fields[field_name].widget = MoneyWidget(
                    amount_widget=forms.TextInput(attrs={'class': 'input input-bordered currency', 'placeholder': 'R$ 0,00'}),
                    currency_widget=forms.HiddenInput(attrs={'value': 'BRL'})
                )

    def clean(self):
        cleaned_data = super().clean()
        money_fields = [
            'valor_aluguel', 'valor_pacote', 'valor_taxa_administracao_fixo',
            'valor_caucao', 'valor_segfi', 'valor_cap'
        ]
        for field in money_fields:
            value = cleaned_data.get(field)
            try:
                if isinstance(value, Money) and not value.currency:
                    value.currency = 'BRL'
                    cleaned_data[field] = value
                elif isinstance(value, (int, float, Decimal)):
                    cleaned_data[field] = Money(value, 'BRL')
                elif value is None:
                    cleaned_data[field] = None
            except Exception as e:
                print(f"Erro ao processar o campo {field}: {e}")
                cleaned_data[field] = Money(0, 'BRL')
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

class DespesaForm(forms.ModelForm):
    valor_total = forms.CharField(
        label='Valor (R$)',
        widget=forms.TextInput(attrs={'class': 'currency', 'placeholder': 'R$ 0,00'}),
        help_text='Informe o valor total ou o valor por parcela, conforme selecionado.'
    )

    class Meta:
        model = Despesa
        exclude = ['contrato']

    def __init__(self, *args, **kwargs):
        contrato = kwargs.pop('contrato', None)
        super().__init__(*args, **kwargs)
        if contrato:
            self.instance.contrato = contrato

    def clean_valor_total(self):
        valor = self.cleaned_data.get('valor_total')
        
        # Se já for um objeto Money, retorne diretamente
        if isinstance(valor, Money):
            return valor
            
        # Trata o formato brasileiro R$ 1.234,56 -> 1234.56
        if isinstance(valor, str):
            # Remove R$ e espaços
            valor = valor.replace('R$', '').strip()
            
            # Se tiver pontos e vírgulas (formato brasileiro)
            if ',' in valor:
                # Remove os pontos de milhar
                valor = valor.replace('.', '')
                # Substitui a vírgula decimal por ponto
                valor = valor.replace(',', '.')
                
            try:
                valor_decimal = Decimal(valor)
                return Money(valor_decimal, 'BRL')
            except:
                raise forms.ValidationError("Valor inválido")
        
        # Se for um número, apenas converte
        try:
            return Money(Decimal(str(valor)), 'BRL')
        except:
            raise forms.ValidationError("Valor inválido")

    def clean(self):
        cleaned_data = super().clean()
        valor = cleaned_data.get('valor_total')
        parcelas = cleaned_data.get('numero_parcelas')
        por_parcela = cleaned_data.get('valor_por_parcela')

        if valor and por_parcela and parcelas:
            total = valor.amount * int(parcelas)
            self.instance.valor_total = Money(total, 'BRL')
        elif valor:
            self.instance.valor_total = valor

        return cleaned_data