# financeiro/forms/cobranca_forms.py
"""
Formulários para Cobranças - Corrigidos para o novo modelo
=========================================================
"""

from django import forms
from django.core.exceptions import ValidationError
from datetime import date, timedelta
from decimal import Decimal

from ..models import Cobranca


class CobrancaBaseForm(forms.ModelForm):
    """
    Formulário base para cobranças com funcionalidades comuns
    """
    
    # CSS classes padrão
    CSS_CLASSES = {
        'default': 'w-full bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500',
        'currency': 'w-full bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg pl-12 pr-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500',
        'readonly': 'w-full bg-gray-100 dark:bg-gray-600 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg px-3 py-2 cursor-not-allowed',
        'textarea': 'w-full bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-vertical',
        'checkbox': 'w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 focus:ring-2'
    }
    
    class Meta:
        model = Cobranca
        fields = [
            'contrato', 'mes_referencia', 'ano_referencia',
            'valor', 'data_vencimento', 'descricao', 'observacoes'  # CORRIGIDO: valor em vez de valor_aluguel
        ]
        
        labels = {
            'contrato': 'Contrato',
            'mes_referencia': 'Mês de Referência',
            'ano_referencia': 'Ano de Referência',
            'valor': 'Valor da Cobrança (R$)',  # CORRIGIDO
            'data_vencimento': 'Data de Vencimento',
            'descricao': 'Descrição da Cobrança',
            'observacoes': 'Observações Internas'
        }
        
        help_texts = {
            'contrato': 'Selecione o contrato para esta cobrança',
            'mes_referencia': 'Mês ao qual se refere esta cobrança',
            'ano_referencia': 'Ano de referência da cobrança',
            'valor': 'Valor total da cobrança (aluguel + despesas)',  # CORRIGIDO
            'data_vencimento': 'Data limite para pagamento',
            'descricao': 'Descrição detalhada que aparecerá na cobrança',
            'observacoes': 'Observações internas (não aparecem na cobrança)'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._configurar_widgets()
        self._configurar_queryset_contrato()
        self._configurar_opcoes_mes()
        self._configurar_valores_padrao()
    
    def _configurar_widgets(self):
        """Aplica CSS classes padronizadas aos widgets"""
        
        # Widgets padrão
        for field_name in ['contrato', 'mes_referencia', 'ano_referencia']:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs.update({
                    'class': self.CSS_CLASSES['default']
                })
        
        # Campo monetário - CORRIGIDO para 'valor'
        if 'valor' in self.fields:
            self.fields['valor'].widget.attrs.update({
                'class': self.CSS_CLASSES['currency'],
                'step': '0.01',
                'min': '0',
                'placeholder': '0,00'
            })
        
        # Campo de data
        if 'data_vencimento' in self.fields:
            self.fields['data_vencimento'].widget.attrs.update({
                'class': self.CSS_CLASSES['default'],
                'type': 'date'
            })
        
        # Textareas
        for field_name in ['descricao', 'observacoes']:
            if field_name in self.fields:
                rows = 4 if field_name == 'descricao' else 3
                self.fields[field_name].widget.attrs.update({
                    'class': self.CSS_CLASSES['textarea'],
                    'rows': rows,
                    'placeholder': f'{self.fields[field_name].label}...'
                })
        
        # Ano com validação
        if 'ano_referencia' in self.fields:
            self.fields['ano_referencia'].widget.attrs.update({
                'min': '2020',
                'max': '2030'
            })
    
    def _configurar_queryset_contrato(self):
        """Configura queryset para contratos ativos"""
        if 'contrato' in self.fields:
            try:
                from core.models import Contrato
                self.fields['contrato'].queryset = Contrato.objects.filter(
                    ativo=True
                ).order_by('-data_inicio')
            except ImportError:
                pass
    
    def _configurar_opcoes_mes(self):
        """Configura opções do campo mês"""
        if 'mes_referencia' in self.fields:
            meses_choices = [
                (1, 'Janeiro'), (2, 'Fevereiro'), (3, 'Março'), (4, 'Abril'),
                (5, 'Maio'), (6, 'Junho'), (7, 'Julho'), (8, 'Agosto'),
                (9, 'Setembro'), (10, 'Outubro'), (11, 'Novembro'), (12, 'Dezembro')
            ]
            self.fields['mes_referencia'] = forms.ChoiceField(
                choices=meses_choices,
                widget=forms.Select(attrs=self.fields['mes_referencia'].widget.attrs),
                label=self.fields['mes_referencia'].label,
                help_text=self.fields['mes_referencia'].help_text
            )
    
    def _configurar_valores_padrao(self):
        """Define valores padrão para novos registros"""
        if not self.instance.pk:
            hoje = date.today()
            
            # Mês e ano atual
            if 'mes_referencia' in self.fields:
                self.fields['mes_referencia'].initial = hoje.month
            if 'ano_referencia' in self.fields:
                self.fields['ano_referencia'].initial = hoje.year
            
            # Data de vencimento padrão: dia 10 do próximo mês
            if 'data_vencimento' in self.fields:
                if hoje.month == 12:
                    vencimento = date(hoje.year + 1, 1, 10)
                else:
                    vencimento = date(hoje.year, hoje.month + 1, 10)
                self.fields['data_vencimento'].initial = vencimento
    
    def clean_mes_referencia(self):
        """Validação específica do mês"""
        mes = self.cleaned_data.get('mes_referencia')
        if mes:
            try:
                mes = int(mes)
                if not (1 <= mes <= 12):
                    raise ValidationError('Mês deve estar entre 1 e 12.')
            except (ValueError, TypeError):
                raise ValidationError('Mês inválido.')
        return mes
    
    def clean_ano_referencia(self):
        """Validação específica do ano"""
        ano = self.cleaned_data.get('ano_referencia')
        if ano:
            try:
                ano = int(ano)
                if not (2020 <= ano <= 2030):
                    raise ValidationError('Ano deve estar entre 2020 e 2030.')
            except (ValueError, TypeError):
                raise ValidationError('Ano inválido.')
        return ano
    
    def clean_valor(self):  # CORRIGIDO: clean_valor em vez de clean_valor_aluguel
        """Validação específica do valor"""
        valor = self.cleaned_data.get('valor')
        if valor is not None and valor <= 0:
            raise ValidationError('Valor da cobrança deve ser maior que zero.')
        return valor
    
    def clean_data_vencimento(self):
        """Validação específica da data de vencimento"""
        data = self.cleaned_data.get('data_vencimento')
        if data and data < date.today():
            raise ValidationError('Data de vencimento não pode ser anterior a hoje.')
        return data
    
    def _verificar_duplicata(self):
        """Verifica se já existe cobrança para o período"""
        contrato = self.cleaned_data.get('contrato')
        mes = self.cleaned_data.get('mes_referencia')
        ano = self.cleaned_data.get('ano_referencia')
        
        if contrato and mes and ano:
            queryset = Cobranca.objects.filter(
                contrato=contrato,
                mes_referencia=mes,
                ano_referencia=ano
            )
            
            if self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            
            if queryset.exists():
                raise ValidationError({
                    'mes_referencia': f'Já existe uma cobrança para {contrato} em {mes}/{ano}'
                })


class CobrancaCreateForm(CobrancaBaseForm):
    """
    Formulário específico para criação de cobranças
    """
    
    # Campos adicionais para criação
    calcular_automaticamente = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': CobrancaBaseForm.CSS_CLASSES['checkbox']
        }),
        label='Calcular Valor Automaticamente',
        help_text='Calcular valor baseado no contrato + despesas'
    )
    
    incluir_despesas = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': CobrancaBaseForm.CSS_CLASSES['checkbox']
        }),
        label='Incluir Despesas do Contrato',
        help_text='Incluir automaticamente as despesas ativas do contrato no valor total'
    )
    
    gerar_descricao_automatica = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': CobrancaBaseForm.CSS_CLASSES['checkbox']
        }),
        label='Gerar Descrição Automática',
        help_text='Gerar automaticamente a descrição com detalhes do aluguel e despesas'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Se calcular automaticamente, campo valor fica readonly
        if self.data.get('calcular_automaticamente', 'on') == 'on':
            self.fields['valor'].widget.attrs.update({
                'class': self.CSS_CLASSES['readonly'],
                'readonly': True,
                'placeholder': 'Será calculado automaticamente'
            })
    
    def clean(self):
        """Validação geral do formulário de criação"""
        cleaned_data = super().clean()
        
        # Verificar duplicata
        self._verificar_duplicata()
        
        # Se deve calcular automaticamente
        if cleaned_data.get('calcular_automaticamente', True):
            contrato = cleaned_data.get('contrato')
            if contrato:
                # Pegar valor base do contrato
                valor_base = getattr(contrato, 'valor_aluguel', None) or getattr(contrato, 'valor_base', Decimal('0.00'))
                
                # Calcular despesas se solicitado
                valor_despesas = Decimal('0.00')
                if cleaned_data.get('incluir_despesas', True):
                    try:
                        # Tentar usar service se existir
                        from ..services.cobranca.cobranca_calculadora_service import CobrancaCalculadoraService
                        mes = cleaned_data.get('mes_referencia')
                        ano = cleaned_data.get('ano_referencia')
                        if mes and ano:
                            valor_despesas = CobrancaCalculadoraService.calcular_despesas_periodo(
                                contrato, mes, ano
                            )
                    except ImportError:
                        # Service ainda não existe, usar valor zero
                        pass
                
                # Calcular valor total
                cleaned_data['valor'] = valor_base + valor_despesas
        
        return cleaned_data
    
    def save(self, commit=True):
        """Save customizado para criação"""
        cobranca = super().save(commit=False)
        
        # Garantir que valor está definido
        if not cobranca.valor:
            cobranca.valor = Decimal('0.00')
        
        # Poplar detalhes_calculo para transparência
        if self.cleaned_data.get('calcular_automaticamente', True):
            contrato = cobranca.contrato
            valor_base = getattr(contrato, 'valor_aluguel', None) or getattr(contrato, 'valor_base', Decimal('0.00'))
            valor_despesas = cobranca.valor - valor_base
            
            cobranca.detalhes_calculo = {
                'valor_base': float(valor_base),
                'valor_despesas': float(valor_despesas),
                'data_calculo': date.today().isoformat(),
                'metodo': 'automatico'
            }
        
        # Gerar descrição automática se solicitado
        if self.cleaned_data.get('gerar_descricao_automatica', True):
            cobranca.descricao = cobranca.gerar_descricao_automatica()
        
        if commit:
            cobranca.save()
        
        return cobranca


class CobrancaUpdateForm(CobrancaBaseForm):
    """
    Formulário específico para edição de cobranças
    """
    
    # Campo para recalcular valores
    recalcular_valores = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            'class': CobrancaBaseForm.CSS_CLASSES['checkbox']
        }),
        label='Recalcular Valores',
        help_text='Recalcular valor total baseado nas despesas atuais do contrato'
    )
    
    atualizar_descricao = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            'class': CobrancaBaseForm.CSS_CLASSES['checkbox']
        }),
        label='Atualizar Descrição',
        help_text='Regenerar descrição automática com dados atuais'
    )
    
    class Meta(CobrancaBaseForm.Meta):
        fields = CobrancaBaseForm.Meta.fields + ['status']
        
        labels = dict(CobrancaBaseForm.Meta.labels, **{
            'status': 'Status da Cobrança'
        })
        
        help_texts = dict(CobrancaBaseForm.Meta.help_texts, **{
            'status': 'Status atual da cobrança'
        })
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Configurar campos baseado no status atual
        if self.instance.pk:
            self._configurar_campos_por_status()
            self._mostrar_detalhes_calculo()
    
    def _configurar_campos_por_status(self):
        """Configura campos baseado no status da cobrança"""
        
        # Se já foi integrada com Asaas, limitar edições
        if hasattr(self.instance, 'asaas_integracao'):
            try:
                if self.instance.asaas_integracao and self.instance.asaas_integracao.asaas_id:
                    # Campos que não podem ser alterados após integração
                    campos_readonly = ['valor', 'data_vencimento']
                    
                    for campo in campos_readonly:
                        if campo in self.fields:
                            self.fields[campo].widget.attrs.update({
                                'class': self.CSS_CLASSES['readonly'],
                                'readonly': True
                            })
                            self.fields[campo].help_text += " (Não pode ser alterado - cobrança já integrada)"
            except:
                pass
        
        # Se já foi paga, bloquear alterações críticas
        if self.instance.status == 'paga':
            campos_readonly = ['valor', 'contrato', 'mes_referencia', 'ano_referencia']
            
            for campo in campos_readonly:
                if campo in self.fields:
                    self.fields[campo].widget.attrs.update({
                        'class': self.CSS_CLASSES['readonly'],
                        'readonly': True
                    })
                    self.fields[campo].help_text += " (Não pode ser alterado - cobrança já foi paga)"
    
    def _mostrar_detalhes_calculo(self):
        """Mostra detalhes do cálculo original"""
        if self.instance.detalhes_calculo:
            detalhes = self.instance.detalhes_calculo
            valor_base = detalhes.get('valor_base', 0)
            valor_despesas = detalhes.get('valor_despesas', 0)
            
            help_text = f"Cálculo original: Base R$ {valor_base:.2f} + Despesas R$ {valor_despesas:.2f}"
            self.fields['valor'].help_text = help_text
    
    def clean(self):
        """Validação geral do formulário de edição"""
        cleaned_data = super().clean()
        
        # Verificar duplicata apenas se período foi alterado
        periodo_alterado = (
            self.instance.mes_referencia != cleaned_data.get('mes_referencia') or
            self.instance.ano_referencia != cleaned_data.get('ano_referencia') or
            self.instance.contrato != cleaned_data.get('contrato')
        )
        
        if periodo_alterado:
            self._verificar_duplicata()
        
        # Validações específicas por status
        if self.instance.status == 'paga':
            campos_criticos = ['valor', 'contrato']
            for campo in campos_criticos:
                if campo in cleaned_data and cleaned_data[campo] != getattr(self.instance, campo):
                    raise ValidationError(f'Não é possível alterar {campo} de uma cobrança já paga.')
        
        return cleaned_data
    
    def save(self, commit=True):
        """Save customizado para edição"""
        cobranca = super().save(commit=False)
        
        # Recalcular valores se solicitado
        if self.cleaned_data.get('recalcular_valores', False):
            cobranca.recalcular_valor_total()
        
        # Atualizar descrição se solicitado
        if self.cleaned_data.get('atualizar_descricao', False):
            cobranca.descricao = cobranca.gerar_descricao_automatica()
        
        if commit:
            cobranca.save()
        
        return cobranca


class CobrancaFiltroForm(forms.Form):
    """
    Formulário simplificado para filtros na listagem
    """
    
    STATUS_CHOICES = [
        ('todos', 'Todos'),
        ('pendente', 'Pendentes'),
        ('paga', 'Pagas'),
        ('atrasada', 'Atrasadas'),
        ('cancelada', 'Canceladas'),
    ]
    
    MES_CHOICES = [('', 'Todos os meses')] + [
        (i, f'{i:02d}') for i in range(1, 13)
    ]
    
    CSS_CLASS = 'w-full bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500'
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        initial='pendente',
        required=False,
        widget=forms.Select(attrs={
            'class': CSS_CLASS,
            'onchange': 'this.form.submit();'
        }),
        label='Status'
    )
    
    mes_referencia = forms.ChoiceField(
        choices=MES_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': CSS_CLASS,
            'onchange': 'this.form.submit();'
        }),
        label='Mês'
    )
    
    ano_referencia = forms.CharField(
        max_length=4,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': CSS_CLASS,
            'placeholder': 'Ano...',
            'min': '2020',
            'max': '2030'
        }),
        label='Ano'
    )
    
    contrato = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': CSS_CLASS,
            'placeholder': 'Buscar por contrato...'
        }),
        label='Contrato'
    )
    
    inquilino = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': CSS_CLASS,
            'placeholder': 'Buscar por inquilino...'
        }),
        label='Inquilino'
    )


