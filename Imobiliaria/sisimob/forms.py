from django import forms
from .models import Cliente, Imovel, Contrato

class ImovelForm(forms.ModelForm):
    class Meta:
        model = Imovel
        fields = '__all__'
        widgets = {
            'cep': forms.TextInput(attrs={'placeholder': 'Ex.: 00000-000'}),
            'endereco': forms.TextInput(attrs={'placeholder': 'Ex.: Rua das Flores'}),
            'numero': forms.TextInput(attrs={'placeholder': 'Ex.: 123'}),
            'complemento': forms.TextInput(attrs={'placeholder': 'Ex.: Apto 101'}),
            'bairro': forms.TextInput(attrs={'placeholder': 'Ex.: Centro'}),
            'cidade': forms.TextInput(attrs={'placeholder': 'Ex.: São Paulo'}),
            'estado': forms.TextInput(attrs={'placeholder': 'Ex.: SP'}),
            'iptu': forms.TextInput(attrs={'placeholder': 'Ex.: xxx.xxx.xxxx-x', 'class': 'iptu-mask'}),
            'comgas': forms.NumberInput(attrs={'placeholder': 'Ex.: 50.00'}),
            'sabesp': forms.NumberInput(attrs={'placeholder': 'Ex.: 30.00'}),
            'enel': forms.NumberInput(attrs={'placeholder': 'Ex.: 70.00'}),
        }


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = '__all__'
        widgets = {
            'tipo': forms.Select(attrs={'onchange': 'toggleFields()'}),
            'anuente': forms.Select(),
            'estado_civil': forms.Select(attrs={'onchange': 'toggleRegimeCasamento()'}),
            'pix_modalidade': forms.Select(),
            'nacionalidade': forms.TextInput(attrs={'class': 'form-control'}),
            'profissao': forms.TextInput(attrs={'class': 'form-control'}),
        }

class ContratoForm(forms.ModelForm):
    class Meta:
        model = Contrato
        fields = '__all__'
        widgets = {
            'data_inicio': forms.DateInput(attrs={'type': 'date'}),
            'data_fim': forms.DateInput(attrs={'type': 'date'}),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'fator_reajuste': forms.Select(attrs={'class': 'form-control'}),
            'multa_contratual': forms.Select(attrs={'class': 'form-control'}),
            'carencia_dias': forms.NumberInput(attrs={'class': 'form-control'}),
            'valor_iptu': forms.NumberInput(attrs={'step': '0.01'}),
            'tipo_pagamento': forms.Select(attrs={'onchange': 'toggleAluguelFields()'}),
            'documentos': forms.ClearableFileInput(),
        }

    def clean(self):
        cleaned_data = super().clean()
        # Validação adicional se necessário
        return cleaned_data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Define os campos para os grupos "Pacote" e "Despesas"
        self.fields['valor_aluguel'].widget.attrs['class'] = 'despesas-field'
        self.fields['valor_condominio'].widget.attrs['class'] = 'despesas-field'
        self.fields['valor_iptu'].widget.attrs['class'] = 'despesas-field'
        self.fields['valor_outros'].widget.attrs['class'] = 'despesas-field'
        self.fields['valor_pacote'].widget.attrs['class'] = 'pacote-field'
    
    def clean(self):
        cleaned_data = super().clean()
        tipo_pagamento = cleaned_data.get('tipo_pagamento')
        
        if tipo_pagamento == 'pacote':
            valor_pacote = cleaned_data.get('valor_pacote')
            if valor_pacote is None or valor_pacote <= 0:
                self.add_error('valor_pacote', 'Este campo é obrigatório.')
            # Define os campos de despesas como zero
            cleaned_data['valor_aluguel'] = 0.00
            cleaned_data['valor_condominio'] = 0.00
            cleaned_data['valor_iptu'] = 0.00
            cleaned_data['valor_outros'] = 0.00
        elif tipo_pagamento == 'despesas_separadas':
            valor_aluguel = cleaned_data.get('valor_aluguel')
            if valor_aluguel is None or valor_aluguel <= 0:
                self.add_error('valor_aluguel', 'Este campo é obrigatório.')
            # Define o valor_pacote como zero
            cleaned_data['valor_pacote'] = 0.00
        
        return cleaned_data

    def clean_carencia_dias(self):
        carencia = self.cleaned_data.get('carencia_dias')
        if carencia is None:
            return 0  # Define como zero se estiver vazio
        return carencia
    
    def clean_valor_iptu(self):
        valor_iptu = self.cleaned_data.get('valor_iptu')
        if valor_iptu is None:
            return 0.00  # Define como zero se estiver vazio
        return valor_iptu

    def __init__(self, *args, **kwargs):
        super(ContratoForm, self).__init__(*args, **kwargs)
        
        # Filtra os proprietários apenas para clientes do tipo "Proprietário(a)"
        self.fields['proprietario'].queryset = Cliente.objects.filter(
            tipo='Proprietario'  # Use o valor exato do campo 'tipo' no modelo Cliente
        )
        
        # Filtra os inquilinos apenas para clientes do tipo "Inquilino(a)"
        self.fields['inquilino'].queryset = Cliente.objects.filter(
            tipo='Inquilino'  # Use o valor exato do campo 'tipo' no modelo Cliente
        )

class GerarCobrancasForm(forms.ModelForm):
    class Meta:
        model = Contrato
        fields = '__all__'
        widgets = {
        }

class BaseAutocompleteForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Campos que devem ter autocomplete
        autocomplete_fields = {
            'Cliente': ['nacionalidade', 'profissao', 'fiador'],
            'Imovel': ['endereco', 'bairro', 'cidade'],
            'Contrato': ['tipo', 'garantia', 'seguradora_incendio'],
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