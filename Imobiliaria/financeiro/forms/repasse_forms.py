# financeiro/forms/repasse_forms.py
from django import forms
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import date
from ..models.repasse import Repasse, PoliticaRepasseContrato, PoliticaRepasseGlobal
from sisimob.models import Contrato, Cliente

try:
    from ..models.cobranca import Cobranca
except ImportError:
    Cobranca = None


class RepasseForm(forms.ModelForm):
    """Form para criar/editar repasses"""
    
    class Meta:
        model = Repasse
        fields = [
            'proprietario', 'contrato', 'cobranca', 'valor', 'valor_desconto', 
            'valor_taxa_admin', 'data_prevista', 'mes_referencia', 'ano_referencia',
            'tipo', 'metodo_pagamento', 'descricao', 'observacoes'
        ]
        widgets = {
            'proprietario': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md bg-gray-700 border-gray-600 text-white shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
            }),
            'contrato': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md bg-gray-700 border-gray-600 text-white shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
            }),
            'cobranca': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md bg-gray-700 border-gray-600 text-white shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
            }),
            'valor': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md bg-gray-700 border-gray-600 text-white placeholder-gray-400 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm',
                'step': '0.01',
                'min': '0'
            }),
            'valor_desconto': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md bg-gray-700 border-gray-600 text-white placeholder-gray-400 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm',
                'step': '0.01',
                'min': '0'
            }),
            'valor_taxa_admin': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md bg-gray-700 border-gray-600 text-white placeholder-gray-400 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm',
                'step': '0.01',
                'min': '0'
            }),
            'data_prevista': forms.DateInput(attrs={
                'class': 'mt-1 block w-full rounded-md bg-gray-700 border-gray-600 text-white placeholder-gray-400 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm',
                'type': 'date'
            }),
            'mes_referencia': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md bg-gray-700 border-gray-600 text-white shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
            }),
            'ano_referencia': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md bg-gray-700 border-gray-600 text-white placeholder-gray-400 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm',
                'min': '2020',
                'max': '2030'
            }),
            'tipo': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md bg-gray-700 border-gray-600 text-white shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
            }),
            'metodo_pagamento': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md bg-gray-700 border-gray-600 text-white shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
            }),
            'descricao': forms.Textarea(attrs={
                'class': 'mt-1 block w-full rounded-md bg-gray-700 border-gray-600 text-white placeholder-gray-400 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm',
                'rows': 3
            }),
            'observacoes': forms.Textarea(attrs={
                'class': 'mt-1 block w-full rounded-md bg-gray-700 border-gray-600 text-white placeholder-gray-400 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm',
                'rows': 3
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Configurar choices para mês
        self.fields['mes_referencia'].choices = [
            ('', 'Selecione o mês')
        ] + [(i, f'{i:02d} - {mes}') for i, mes in enumerate([
            '', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
            'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
        ], 0) if i > 0]
        
        # Filtrar proprietários
        self.fields['proprietario'].queryset = Cliente.objects.filter(
            tipo='proprietario'
        ).order_by('nome')
        
        # Filtrar contratos ativos
        self.fields['contrato'].queryset = Contrato.objects.filter(
            ativo=True
        ).select_related('proprietario', 'imovel').order_by(
            'proprietario__nome', 'imovel__endereco'
        )
        
        # Configurar cobrança se disponível
        if Cobranca:
            self.fields['cobranca'].queryset = Cobranca.objects.filter(
                status='paga'
            ).select_related('contrato').order_by('-data_pagamento')
            self.fields['cobranca'].required = False
        else:
            self.fields['cobranca'].widget = forms.HiddenInput()
        
        # Valores padrão
        if not self.instance.pk:
            self.fields['ano_referencia'].initial = date.today().year
            self.fields['mes_referencia'].initial = date.today().month
            self.fields['data_prevista'].initial = date.today()
            self.fields['valor_desconto'].initial = Decimal('0.00')
            self.fields['valor_taxa_admin'].initial = Decimal('0.00')
    
    def clean(self):
        cleaned_data = super().clean()
        valor = cleaned_data.get('valor', Decimal('0'))
        valor_desconto = cleaned_data.get('valor_desconto', Decimal('0'))
        valor_taxa_admin = cleaned_data.get('valor_taxa_admin', Decimal('0'))
        
        # Validar que descontos não excedem o valor
        if valor_desconto + valor_taxa_admin >= valor:
            raise ValidationError('A soma dos descontos não pode ser maior ou igual ao valor bruto.')
        
        # Validar que o valor líquido é positivo
        valor_liquido = valor - valor_desconto - valor_taxa_admin
        if valor_liquido <= 0:
            raise ValidationError('O valor líquido deve ser maior que zero.')
        
        return cleaned_data


class PoliticaRepasseContratoForm(forms.ModelForm):
    """Form para políticas específicas por contrato"""
    
    class Meta:
        model = PoliticaRepasseContrato
        fields = [
            'contrato', 'ativa', 'periodicidade', 'tipo_dias', 'dia_mes', 'dia_semana',
            'dias_apos_recebimento', 'percentual_adiantamento', 'taxa_adiantamento',
            'valor_minimo_repasse', 'taxa_admin_personalizada', 'considerar_feriados',
            'antecipar_fds_feriados', 'observacoes'
        ]
        widgets = {
            'contrato': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md bg-gray-700 border-gray-600 text-white shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
            }),
            'ativa': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-600 bg-gray-700 rounded'
            }),
            'periodicidade': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md bg-gray-700 border-gray-600 text-white shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
            }),
            'tipo_dias': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md bg-gray-700 border-gray-600 text-white shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
            }),
            'dia_mes': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md bg-gray-700 border-gray-600 text-white placeholder-gray-400 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm',
                'min': '1',
                'max': '31'
            }),
            'dia_semana': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md bg-gray-700 border-gray-600 text-white shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
            }),
            'dias_apos_recebimento': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md bg-gray-700 border-gray-600 text-white placeholder-gray-400 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm',
                'min': '0',
                'max': '30'
            }),
            'percentual_adiantamento': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md bg-gray-700 border-gray-600 text-white placeholder-gray-400 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm',
                'step': '0.01',
                'min': '0',
                'max': '100'
            }),
            'taxa_adiantamento': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md bg-gray-700 border-gray-600 text-white placeholder-gray-400 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm',
                'step': '0.01',
                'min': '0',
                'max': '100'
            }),
            'valor_minimo_repasse': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md bg-gray-700 border-gray-600 text-white placeholder-gray-400 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm',
                'step': '0.01',
                'min': '0'
            }),
            'taxa_admin_personalizada': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md bg-gray-700 border-gray-600 text-white placeholder-gray-400 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm',
                'step': '0.01',
                'min': '0',
                'max': '100'
            }),
            'considerar_feriados': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-600 bg-gray-700 rounded'
            }),
            'antecipar_fds_feriados': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-600 bg-gray-700 rounded'
            }),
            'observacoes': forms.Textarea(attrs={
                'class': 'mt-1 block w-full rounded-md bg-gray-700 border-gray-600 text-white placeholder-gray-400 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm',
                'rows': 3
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filtrar contratos disponíveis
        if not self.instance.pk:
            self.fields['contrato'].queryset = Contrato.objects.filter(
                ativo=True,
                politica_repasse__isnull=True
            ).select_related('proprietario', 'imovel').order_by(
                'proprietario__nome', 'imovel__endereco'
            )
        else:
            # Para edição, incluir o contrato atual
            self.fields['contrato'].queryset = Contrato.objects.filter(
                models.Q(id=self.instance.contrato.id) |
                models.Q(ativo=True, politica_repasse__isnull=True)
            ).select_related('proprietario', 'imovel').order_by(
                'proprietario__nome', 'imovel__endereco'
            )
        
        # Valores padrão
        if not self.instance.pk:
            self.fields['ativa'].initial = True
            self.fields['tipo_dias'].initial = 'uteis'
            self.fields['dias_apos_recebimento'].initial = 2
            self.fields['considerar_feriados'].initial = True
            self.fields['antecipar_fds_feriados'].initial = True
    
    def clean(self):
        cleaned_data = super().clean()
        periodicidade = cleaned_data.get('periodicidade')
        dia_mes = cleaned_data.get('dia_mes')
        dia_semana = cleaned_data.get('dia_semana')
        
        # Validar campos obrigatórios baseados na periodicidade
        if periodicidade == 'mensal' and not dia_mes:
            raise ValidationError('Para periodicidade mensal, o dia do mês é obrigatório.')
        
        if periodicidade == 'semanal' and not dia_semana:
            raise ValidationError('Para periodicidade semanal, o dia da semana é obrigatório.')
        
        # Validar dia do mês
        if dia_mes and (dia_mes < 1 or dia_mes > 31):
            raise ValidationError('Dia do mês deve estar entre 1 e 31.')
        
        return cleaned_data


class PoliticaRepasseGlobalForm(forms.ModelForm):
    """Form para políticas globais"""
    
    class Meta:
        model = PoliticaRepasseGlobal
        fields = [
            'nome', 'ativa', 'periodicidade', 'tipo_dias', 'dia_mes', 'dia_semana',
            'dias_apos_recebimento', 'percentual_adiantamento', 'taxa_adiantamento',
            'valor_minimo_repasse', 'taxa_admin_padrao', 'considerar_feriados',
            'antecipar_fds_feriados'
        ]
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md bg-gray-700 border-gray-600 text-white placeholder-gray-400 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
            }),
            'ativa': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-600 bg-gray-700 rounded'
            }),
            'periodicidade': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md bg-gray-700 border-gray-600 text-white shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
            }),
            'tipo_dias': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md bg-gray-700 border-gray-600 text-white shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
            }),
            'dia_mes': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md bg-gray-700 border-gray-600 text-white placeholder-gray-400 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm',
                'min': '1',
                'max': '31'
            }),
            'dia_semana': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md bg-gray-700 border-gray-600 text-white shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
            }),
            'dias_apos_recebimento': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md bg-gray-700 border-gray-600 text-white placeholder-gray-400 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm',
                'min': '0',
                'max': '30'
            }),
            'percentual_adiantamento': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md bg-gray-700 border-gray-600 text-white placeholder-gray-400 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm',
                'step': '0.01',
                'min': '0',
                'max': '100'
            }),
            'taxa_adiantamento': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md bg-gray-700 border-gray-600 text-white placeholder-gray-400 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm',
                'step': '0.01',
                'min': '0',
                'max': '100'
            }),
            'valor_minimo_repasse': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md bg-gray-700 border-gray-600 text-white placeholder-gray-400 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm',
                'step': '0.01',
                'min': '0'
            }),
            'taxa_admin_padrao': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md bg-gray-700 border-gray-600 text-white placeholder-gray-400 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm',
                'step': '0.01',
                'min': '0',
                'max': '100'
            }),
            'considerar_feriados': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-600 bg-gray-700 rounded'
            }),
            'antecipar_fds_feriados': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-600 bg-gray-700 rounded'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Valores padrão
        if not self.instance.pk:
            self.fields['ativa'].initial = True
            self.fields['tipo_dias'].initial = 'uteis'
            self.fields['dias_apos_recebimento'].initial = 2
            self.fields['taxa_admin_padrao'].initial = Decimal('8.00')
            self.fields['considerar_feriados'].initial = True
            self.fields['antecipar_fds_feriados'].initial = True


