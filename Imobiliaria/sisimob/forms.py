from django import forms
from .models import Cliente, Imovel, Contrato, Cobranca, Despesa
from decimal import Decimal
from datetime import datetime
from django_select2.forms import Select2MultipleWidget


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
        widgets = {
            'nome_completo': forms.TextInput(attrs={'class': 'w-full p-2 border rounded'}),
            'email': forms.EmailInput(attrs={'class': 'w-full p-2 border rounded'}),
            'telefone': forms.TextInput(attrs={'class': 'w-full p-2 border rounded'}),
            'tipo_pessoa': forms.Select(attrs={'class': 'w-full p-2 border rounded'}),
            'CPF': forms.TextInput(attrs={'class': 'w-full p-2 border rounded'}),
            'rg_rne': forms.TextInput(attrs={'class': 'w-full p-2 border rounded'}),
            'estado_civil': forms.Select(attrs={'class': 'w-full p-2 border rounded'}),
            'regime_casamento': forms.Select(attrs={'class': 'w-full p-2 border rounded'}),
            'anuente': forms.Select(attrs={'class': 'w-full p-2 border rounded'}),
            'razao_social': forms.TextInput(attrs={'class': 'w-full p-2 border rounded'}),
            'nome_fantasia': forms.TextInput(attrs={'class': 'w-full p-2 border rounded'}),
            'cnpj': forms.TextInput(attrs={'class': 'w-full p-2 border rounded'}),
            'representante_legal': forms.Select(attrs={'class': 'w-full p-2 border rounded'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        tipo_pessoa = self.initial.get('tipo_pessoa') or self.data.get('tipo_pessoa')

        if tipo_pessoa == 'F':
            self.fields['razao_social'].widget = forms.HiddenInput()
            self.fields['nome_fantasia'].widget = forms.HiddenInput()
            self.fields['cnpj'].widget = forms.HiddenInput()
            self.fields['representante_legal'].widget = forms.HiddenInput()
        elif tipo_pessoa == 'J':
            self.fields['CPF'].widget = forms.HiddenInput()
            self.fields['rg_rne'].widget = forms.HiddenInput()
            self.fields['estado_civil'].widget = forms.HiddenInput()
            self.fields['regime_casamento'].widget = forms.HiddenInput()
            self.fields['anuente'].widget = forms.HiddenInput()

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
            'proprietario': Select2MultipleWidget,
            'inquilino': Select2MultipleWidget,
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
            
        # Organizar os campos em uma ordem lógica
        field_order = [
            'tipo', 'is_recorrente', 'descricao', 'valor_total', 
            'paga', 'numero_parcelas', 'periodicidade', 'data_inicio',
            'cobranca_referencia', 'percentual_repassado', 'is_base_calculo_administracao'
        ]
        
        # Adicionar classes de estilo para manter consistência
        for field_name, field in self.fields.items():
            if field_name != 'valor_total':  # Já configurado acima
                field.widget.attrs.update({'class': 'block w-full pl-10 pr-3 py-2 border border-gray-700 bg-gray-900 text-white rounded-md focus:ring-blue-500 focus:border-blue-500 sm:text-sm'})
                
        # Adicionar comportamento dinâmico para campos específicos
            if field_name == 'tipo':
                field.widget.attrs.update({'onchange': 'handleTipoChange(this)'})

    def clean_valor_total(self):
        import re
        # Obtenha o valor bruto enviado pelo formulário
        valor_bruto = self.cleaned_data.get('valor_total')
        # Se não houver valor, retorne None ou 0
        if not valor_bruto:
            return 0
        # Debugando o valor recebido
        print(f"VALOR RECEBIDO NO FORM: {valor_bruto}")
        # Se o valor estiver em formato de string, converta para float
        if isinstance(valor_bruto, str):
            # Verifique se é um valor muito grande (possivelmente em centavos)
            try:
                # Remova símbolos de moeda, espaços e sinais
                is_negative = '-' in valor_bruto
                valor_limpo = valor_bruto.replace('R$', '').replace('-', '').strip()
                print(f"VALOR LIMPO: {valor_limpo}")
                # Trate o formato brasileiro de moeda (1.568,49)
                # Primeiro remova pontos de milhar
                valor_limpo = valor_limpo.replace('.', '')
                print(f"VALOR SEM MILHARES: {valor_limpo}")
                # Depois substitua vírgula por ponto para decimais
                valor_limpo = valor_limpo.replace(',', '.')
                print(f"VALOR COM PONTO DECIMAL: {valor_limpo}")
                # Verificar se é um número puro sem formatação
                if re.match(r'^\d+$', valor_limpo) and len(valor_limpo) > 4:
                    # Provavelmente é um valor em centavos, converter para reais
                    valor_numerico = Decimal(valor_limpo) / 100
                    print(f"VALOR INTERPRETADO COMO CENTAVOS: {valor_limpo} -> {valor_numerico}")
                else:
                    valor_numerico = Decimal(valor_limpo)
                    print(f"VALOR FINAL CONVERTIDO: {valor_numerico}")
                # Aplicar sinal negativo se necessário
                if is_negative:
                    valor_numerico = -valor_numerico
                    print(f"VALOR FINAL COM SINAL NEGATIVO: {valor_numerico}")
                return valor_numerico
            except ValueError as e:
                print(f"ERRO NA CONVERSÃO: {e}")
                raise forms.ValidationError("Valor inválido. Use o formato: R$ 0,00")
        return valor_bruto
    

from django import forms
from .models import Contrato, IndiceInflacao

class ReajusteContratosForm(forms.Form):
    data_inicio = forms.DateField(label="Data de Início do Reajuste", widget=forms.DateInput(attrs={'type': 'date'}))
    valor_manual = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        label="Valor Manual de Reajuste (%)",
        required=False,
        widget=forms.NumberInput(attrs={'step': '0.01'})
    )

    def clean(self):
        cleaned_data = super().clean()
        data_inicio = cleaned_data.get('data_inicio')
        valor_manual = cleaned_data.get('valor_manual')

        if not data_inicio:
            self.add_error('data_inicio', "Informe a data de início do reajuste.")

        if valor_manual is not None and valor_manual < 0:
            self.add_error('valor_manual', "O valor manual de reajuste não pode ser negativo.")

        return cleaned_data
    

from django import forms
from django.utils import timezone
from cadastro.models import Cobranca, Cliente, Contrato

class CobrancaFiltroForm(forms.Form):
    """
    Formulário para filtrar cobranças no painel financeiro
    """
    STATUS_CHOICES = [('', '-- Todos os Status --')] + list(Cobranca.STATUS_CHOICES)
    STATUS_REPASSE_CHOICES = [('', '-- Todos os Status --')] + list(Cobranca.STATUS_REPASSE_CHOICES)
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES, 
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    status_repasse = forms.ChoiceField(
        choices=STATUS_REPASSE_CHOICES, 
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    data_inicio = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    data_fim = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    proprietario = forms.ModelChoiceField(
        queryset=Cliente.objects.filter(tipo='Proprietario'),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select select2'})
    )
    
    inquilino = forms.ModelChoiceField(
        queryset=Cliente.objects.filter(tipo='Inquilino'),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select select2'})
    )
    
    contrato = forms.ModelChoiceField(
        queryset=Contrato.objects.filter(ativo=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select select2'})
    )


class PagamentoForm(forms.Form):
    """
    Formulário para registrar pagamento de cobranças
    """
    data_pagamento = forms.DateField(
        initial=timezone.now().date(),
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    observacao = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )


class RepasseForm(forms.Form):
    """
    Formulário para registrar repasse aos proprietários
    """
    data_repasse = forms.DateField(
        initial=timezone.now().date(),
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    observacao = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )