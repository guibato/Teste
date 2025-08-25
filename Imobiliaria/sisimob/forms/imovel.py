from django import forms
from cadastro.models import Imovel


class ImovelForm(forms.ModelForm):
    """
    Formulário para cadastro e edição de imóveis
    """
    
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
            'cep': forms.TextInput(attrs={
                'placeholder': 'Ex.: 00000-000', 
                'class': 'cep-mask form-control'
            }),
            'endereco': forms.TextInput(attrs={
                'placeholder': 'Ex.: Rua das Flores',
                'class': 'form-control'
            }),
            'numero': forms.TextInput(attrs={
                'placeholder': 'Ex.: 123',
                'class': 'form-control'
            }),
            'complemento': forms.TextInput(attrs={
                'placeholder': 'Ex.: Apto 101',
                'class': 'form-control'
            }),
            'bairro': forms.TextInput(attrs={
                'placeholder': 'Ex.: Centro',
                'class': 'form-control'
            }),
            'cidade': forms.TextInput(attrs={
                'placeholder': 'Ex.: São Paulo',
                'class': 'form-control'
            }),
            'estado': forms.TextInput(attrs={
                'placeholder': 'Ex.: SP',
                'class': 'form-control',
                'maxlength': '2'
            }),
            'iptu': forms.TextInput(attrs={
                'placeholder': 'Ex.: xxx.xxx.xxxx-x', 
                'class': 'iptu-mask form-control'
            }),
            'comgas': forms.NumberInput(attrs={
                'placeholder': 'Ex.: 50.00', 
                'class': 'form-control',
                'step': '0.01'
            }),
            'sabesp': forms.NumberInput(attrs={
                'placeholder': 'Ex.: 30.00', 
                'class': 'form-control',
                'step': '0.01'
            }),
            'enel': forms.NumberInput(attrs={
                'placeholder': 'Ex.: 70.00', 
                'class': 'form-control',
                'step': '0.01'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Campos obrigatórios
        required_fields = ['cep', 'endereco', 'numero', 'cidade', 'estado']
        for field_name in required_fields:
            if field_name in self.fields:
                self.fields[field_name].required = True

    def clean_cep(self):
        """Validação e formatação do CEP"""
        cep = self.cleaned_data.get('cep')
        if cep:
            # Remove caracteres não numéricos
            cep = ''.join(filter(str.isdigit, cep))
            
            # Valida se tem 8 dígitos
            if len(cep) != 8:
                raise forms.ValidationError("CEP deve ter 8 dígitos.")
            
            # Formata com hífen
            return f"{cep[:5]}-{cep[5:]}"
        
        return cep

    def clean_estado(self):
        """Validação e formatação do estado"""
        estado = self.cleaned_data.get('estado')
        if estado:
            estado = estado.upper()
            
    def clean_estado(self):
        """Validação e formatação do estado"""
        estado = self.cleaned_data.get('estado')
        if estado:
            estado = estado.upper()
            
            # Lista de UFs válidas
            ufs_validas = [
                'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 
                'MA', 'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 
                'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO'
            ]
            
            if estado not in ufs_validas:
                raise forms.ValidationError("Digite uma UF válida.")
            
            return estado
        
        return estado

    def clean(self):
        """Validações gerais do formulário"""
        cleaned_data = super().clean()
        
        # Validação de valores de utilities
        utilities = ['comgas', 'sabesp', 'enel']
        for utility in utilities:
            valor = cleaned_data.get(utility)
            if valor is not None and valor < 0:
                self.add_error(utility, "Valor não pode ser negativo.")
        
        return cleaned_data


class ImovelFiltroForm(forms.Form):
    """
    Formulário para filtrar imóveis na listagem
    """
    endereco = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Digite o endereço...'
        })
    )
    
    bairro = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Digite o bairro...'
        })
    )
    
    cidade = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Digite a cidade...'
        })
    )
    
    estado = forms.CharField(
        max_length=2,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'UF'
        })
    )


class ImovelBuscaForm(forms.Form):
    """
    Formulário simples para busca de imóveis
    """
    busca = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Buscar por endereço, bairro ou cidade...'
        })
    )