class ProcessarRepasseForm(forms.Form):
    """Form para processar um repasse"""
    
    metodo_pagamento = forms.ChoiceField(
        choices=Repasse.METODO_PAGAMENTO_CHOICES,
        widget=forms.Select(attrs={
            'class': 'mt-1 block w-full rounded-md bg-gray-700 border-gray-600 text-white shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
        }),
        required=True,
        label='Método de Pagamento'
    )
    
    comprovante = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'sr-only',
            'accept': '.pdf,.jpg,.jpeg,.png'
        }),
        required=False,
        label='Comprovante'
    )
    
    observacoes = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'mt-1 block w-full rounded-md bg-gray-700 border-gray-600 text-white placeholder-gray-400 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm',
            'rows': 3,
            'placeholder': 'Observações sobre o processamento...'
        }),
        required=False,
        label='Observações'
    )


class ConfiguracaoPoliticasForm(forms.Form):
    """Form para configurações globais do sistema"""
    
    taxa_admin_global = forms.DecimalField(
        max_digits=5,
        decimal_places=2,
        initial=Decimal('8.00'),
        widget=forms.NumberInput(attrs={
            'class': 'mt-1 block w-full rounded-md bg-gray-700 border-gray-600 text-white placeholder-gray-400 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm',
            'step': '0.01',
            'min': '0',
            'max': '100'
        }),
        label='Taxa de Administração Global (%)'
    )
    
    valor_minimo_global = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        initial=Decimal('0.00'),
        widget=forms.NumberInput(attrs={
            'class': 'mt-1 block w-full rounded-md bg-gray-700 border-gray-600 text-white placeholder-gray-400 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm',
            'step': '0.01',
            'min': '0'
        }),
        label='Valor Mínimo Global (R$)'
    )
    
    email_notificacoes = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'mt-1 block w-full rounded-md bg-gray-700 border-gray-600 text-white placeholder-gray-400 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
        }),
        required=False,
        label='E-mail para Notificações'
    )
    
    criar_automatico_na_cobranca = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={
            'class': 'h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-600 bg-gray-700 rounded'
        }),
        required=False,
        initial=True,
        label='Criar repasse automaticamente quando cobrança for paga'
    )
    
    dias_uteis_padrao = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={
            'class': 'h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-600 bg-gray-700 rounded'
        }),
        required=False,
        initial=True,
        label='Usar dias úteis como padrão para novas políticas'
    )
    
    considerar_feriados_padrao = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={
            'class': 'h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-600 bg-gray-700 rounded'
        }),
        required=False,
        initial=True,
        label='Considerar feriados por padrão'
    )


class FiltroContratosForm(forms.Form):
    """Form para filtrar contratos"""
    
    proprietario = forms.ModelChoiceField(
        queryset=Cliente.objects.filter(tipo='proprietario').order_by('nome'),
        widget=forms.Select(attrs={
            'class': 'mt-1 block w-full rounded-md bg-gray-700 border-gray-600 text-white shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
        }),
        required=False,
        empty_label='Todos os proprietários'
    )
    
    search = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'mt-1 block w-full rounded-md bg-gray-700 border-gray-600 text-white placeholder-gray-400 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm',
            'placeholder': 'Buscar por proprietário ou endereço...'
        }),
        required=False
    )