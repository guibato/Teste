# financeiro/forms/despesa_forms.py - ADAPTADO AO MODELO ATUALIZADO
"""
Formulários para Despesas - Versão com Taxa de Administração
============================================================
"""

from django import forms
from django.core.exceptions import ValidationError
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from decimal import Decimal

from ..models import Despesa, TipoDespesa


class DespesaForm(forms.ModelForm):
    """
    Formulário para criação e edição de despesas
    Com suporte completo a taxa de administração e despesas recorrentes
    """
    
    # Campos adicionais não salvos no modelo
    tipo_valor = forms.ChoiceField(
        choices=[
            ('total', 'Valor Total'),
            ('parcela', 'Valor por Parcela')
        ],
        initial='total',
        widget=forms.RadioSelect(attrs={
            'class': 'form-radio text-blue-600 bg-gray-700 border-gray-600 focus:ring-blue-500'
        }),
        label='Tipo de Valor',
        help_text='Escolha se está informando o valor total ou o valor de cada parcela'
    )
    
    valor_parcela = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg pl-12 pr-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500',
            'step': '0.01',
            'min': '0',
            'placeholder': '0,00'
        }),
        label='Valor por Parcela (R$)',
        help_text='Valor de cada parcela individual'
    )
    
    gerar_recorrentes = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'w-4 h-4 text-blue-600 bg-gray-700 border-gray-600 rounded focus:ring-blue-500 focus:ring-2'
        }),
        label='Gerar Despesas Recorrentes',
        help_text='Marca para criar automaticamente despesas futuras (ex: Condomínio todo mês)'
    )
    
    quantidade_recorrentes = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=60,
        initial=12,
        widget=forms.NumberInput(attrs={
            'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500',
            'min': '1',
            'max': '60'
        }),
        label='Quantidade de Recorrências',
        help_text='Quantas despesas recorrentes criar (máximo 60)'
    )
    
    class Meta:
        model = Despesa
        fields = [
            'contrato', 'tipo', 'descricao', 'cobranca_referencia',
            'valor_total', 'incidencia_taxa_admin', 'percentual_com_incidencia', 
            'taxa_admin_especifica', 'paga_por', 'numero_parcelas', 'periodicidade', 
            'data_inicio', 'data_fim_prevista', 'percentual_repassado',
            'is_ativa', 'is_recorrente', 'comprovante', 'observacoes'
        ]
        
        widgets = {
            'contrato': forms.Select(attrs={
                'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500',
                'required': True
            }),
            'tipo': forms.Select(attrs={
                'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500',
                'required': True
            }),
            'descricao': forms.TextInput(attrs={
                'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Descrição da despesa (opcional)...'
            }),
            'cobranca_referencia': forms.TextInput(attrs={
                'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Ex: 01/2025, Março/2025...'
            }),
            'valor_total': forms.NumberInput(attrs={
                'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg pl-12 pr-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500',
                'step': '0.01',
                'min': '0',
                'placeholder': '0,00',
                'required': True
            }),
            # NOVOS: Campos de Taxa de Administração
            'incidencia_taxa_admin': forms.RadioSelect(attrs={
                'class': 'form-radio text-blue-600 bg-gray-700 border-gray-600 focus:ring-blue-500'
            }),
            'percentual_com_incidencia': forms.NumberInput(attrs={
                'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 pr-8 focus:outline-none focus:ring-2 focus:ring-blue-500',
                'step': '0.01',
                'min': '0',
                'max': '100',
                'placeholder': '0,00'
            }),
            'taxa_admin_especifica': forms.NumberInput(attrs={
                'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 pr-8 focus:outline-none focus:ring-2 focus:ring-blue-500',
                'step': '0.01',
                'min': '0',
                'max': '100',
                'placeholder': '8,00'
            }),
            'paga_por': forms.Select(attrs={
                'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500'
            }),
            'numero_parcelas': forms.NumberInput(attrs={
                'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500',
                'min': '1',
                'value': '1'
            }),
            'periodicidade': forms.Select(attrs={
                'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500'
            }),
            'data_inicio': forms.DateInput(attrs={
                'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500',
                'type': 'date',
                'required': True
            }),
            'data_fim_prevista': forms.DateInput(attrs={
                'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500',
                'type': 'date'
            }),
            'percentual_repassado': forms.NumberInput(attrs={
                'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 pr-8 focus:outline-none focus:ring-2 focus:ring-blue-500',
                'step': '0.01',
                'min': '0',
                'max': '100',
                'value': '100'
            }),
            'is_ativa': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-blue-600 bg-gray-700 border-gray-600 rounded focus:ring-blue-500 focus:ring-2'
            }),
            'is_recorrente': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-blue-600 bg-gray-700 border-gray-600 rounded focus:ring-blue-500 focus:ring-2'
            }),
            'comprovante': forms.FileInput(attrs={
                'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500',
                'accept': '.pdf,.jpg,.jpeg,.png'
            }),
            'observacoes': forms.Textarea(attrs={
                'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500',
                'rows': 3,
                'placeholder': 'Observações adicionais...'
            })
        }
        
        labels = {
            'contrato': 'Contrato',
            'tipo': 'Tipo de Despesa',
            'descricao': 'Descrição',
            'cobranca_referencia': 'Referência de Cobrança',
            'valor_total': 'Valor Total (R$)',
            'incidencia_taxa_admin': 'Incidência de Taxa Administrativa',
            'percentual_com_incidencia': 'Percentual com Incidência (%)',
            'taxa_admin_especifica': 'Taxa Administrativa Específica (%)',
            'paga_por': 'Paga Por',
            'numero_parcelas': 'Número de Parcelas',
            'periodicidade': 'Periodicidade',
            'data_inicio': 'Data de Início',
            'data_fim_prevista': 'Data Fim Prevista',
            'percentual_repassado': 'Percentual Repassado (%)',
            'is_ativa': 'Ativa',
            'is_recorrente': 'Recorrente',
            'comprovante': 'Comprovante',
            'observacoes': 'Observações'
        }
        
        help_texts = {
            'contrato': 'Selecione o contrato ao qual esta despesa se refere',
            'tipo': 'Selecione o tipo de despesa',
            'cobranca_referencia': 'Referência do período de cobrança (ex: 01/2025)',
            'valor_total': 'Valor total da despesa (será dividido pelas parcelas)',
            'incidencia_taxa_admin': 'Define se esta despesa tem incidência de taxa administrativa',
            'percentual_com_incidencia': 'Para incidência parcial: percentual do valor que tem incidência (0-100%)',
            'taxa_admin_especifica': 'Taxa específica para esta despesa (deixe vazio para usar padrão do contrato)',
            'paga_por': 'Quem será responsável pelo pagamento',
            'numero_parcelas': 'Em quantas parcelas será dividida',
            'periodicidade': 'Frequência das parcelas',
            'data_inicio': 'Data de início da primeira parcela',
            'data_fim_prevista': 'Data prevista para fim da despesa (calculada automaticamente se não informada)',
            'percentual_repassado': 'Percentual do valor que é repassado',
            'is_ativa': 'Desmarque para inativar a despesa',
            'is_recorrente': 'Marca se é uma despesa recorrente',
            'comprovante': 'Arquivo comprobatório da despesa (PDF, JPG, PNG)',
            'observacoes': 'Informações adicionais sobre a despesa'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fields['percentual_com_incidencia'].required = False

        # Filtrar apenas tipos ativos
        self.fields['tipo'].queryset = TipoDespesa.objects.filter(ativo=True).order_by('categoria', 'nome')
        
        # Configurar campo contrato
        try:
            from cadastro.models import Contrato
            self.fields['contrato'].queryset = Contrato.objects.filter(
                ativo=True
            ).order_by('-data_inicio')
        except ImportError:
            pass
        
        # Campo is_ativa marcado por padrão para novos registros
        if not self.instance.pk:
            self.fields['is_ativa'].initial = True
            self.fields['incidencia_taxa_admin'].initial = 'nao'
        
        # Se está editando, desabilitar campos de recorrência
        if self.instance.pk:
            self.fields['gerar_recorrentes'].widget.attrs['disabled'] = True
            self.fields['quantidade_recorrentes'].widget.attrs['disabled'] = True
            self.fields['gerar_recorrentes'].help_text = 'Recorrência só pode ser configurada na criação'
        
        # Configurar incidência baseada no tipo selecionado (se houver)
        if self.instance.pk and self.instance.tipo:
            if not self.instance.incidencia_taxa_admin:
                # Auto-configurar baseado no padrão do tipo
                if self.instance.tipo.incidencia_taxa_admin_padrao:
                    self.fields['incidencia_taxa_admin'].initial = 'sim'
                else:
                    self.fields['incidencia_taxa_admin'].initial = 'nao'
    
    def clean(self):
        """Validação geral do formulário"""
        cleaned_data = super().clean()
        
        tipo_valor = cleaned_data.get('tipo_valor')
        valor_total = cleaned_data.get('valor_total')
        valor_parcela = cleaned_data.get('valor_parcela')
        numero_parcelas = cleaned_data.get('numero_parcelas', 1)
        gerar_recorrentes = cleaned_data.get('gerar_recorrentes')
        quantidade_recorrentes = cleaned_data.get('quantidade_recorrentes')
        
        # NOVA: Validação de taxa administrativa
        incidencia_taxa = cleaned_data.get('incidencia_taxa_admin')
        percentual_incidencia = cleaned_data.get('percentual_com_incidencia')
        taxa_especifica = cleaned_data.get('taxa_admin_especifica')
        
        # Validar campos de valor
        if tipo_valor == 'parcela':
            if not valor_parcela or valor_parcela <= 0:
                raise ValidationError({
                    'valor_parcela': 'Valor por parcela é obrigatório quando selecionado.'
                })
            # Calcular valor total baseado na parcela
            cleaned_data['valor_total'] = valor_parcela * numero_parcelas
        else:
            if not valor_total or valor_total <= 0:
                raise ValidationError({
                    'valor_total': 'Valor total é obrigatório quando selecionado.'
                })
        
        # NOVA: Validar taxa administrativa
        if incidencia_taxa == 'parcial':
            if not percentual_incidencia or percentual_incidencia <= 0:
                raise ValidationError({
                    'percentual_com_incidencia': 'Para incidência parcial, informe o percentual (maior que 0).'
                })
            if percentual_incidencia > 100:
                raise ValidationError({
                    'percentual_com_incidencia': 'Percentual não pode ser maior que 100%.'
                })
        
        if taxa_especifica is not None:
            if taxa_especifica < 0:
                raise ValidationError({
                    'taxa_admin_especifica': 'Taxa de administração não pode ser negativa.'
                })
            if taxa_especifica > 50:  # Limite razoável
                raise ValidationError({
                    'taxa_admin_especifica': 'Taxa de administração muito alta (máximo 50%).'
                })
        
        # Validar recorrência
        if gerar_recorrentes:
            if not quantidade_recorrentes or quantidade_recorrentes < 1:
                cleaned_data['quantidade_recorrentes'] = 12  # Padrão
            
            # Verificar se o tipo de despesa é adequado para recorrência
            tipo_despesa = cleaned_data.get('tipo')
            if tipo_despesa:
                tipos_recorrentes = ['condomínio', 'condominio', 'iptu', 'água', 'agua', 'luz', 'energia']
                if not any(palavra in tipo_despesa.nome.lower() for palavra in tipos_recorrentes):
                    # Avisar mas não bloquear
                    pass
        
        # Validar data de início
        data_inicio = cleaned_data.get('data_inicio')
        if data_inicio:
            data_limite = date.today() - timedelta(days=365*2)  # 2 anos atrás
            if data_inicio < data_limite:
                raise ValidationError({
                    'data_inicio': 'Data de início não pode ser anterior a 2 anos.'
                })
        
        # Validar data fim prevista
        data_fim = cleaned_data.get('data_fim_prevista')
        if data_fim and data_inicio:
            if data_fim <= data_inicio:
                raise ValidationError({
                    'data_fim_prevista': 'Data fim deve ser posterior à data de início.'
                })
        
        # Validar percentual repassado
        percentual_repassado = cleaned_data.get('percentual_repassado')
        if percentual_repassado is not None:
            if percentual_repassado < 0 or percentual_repassado > 100:
                raise ValidationError({
                    'percentual_repassado': 'Percentual deve estar entre 0% e 100%.'
                })
        
        return cleaned_data
    
    def clean_valor_total(self):
        """Valida o valor total"""
        valor = self.cleaned_data.get('valor_total')
        tipo_valor = self.data.get('tipo_valor', 'total')
        
        # Se está usando valor por parcela, não validar aqui
        if tipo_valor == 'parcela':
            return valor
        
        if valor is None or valor <= 0:
            raise ValidationError('O valor deve ser maior que zero.')
        
        if valor > Decimal('9999999.99'):  # Limite do campo
            raise ValidationError('Valor muito alto.')
        
        return valor
    
    def clean_valor_parcela(self):
        """Valida o valor por parcela"""
        valor_parcela = self.cleaned_data.get('valor_parcela')
        tipo_valor = self.data.get('tipo_valor', 'total')
        
        if tipo_valor == 'parcela':
            if valor_parcela is None or valor_parcela <= 0:
                raise ValidationError('O valor por parcela deve ser maior que zero.')
            
            if valor_parcela > Decimal('9999999.99'):
                raise ValidationError('Valor por parcela muito alto.')
        
        return valor_parcela
    
    def clean_numero_parcelas(self):
        """Valida número de parcelas"""
        parcelas = self.cleaned_data.get('numero_parcelas')
        
        if parcelas is None or parcelas < 1:
            raise ValidationError('Número de parcelas deve ser maior que zero.')
        
        if parcelas > 360:  # Máximo 30 anos
            raise ValidationError('Número de parcelas não pode ser maior que 360.')
        
        return parcelas
    
    def clean_percentual_com_incidencia(self):
        """Valida percentual com incidência"""
        percentual = self.cleaned_data.get('percentual_com_incidencia')
        incidencia = self.data.get('incidencia_taxa_admin')
        

        if incidencia == 'parcial':
            if percentual is None:
                raise ValidationError('Percentual é obrigatório para incidência parcial.')
            if percentual <= 0 or percentual > 100:
                raise ValidationError('Percentual deve estar entre 0,01% e 100%.')
        
        return Decimal('0.00')
    
    def clean_comprovante(self):
        """Valida arquivo de comprovante"""
        arquivo = self.cleaned_data.get('comprovante')
        
        if arquivo:
            # Verificar tamanho (máximo 10MB)
            if arquivo.size > 10 * 1024 * 1024:
                raise ValidationError('Arquivo muito grande. Máximo 10MB.')
            
            # Verificar tipo
            tipos_permitidos = ['application/pdf', 'image/jpeg', 'image/png', 'image/jpg']
            if arquivo.content_type not in tipos_permitidos:
                raise ValidationError('Tipo de arquivo não permitido. Use PDF, JPG ou PNG.')
        
        return arquivo
    
    def save(self, commit=True):
        """
        Salva o formulário com processamento adicional
        """
        instance = super().save(commit=False)
        
        # Auto-configurar is_recorrente se está gerando recorrentes
        gerar_recorrentes = self.cleaned_data.get('gerar_recorrentes', False)
        if gerar_recorrentes:
            instance.is_recorrente = True
        
        if commit:
            instance.save()
        
        return instance


class DespesaFiltroForm(forms.Form):
    """
    Formulário para filtros na listagem de despesas
    """
    
    STATUS_CHOICES = [
        ('ativa', 'Apenas Ativas'),
        ('inativa', 'Apenas Inativas'),
        ('todos', 'Todas'),
    ]
    
    PAGA_POR_CHOICES = [
        ('todos', 'Todos'),
        ('proprietario', 'Proprietário'),
        ('inquilino', 'Inquilino'),
        ('imobiliaria', 'Imobiliária'),
    ]
    
    # NOVO: Filtro de Taxa Admin
    INCIDENCIA_TAXA_CHOICES = [
        ('todas', 'Todas'),
        ('com_taxa', 'Com Taxa'),
        ('sem_taxa', 'Sem Taxa'),
        ('parcial', 'Taxa Parcial'),
    ]
    
    PERIODO_CHOICES = [
        ('todas', 'Todas as Despesas'),
        ('periodo', 'Apenas Período Atual'),
    ]
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        initial='ativa',
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500',
            'onchange': 'this.form.submit();'
        }),
        label='Status'
    )
    
    paga_por = forms.ChoiceField(
        choices=PAGA_POR_CHOICES,
        initial='todos',
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500',
            'onchange': 'this.form.submit();'
        }),
        label='Paga Por'
    )
    
    # NOVO: Filtro Taxa Admin
    incidencia_taxa = forms.ChoiceField(
        choices=INCIDENCIA_TAXA_CHOICES,
        initial='todas',
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500',
            'onchange': 'this.form.submit();'
        }),
        label='Taxa Admin'
    )
    
    periodo_filtro = forms.ChoiceField(
        choices=PERIODO_CHOICES,
        initial='todas',
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500',
            'onchange': 'this.form.submit();'
        }),
        label='Período'
    )
    
    tipo = forms.ModelChoiceField(
        queryset=TipoDespesa.objects.filter(ativo=True).order_by('categoria', 'nome'),
        required=False,
        empty_label="Todos os tipos",
        widget=forms.Select(attrs={
            'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500',
            'onchange': 'this.form.submit();'
        }),
        label='Tipo'
    )
    
    busca = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500',
            'placeholder': 'Buscar por descrição...',
            'autocomplete': 'off'
        }),
        label='Buscar'
    )