# financeiro/forms/tipodespesa_forms.py - ADAPTADO AO MODELO ATUALIZADO
"""
Formulários para Tipos de Despesa - Com Categoria e Taxa Admin
=============================================================

Este módulo contém os formulários relacionados ao modelo TipoDespesa atualizado.
Inclui validações customizadas, configurações de exibição e suporte aos novos campos.
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
    - Suporte a categorias
    - Configuração de taxa administrativa padrão
    - Campos com widgets customizados
    - Validações de negócio
    - Help texts informativos
    """
    
    class Meta:
        model = TipoDespesa
        fields = ['nome', 'categoria', 'descricao', 'incidencia_taxa_admin_padrao', 'ativo']
        
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Ex: Condomínio, IPTU, Água...',
                'maxlength': 50,
                'required': True
            }),
            'categoria': forms.Select(attrs={
                'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500',
                'required': True
            }),
            'descricao': forms.Textarea(attrs={
                'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Descrição opcional do tipo de despesa...',
                'rows': 3,
                'maxlength': 500
            }),
            'incidencia_taxa_admin_padrao': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-blue-600 bg-gray-700 border-gray-600 rounded focus:ring-blue-500 focus:ring-2'
            }),
            'ativo': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-blue-600 bg-gray-700 border-gray-600 rounded focus:ring-blue-500 focus:ring-2'
            })
        }
        
        labels = {
            'nome': 'Nome do Tipo',
            'categoria': 'Categoria',
            'descricao': 'Descrição',
            'incidencia_taxa_admin_padrao': 'Taxa Administrativa Padrão',
            'ativo': 'Ativo'
        }
        
        help_texts = {
            'nome': 'Nome único para identificar o tipo de despesa (máximo 50 caracteres)',
            'categoria': 'Categoria que melhor classifica este tipo de despesa',
            'descricao': 'Descrição opcional para detalhar o tipo de despesa',
            'incidencia_taxa_admin_padrao': 'Por padrão, despesas deste tipo têm incidência de taxa administrativa?',
            'ativo': 'Desmarque para inativar o tipo (não poderá ser usado em novas despesas)'
        }
    
    def __init__(self, *args, **kwargs):
        """
        Inicializa o formulário com configurações adicionais
        """
        super().__init__(*args, **kwargs)
        
        # Marca os campos obrigatórios visualmente
        self.fields['nome'].widget.attrs['required'] = 'required'
        self.fields['categoria'].widget.attrs['required'] = 'required'
        
        # Campo ativo marcado por padrão para novos registros
        if not self.instance.pk:
            self.fields['ativo'].initial = True
        
        # Auto-configurar taxa admin baseada na categoria (para novos registros)
        if not self.instance.pk:
            # Categorias que geralmente têm taxa administrativa
            categorias_com_taxa = ['operacional', 'manutencao', 'melhorias']
            categoria_inicial = self.initial.get('categoria') or self.data.get('categoria')
            
            if categoria_inicial in categorias_com_taxa:
                self.fields['incidencia_taxa_admin_padrao'].initial = True
            else:
                self.fields['incidencia_taxa_admin_padrao'].initial = False
        
        # Se está editando, ajusta o help text do campo ativo
        if self.instance and self.instance.pk:
            despesas_count = self.instance.despesas.count()
            if despesas_count > 0:
                self.fields['ativo'].help_text = (
                    f'Este tipo possui {despesas_count} despesas associadas. '
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
        - Nome deve ter pelo menos 2 caracteres
        
        Returns:
            str: Nome validado e limpo
            
        Raises:
            ValidationError: Se a validação falhar
        """
        nome = self.cleaned_data.get('nome', '').strip()
        
        if not nome:
            raise ValidationError('Nome é obrigatório.')
        
        if len(nome) < 2:
            raise ValidationError('Nome deve ter pelo menos 2 caracteres.')
        
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
    
    def clean_categoria(self):
        """
        Valida o campo categoria
        
        Returns:
            str: Categoria validada
            
        Raises:
            ValidationError: Se a categoria for inválida
        """
        categoria = self.cleaned_data.get('categoria')
        
        if not categoria:
            raise ValidationError('Categoria é obrigatória.')
        
        # Verificar se a categoria está nas opções válidas
        categorias_validas = [choice[0] for choice in TipoDespesa._meta.get_field('categoria').choices]
        
        if categoria not in categorias_validas:
            raise ValidationError('Categoria inválida.')
        
        return categoria
    
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
        categoria = cleaned_data.get('categoria')
        ativo = cleaned_data.get('ativo', True)
        incidencia_taxa_admin_padrao = cleaned_data.get('incidencia_taxa_admin_padrao', False)
        
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
        
        # Validação de consistência: sugerir configuração baseada na categoria
        if categoria and nome:
            sugestoes_taxa = {
                'operacional': True,   # Condomínio, Taxa Admin -> geralmente com taxa
                'manutencao': True,    # Reparos -> geralmente com taxa
                'melhorias': None,     # Reformas -> pode variar
                'impostos': False,     # IPTU, Taxas Gov -> geralmente sem taxa
                'servicos': False,     # Água, Luz -> geralmente sem taxa
                'outros': None         # Outros -> pode variar
            }
            
            sugestao = sugestoes_taxa.get(categoria)
            
            # Se há uma sugestão forte e o usuário escolheu diferente, avisar (mas não bloquear)
            if sugestao is not None and incidencia_taxa_admin_padrao != sugestao:
                # Não vamos bloquear, apenas sugerir via JavaScript no template
                pass
        
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
    
    Usado na view de listagem para filtrar por status, categoria, taxa admin e busca
    """
    
    STATUS_CHOICES = [
        ('ativo', 'Apenas Ativos'),
        ('inativo', 'Apenas Inativos'),
        ('todos', 'Todos'),
    ]
    
    # NOVO: Filtro por categoria
    CATEGORIA_CHOICES = [
        ('', 'Todas as categorias'),
        ('operacional', 'Operacional'),
        ('manutencao', 'Manutenção'),
        ('melhorias', 'Melhorias'),
        ('impostos', 'Impostos/Taxas'),
        ('servicos', 'Serviços'),
        ('outros', 'Outros'),
    ]
    
    # NOVO: Filtro por taxa admin
    TAXA_ADMIN_CHOICES = [
        ('', 'Todos'),
        ('com_taxa', 'Com Taxa Padrão'),
        ('sem_taxa', 'Sem Taxa Padrão'),
    ]
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        initial='ativo',
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500',
            'onchange': 'this.form.submit();'
        }),
        label='Status'
    )
    
    categoria = forms.ChoiceField(
        choices=CATEGORIA_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500',
            'onchange': 'this.form.submit();'
        }),
        label='Categoria'
    )
    
    taxa_admin = forms.ChoiceField(
        choices=TAXA_ADMIN_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500',
            'onchange': 'this.form.submit();'
        }),
        label='Taxa Admin'
    )
    
    busca = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500',
            'placeholder': 'Buscar por nome ou descrição...',
            'autocomplete': 'off'
        }),
        label='Buscar'
    )