class CobrancaIntegracaoAsaasForm(forms.Form):
    """
    Formulário para configurações de integração com Asaas
    """
    
    FORMAS_PAGAMENTO_CHOICES = [
        ('BOLETO', 'Boleto Bancário'),
        ('PIX', 'PIX'),
        ('CREDIT_CARD', 'Cartão de Crédito'),
        ('DEBIT_CARD', 'Cartão de Débito'),
    ]
    
    CSS_CHECKBOX = 'form-checkbox text-blue-600 bg-gray-100 dark:bg-gray-700 border-gray-300 dark:border-gray-600 rounded focus:ring-blue-500'
    CSS_TEXTAREA = 'w-full bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500'
    
    formas_pagamento = forms.MultipleChoiceField(
        choices=FORMAS_PAGAMENTO_CHOICES,
        initial=['BOLETO', 'PIX'],
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': CSS_CHECKBOX
        }),
        label='Formas de Pagamento',
        help_text='Selecione as formas de pagamento disponíveis para esta cobrança'
    )
    
    enviar_por_email = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'w-4 h-4 text-blue-600 bg-gray-100 dark:bg-gray-700 border-gray-300 dark:border-gray-600 rounded focus:ring-blue-500 focus:ring-2'
        }),
        label='Enviar por E-mail',
        help_text='Enviar cobrança automaticamente por e-mail'
    )
    
    enviar_por_whatsapp = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'w-4 h-4 text-blue-600 bg-gray-100 dark:bg-gray-700 border-gray-300 dark:border-gray-600 rounded focus:ring-blue-500 focus:ring-2'
        }),
        label='Enviar por WhatsApp',
        help_text='Enviar cobrança automaticamente por WhatsApp'
    )
    
    observacoes_cobranca = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': CSS_TEXTAREA,
            'rows': 3,
            'placeholder': 'Observações que aparecerão na cobrança...'
        }),
        label='Observações da Cobrança',
        help_text='Texto adicional que aparecerá na cobrança enviada ao cliente'
    )
    
    def clean_formas_pagamento(self):
        """Validação das formas de pagamento"""
        formas = self.cleaned_data.get('formas_pagamento')
        if not formas:
            raise ValidationError('Selecione pelo menos uma forma de pagamento.')
        return formas


