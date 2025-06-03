# financeiro/forms.py
from django import forms
from django.core.exceptions import ValidationError
from datetime import date
from financeiro.models.indice import IndiceInflacao


class IndiceInflacaoForm(forms.ModelForm):
    class Meta:
        model = IndiceInflacao
        fields = ['tipo', 'valor', 'data_referencia', 'fonte']
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'valor': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.0001',
                'placeholder': 'Ex: 0.5678'
            }),
            'data_referencia': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'fonte': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: IBGE'
            })
        }

    def clean_data_referencia(self):
        data_ref = self.cleaned_data.get('data_referencia')
        if data_ref and data_ref > date.today():
            raise ValidationError('Data não pode ser futura')
        return data_ref