class TipoDespesaQuickCreateForm(forms.ModelForm):
    """
    Formulário simplificado para criação rápida de tipos de despesa
    
    Usado em modais ou situações onde se precisa criar rapidamente um tipo
    """
    
    class Meta:
        model = TipoDespesa
        fields = ['nome', 'categoria', 'incidencia_taxa_admin_padrao']
        
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome do tipo...',
                'maxlength': 50,
                'required': True
            }),
            'categoria': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'incidencia_taxa_admin_padrao': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
        
        labels = {
            'nome': 'Nome',
            'categoria': 'Categoria',
            'incidencia_taxa_admin_padrao': 'Com taxa administrativa por padrão'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Sempre ativo para criação rápida
        self.instance.ativo = True
        
        # Auto-configurar taxa baseada na categoria
        if 'categoria' in self.data:
            categoria = self.data['categoria']
            if categoria in ['operacional', 'manutencao', 'melhorias']:
                self.fields['incidencia_taxa_admin_padrao'].initial = True
    
    def clean_nome(self):
        """Validação simplificada do nome"""
        nome = self.cleaned_data.get('nome', '').strip().title()
        
        if not nome:
            raise ValidationError('Nome é obrigatório.')
        
        if TipoDespesa.objects.filter(nome__iexact=nome).exists():
            raise ValidationError('Já existe um tipo com este nome.')
        
        return nome
    
    def save(self, commit=True):
        """Salva o tipo com configurações padrão"""
        instance = super().save(commit=False)
        instance.ativo = True
        
        if commit:
            instance.save()
        
        return instance


class TipoDespesaBulkActionForm(forms.Form):
    """
    Formulário para ações em lote nos tipos de despesa
    """
    
    ACTION_CHOICES = [
        ('', 'Selecione uma ação...'),
        ('ativar', 'Ativar selecionados'),
        ('inativar', 'Inativar selecionados'),
        ('mudar_categoria', 'Alterar categoria'),
        ('configurar_taxa', 'Configurar taxa administrativa'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label='Ação'
    )
    
    tipos_selecionados = forms.ModelMultipleChoiceField(
        queryset=TipoDespesa.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label='Tipos selecionados'
    )
    
    # Campos condicionais para certas ações
    nova_categoria = forms.ChoiceField(
        choices=[],  # Preenchido no __init__
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label='Nova categoria'
    )
    
    taxa_admin_padrao = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='Taxa administrativa padrão'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Preencher opções de categoria
        self.fields['nova_categoria'].choices = [
            ('', 'Selecione uma categoria...')
        ] + list(TipoDespesa._meta.get_field('categoria').choices)
    
    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        tipos_selecionados = cleaned_data.get('tipos_selecionados')
        
        if not tipos_selecionados:
            raise ValidationError('Selecione pelo menos um tipo.')
        
        if action == 'mudar_categoria' and not cleaned_data.get('nova_categoria'):
            raise ValidationError('Selecione a nova categoria.')
        
        # Verificar se pode inativar os tipos selecionados
        if action == 'inativar':
            for tipo in tipos_selecionados:
                despesas_ativas = tipo.despesas.filter(is_ativa=True).count()
                if despesas_ativas > 0:
                    raise ValidationError(
                        f'Não é possível inativar o tipo "{tipo.nome}" - '
                        f'possui {despesas_ativas} despesas ativas.'
                    )
        
        return cleaned_data