class CobrancaMarcarPagaForm(forms.Form):
    """
    Formulário para marcar cobrança como paga
    """
    
    data_pagamento = forms.DateField(
        label='Data do Pagamento',
        initial=date.today,
        widget=forms.DateInput(attrs={
            'class': 'w-full bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500',
            'type': 'date'
        }),
        help_text='Data em que o pagamento foi recebido'
    )
    
    observacoes_pagamento = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'w-full bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500',
            'rows': 3,
            'placeholder': 'Observações sobre o pagamento (opcional)...'
        }),
        label='Observações do Pagamento',
        help_text='Informações adicionais sobre como o pagamento foi recebido'
    )
    
    def clean_data_pagamento(self):
        """Validação da data de pagamento"""
        data = self.cleaned_data.get('data_pagamento')
        if data and data > date.today():
            raise ValidationError('Data de pagamento não pode ser futura.')
        return data


class CobrancaLoteForm(forms.Form):
    """
    Formulário para operações em lote
    """
    
    MES_CHOICES = [
        (1, 'Janeiro'), (2, 'Fevereiro'), (3, 'Março'), (4, 'Abril'),
        (5, 'Maio'), (6, 'Junho'), (7, 'Julho'), (8, 'Agosto'),
        (9, 'Setembro'), (10, 'Outubro'), (11, 'Novembro'), (12, 'Dezembro')
    ]
    
    CSS_CLASS = 'w-full bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500'
    CSS_CHECKBOX = 'w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500'
    
    mes_referencia = forms.ChoiceField(
        choices=MES_CHOICES,
        widget=forms.Select(attrs={'class': CSS_CLASS}),
        label='Mês de Referência'
    )
    
    ano_referencia = forms.IntegerField(
        min_value=2020,
        max_value=2030,
        initial=date.today().year,
        widget=forms.NumberInput(attrs={'class': CSS_CLASS}),
        label='Ano de Referência'
    )
    
    data_vencimento = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': CSS_CLASS,
            'type': 'date'
        }),
        label='Data de Vencimento'
    )
    
    incluir_despesas_automatico = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': CSS_CHECKBOX}),
        label='Incluir despesas automaticamente'
    )
    
    gerar_descricao_automatica = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': CSS_CHECKBOX}),
        label='Gerar descrição automaticamente'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Data de vencimento padrão: dia 10 do próximo mês
        hoje = date.today()
        if hoje.month == 12:
            vencimento_padrao = date(hoje.year + 1, 1, 10)
        else:
            vencimento_padrao = date(hoje.year, hoje.month + 1, 10)
        
        self.fields['data_vencimento'].initial = vencimento_padrao
        self.fields['mes_referencia'].initial = hoje.month
    
    def clean_data_vencimento(self):
        """Validação da data de vencimento"""
        data = self.cleaned_data.get('data_vencimento')
        if data and data < date.today():
            raise ValidationError('Data de vencimento não pode ser anterior a hoje.')
        return data


