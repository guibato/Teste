from django import forms
from .models import Cliente, Imovel, Contrato
from django.core.exceptions import ValidationError


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
            'pix_valor': forms.TextInput(),
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
        }

    def clean(self):
        cleaned_data = super().clean()
        # Validação adicional se necessário
        return cleaned_data

    def clean_carencia_dias(self):
        carencia = self.cleaned_data.get('carencia_dias')
        if carencia is None:
            return 0  # Define como zero se estiver vazio
        return carencia
            
        