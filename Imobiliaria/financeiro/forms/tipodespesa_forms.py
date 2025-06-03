# financeiro/forms/tipodespesa_forms.py
"""
Formulários para Tipos de Despesa
=================================

Este módulo contém os formulários relacionados ao modelo TipoDespesa.
Inclui validações customizadas e configurações de exibição.
"""

from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q

from ..models import TipoDespesa


class TipoDespesaForm(forms.ModelForm):
    """
    Formulário para criação e edição de tipos de despesa
    
    Funcionalidades:
    - Validação de nome único (case-insensitive)
    - Campos com widgets customizados
    - Validações de negócio
    - Help texts informativos
    """
    
    class Meta:
        model = TipoDespesa
        fields = ['nome', 'descricao', 'ativo']
        
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Condomínio, IPTU, Água...',
                'maxlength': 50,
                'required': True
            }),
            'descricao': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Descrição opcional do tipo de despesa...',
                'rows': 3,
                'maxlength': 500
            }),
            'ativo': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
        
        labels = {
            'nome': 'Nome do Tipo',
            'descricao': 'Descrição',
            'ativo': 'Ativo'
        }
        
        help_texts = {
            'nome': 'Nome único para identificar o tipo de despesa (máximo 50 caracteres)',
            'descricao': 'Descrição opcional para detalhar o tipo de despesa',
            'ativo': 'Desmarque para inativar o tipo (não poderá ser usado em novas despesas)'
        }
    
    def __init__(self, *args, **kwargs):
        """
        Inicializa o formulário com configurações adicionais
        """
        super().__init__(*args, **kwargs)
        
        # Marca o campo nome como obrigatório visualmente
        self.fields['nome'].widget.attrs['required'] = 'required'
        
        # Se está editando, ajusta o help text do campo ativo
        if self.instance and self.instance.pk:
            self.fields['ativo'].help_text = (
                'Tipos inativos não podem ser usados em novas despesas. '
                'Só pode ser inativado se não houver despesas ativas associadas.'
            )
    
    def clean_nome(self):
        """
        Valida o campo nome
        
        Verifica:
        - Nome não pode estar vazio (após strip)
        - Nome deve ser único (case-insensitive)
        - Nome não pode ter apenas espaços
        
        Returns:
            str: Nome validado e limpo
            
        Raises:
            ValidationError: Se a validação falhar
        """
        nome = self.cleaned_data.get('nome', '').strip()
        
        if not nome:
            raise ValidationError('Nome é obrigatório.')
        
        # Verifica duplicatas (case-insensitive)
        # Exclui o próprio objeto se estiver editando
        queryset = TipoDespesa.objects.filter(nome__iexact=nome)
        
        if self.instance and self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise ValidationError(
                f'Já existe um tipo de despesa com o nome "{nome}". '
                'Escolha um nome diferente.'
            )
        
        return nome
    
    def clean_descricao(self):
        """
        Valida e limpa o campo descrição
        
        Returns:
            str: Descrição limpa (ou None se vazia)
        """
        descricao = self.cleaned_data.get('descricao', '').strip()
        
        # Retorna None se a descrição estiver vazia
        return descricao if descricao else None
    
    def clean(self):
        """
        Validação geral do formulário
        
        Verifica regras de negócio que envolvem múltiplos campos
        
        Returns:
            dict: Dados limpos validados
            
        Raises:
            ValidationError: Se alguma regra de negócio for violada
        """
        cleaned_data = super().clean()
        nome = cleaned_data.get('nome')
        ativo = cleaned_data.get('ativo', True)
        
        # Se está editando um tipo existente
        if self.instance and self.instance.pk:
            # Se está tentando inativar, verifica se pode
            if not ativo and self.instance.ativo:
                despesas_ativas = self.instance.despesas.filter(is_ativa=True).count()
                
                if despesas_ativas > 0:
                    raise ValidationError(
                        f'Não é possível inativar este tipo. '
                        f'Existem {despesas_ativas} despesas ativas associadas a ele. '
                        f'Inative ou remova essas despesas primeiro.'
                    )
        
        return cleaned_data
    
    def save(self, commit=True):
        """
        Salva o formulário com processamento adicional
        
        Args:
            commit (bool): Se deve salvar no banco imediatamente
            
        Returns:
            TipoDespesa: Instância salva ou não do tipo
        """
        instance = super().save(commit=False)
        
        # Garantir que o nome seja salvo com capitalização adequada
        if instance.nome:
            instance.nome = instance.nome.strip().title()
        
        if commit:
            instance.save()
        
        return instance


class TipoDespesaFiltroForm(forms.Form):
    """
    Formulário para filtros na listagem de tipos de despesa
    
    Usado na view de listagem para filtrar por status e busca
    """
    
    STATUS_CHOICES = [
        ('todos', 'Todos'),
        ('ativo', 'Apenas Ativos'),
        ('inativo', 'Apenas Inativos'),
    ]
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        initial='ativo',
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'onchange': 'this.form.submit();'
        }),
        label='Status'
    )
    
    busca = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Buscar por nome ou descrição...',
            'autocomplete': 'off'
        }),
        label='Buscar'
    )
    
    def __init__(self, *args, **kwargs):
        """
        Inicializa o formulário de filtros
        """
        super().__init__(*args, **kwargs)
        
        # Remove labels para usar apenas placeholders
        self.fields['busca'].label = ''