class CobrancaPreviewForm(forms.Form):
    """
    Formulário para configuração do preview de cobranças em lote
    """
    
    MES_CHOICES = [
        (1, 'Janeiro'), (2, 'Fevereiro'), (3, 'Março'), (4, 'Abril'),
        (5, 'Maio'), (6, 'Junho'), (7, 'Julho'), (8, 'Agosto'),
        (9, 'Setembro'), (10, 'Outubro'), (11, 'Novembro'), (12, 'Dezembro')
    ]
    
    CSS_CLASS = 'w-full bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-sm'
    CSS_CHECKBOX = 'w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 focus:ring-2'
    
    mes_referencia = forms.ChoiceField(
        choices=MES_CHOICES,
        widget=forms.Select(attrs={'class': CSS_CLASS}),
        label='Mês de Referência'
    )
    
    ano_referencia = forms.IntegerField(
        min_value=2020,
        max_value=2030,
        initial=date.today().year,
        widget=forms.NumberInput(attrs={'class': CSS_CLASS}),
        label='Ano de Referência'
    )
    
    data_vencimento = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': CSS_CLASS,
            'type': 'date'
        }),
        label='Data de Vencimento'
    )
    
    filtro_contratos = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
        help_text='IDs dos contratos selecionados (separados por vírgula)'
    )
    
    incluir_despesas = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': CSS_CHECKBOX}),
        label='Incluir despesas automaticamente',
        help_text='Incluir despesas rateadas no cálculo'
    )
    
    gerar_descricao_automatica = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': CSS_CHECKBOX}),
        label='Gerar descrição automaticamente',
        help_text='Gerar descrição automática baseada nos valores'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Valores padrão
        hoje = date.today()
        self.fields['mes_referencia'].initial = hoje.month
        
        # Data de vencimento padrão: dia 10 do próximo mês
        if hoje.month == 12:
            vencimento_padrao = date(hoje.year + 1, 1, 10)
        else:
            vencimento_padrao = date(hoje.year, hoje.month + 1, 10)
        
        self.fields['data_vencimento'].initial = vencimento_padrao
    
    def clean_data_vencimento(self):
        """Validação da data de vencimento"""
        data = self.cleaned_data.get('data_vencimento')
        if data and data < date.today():
            raise ValidationError('Data de vencimento não pode ser anterior a hoje.')
        return data


class CobrancaAcaoMassaForm(forms.Form):
    """
    Formulário para ações em massa nas cobranças
    """
    
    ACAO_CHOICES = [
        ('', 'Selecione uma ação...'),
        ('marcar_paga', 'Marcar como Paga'),
        ('enviar_lembrete', 'Enviar Lembrete'),
        ('cancelar', 'Cancelar'),
        ('reenviar_email', 'Reenviar por Email'),
        ('exportar_pdf', 'Exportar PDF'),
        ('integrar_asaas', 'Integrar com Asaas'),
    ]
    
    CSS_CLASS = 'w-full bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500'
    
    acao = forms.ChoiceField(
        choices=ACAO_CHOICES,
        widget=forms.Select(attrs={'class': CSS_CLASS}),
        label='Ação'
    )
    
    cobrancas_ids = forms.CharField(
        widget=forms.HiddenInput(),
        help_text='IDs das cobranças selecionadas'
    )
    
    data_pagamento = forms.DateField(
        required=False,
        initial=date.today,
        widget=forms.DateInput(attrs={
            'class': CSS_CLASS,
            'type': 'date'
        }),
        label='Data do Pagamento',
        help_text='Para ação "Marcar como Paga"'
    )
    
    motivo = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': CSS_CLASS,
            'rows': 3,
            'placeholder': 'Motivo da ação...'
        }),
        label='Motivo/Observações',
        help_text='Para ações como cancelamento'
    )
    
    def clean(self):
        """Validação geral do formulário"""
        cleaned_data = super().clean()
        acao = cleaned_data.get('acao')
        
        # Validações específicas por ação
        if acao == 'marcar_paga' and not cleaned_data.get('data_pagamento'):
            cleaned_data['data_pagamento'] = date.today()
            
        if acao == 'cancelar' and not cleaned_data.get('motivo'):
            raise ValidationError({'motivo': 'Motivo é obrigatório para cancelamento'})
        
        # Validar se há cobranças selecionadas
        cobrancas_ids = cleaned_data.get('cobrancas_ids', '')
        if not cobrancas_ids.strip():
            raise ValidationError({'cobrancas_ids': 'Selecione pelo menos uma cobrança'})
        
        return cleaned_data
    
    def clean_data_pagamento(self):
        """Validação da data de pagamento"""
        data = self.cleaned_data.get('data_pagamento')
        if data and data > date.today():
            raise ValidationError('Data de pagamento não pode ser futura.')
        return data


