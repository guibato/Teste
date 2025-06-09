from django import forms
from sisimob.models import Cliente


class ClienteForm(forms.ModelForm):
    """
    Formulário para cadastro e edição de clientes
    """
    
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

        # Obtém o tipo de pessoa do formulário
        tipo_pessoa = self.initial.get('tipo_pessoa') or self.data.get('tipo_pessoa')

        # Esconde campos baseado no tipo de pessoa
        if tipo_pessoa == 'F':  # Pessoa Física
            self._hide_pj_fields()
        elif tipo_pessoa == 'J':  # Pessoa Jurídica
            self._hide_pf_fields()

    def _hide_pf_fields(self):
        """Esconde campos específicos de Pessoa Física"""
        pf_fields = ['CPF', 'rg_rne', 'estado_civil', 'regime_casamento', 'anuente']
        for field_name in pf_fields:
            if field_name in self.fields:
                self.fields[field_name].widget = forms.HiddenInput()

    def _hide_pj_fields(self):
        """Esconde campos específicos de Pessoa Jurídica"""
        pj_fields = ['razao_social', 'nome_fantasia', 'cnpj', 'representante_legal']
        for field_name in pj_fields:
            if field_name in self.fields:
                self.fields[field_name].widget = forms.HiddenInput()

    def clean_CPF(self):
        """Validação customizada para CPF"""
        cpf = self.cleaned_data.get('CPF')
        tipo_pessoa = self.cleaned_data.get('tipo_pessoa')
        
        if tipo_pessoa == 'F' and not cpf:
            raise forms.ValidationError("CPF é obrigatório para Pessoa Física.")
        
        return cpf

    def clean_cnpj(self):
        """Validação customizada para CNPJ"""
        cnpj = self.cleaned_data.get('cnpj')
        tipo_pessoa = self.cleaned_data.get('tipo_pessoa')
        
        if tipo_pessoa == 'J' and not cnpj:
            raise forms.ValidationError("CNPJ é obrigatório para Pessoa Jurídica.")
        
        return cnpj

    def clean_razao_social(self):
        """Validação customizada para Razão Social"""
        razao_social = self.cleaned_data.get('razao_social')
        tipo_pessoa = self.cleaned_data.get('tipo_pessoa')
        
        if tipo_pessoa == 'J' and not razao_social:
            raise forms.ValidationError("Razão Social é obrigatória para Pessoa Jurídica.")
        
        return razao_social


class ClienteFiltroForm(forms.Form):
    """
    Formulário para filtrar clientes na listagem
    """
    TIPO_CHOICES = [('', '-- Todos os Tipos --')] + Cliente.TIPO_CLIENTE_CHOICES
    TIPO_PESSOA_CHOICES = [('', '-- Todos --')] + Cliente.TIPO_PESSOA_CHOICES
    
    nome = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Digite o nome...'
        })
    )
    
    tipo = forms.ChoiceField(
        choices=TIPO_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    tipo_pessoa = forms.ChoiceField(
        choices=TIPO_PESSOA_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    cidade = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Digite a cidade...'
        })
    )


class ClienteBuscaForm(forms.Form):
    """
    Formulário simples para busca de clientes
    """
    busca = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Buscar por nome, CPF, CNPJ ou email...'
        })
    )