class CobrancaBuscaForm(forms.Form):
    """
    Formulário avançado para busca de cobranças
    """
    
    CSS_CLASS = 'w-full bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500'
    
    termo_busca = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': CSS_CLASS,
            'placeholder': 'Buscar por número da cobrança, contrato, inquilino...'
        }),
        label='Busca Geral'
    )
    
    valor_min = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': CSS_CLASS,
            'step': '0.01',
            'placeholder': '0,00'
        }),
        label='Valor Mínimo'
    )
    
    valor_max = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': CSS_CLASS,
            'step': '0.01',
            'placeholder': '0,00'
        }),
        label='Valor Máximo'
    )
    
    data_vencimento_inicio = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': CSS_CLASS,
            'type': 'date'
        }),
        label='Vencimento de'
    )
    
    data_vencimento_fim = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': CSS_CLASS,
            'type': 'date'
        }),
        label='Vencimento até'
    )
    
    apenas_atrasadas = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'w-4 h-4 text-red-600 bg-gray-100 border-gray-300 rounded focus:ring-red-500'
        }),
        label='Apenas Atrasadas'
    )
    
    apenas_integradas_asaas = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'w-4 h-4 text-green-600 bg-gray-100 border-gray-300 rounded focus:ring-green-500'
        }),
        label='Apenas Integradas com Asaas'
    )
    
    def clean(self):
        """Validação geral"""
        cleaned_data = super().clean()
        
        # Validar intervalo de valores
        valor_min = cleaned_data.get('valor_min')
        valor_max = cleaned_data.get('valor_max')
        
        if valor_min and valor_max and valor_min > valor_max:
            raise ValidationError({'valor_max': 'Valor máximo deve ser maior que o mínimo'})
        
        # Validar intervalo de datas
        data_inicio = cleaned_data.get('data_vencimento_inicio')
        data_fim = cleaned_data.get('data_vencimento_fim')
        
        if data_inicio and data_fim and data_inicio > data_fim:
            raise ValidationError({'data_vencimento_fim': 'Data final deve ser maior que a inicial'})
        
        return cleaned_data


# === VALIDATORS CUSTOMIZADOS ===

def validar_numero_cobranca(value):
    """Validator para formato do número da cobrança"""
    import re
    
    if not re.match(r'^COB\d{6}\d{4}$', value):
        raise ValidationError(
            'Número da cobrança deve ter o formato COB seguido de 10 dígitos (ex: COB2024100001)'
        )


def validar_valor_positivo(value):
    """Validator para garantir valor positivo"""
    if value <= 0:
        raise ValidationError('Valor deve ser maior que zero')


def validar_periodo_valido(mes, ano):
    """Validator para período válido"""
    try:
        import datetime
        datetime.date(ano, mes, 1)
    except ValueError:
        raise ValidationError('Período inválido')
    
    # Validar se não é muito antigo ou futuro
    hoje = date.today()
    limite_passado = date(hoje.year - 2, 1, 1)
    limite_futuro = date(hoje.year + 1, 12, 31)
    
    periodo = date(ano, mes, 1)
    
    if periodo < limite_passado:
        raise ValidationError('Período muito antigo')
    if periodo > limite_futuro:
        raise ValidationError('Período muito distante no futuro')


# === HELPERS PARA WIDGETS ===

class CurrencyWidget(forms.NumberInput):
    """Widget customizado para campos monetários"""
    
    def __init__(self, attrs=None):
        default_attrs = {
            'class': 'w-full bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg pl-12 pr-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500',
            'step': '0.01',
            'min': '0',
            'placeholder': '0,00'
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)
    
    def format_value(self, value):
        """Formata valor para exibição"""
        if value is None or value == '':
            return ''
        try:
            return f"{float(value):.2f}".replace('.', ',')
        except (ValueError, TypeError):
            return value


class DatePickerWidget(forms.DateInput):
    """Widget customizado para datas"""
    
    def __init__(self, attrs=None):
        default_attrs = {
            'class': 'w-full bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500',
            'type': 'date'
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)


class SelectWidget(forms.Select):
    """Widget customizado para selects"""
    
    def __init__(self, attrs=None):
        default_attrs = {
            'class': 'w-full bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500'
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)