# financeiro/forms/cobranca_forms.py
"""
Formulários para Cobranças - Refatorados
========================================
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
            'valor_aluguel', 'data_vencimento', 'descricao', 'observacoes'
        ]
        
        labels = {
            'contrato': 'Contrato',
            'mes_referencia': 'Mês de Referência',
            'ano_referencia': 'Ano de Referência',
            'valor_aluguel': 'Valor do Aluguel (R$)',
            'data_vencimento': 'Data de Vencimento',
            'descricao': 'Descrição da Cobrança',
            'observacoes': 'Observações Internas'
        }
        
        help_texts = {
            'contrato': 'Selecione o contrato para esta cobrança',
            'mes_referencia': 'Mês ao qual se refere esta cobrança',
            'ano_referencia': 'Ano de referência da cobrança',
            'valor_aluguel': 'Valor base do aluguel do contrato',
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
        
        # Campos monetários
        if 'valor_aluguel' in self.fields:
            self.fields['valor_aluguel'].widget.attrs.update({
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
                from sisimob.models import Contrato
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
    
    def clean_valor_aluguel(self):
        """Validação específica do valor do aluguel"""
        valor = self.cleaned_data.get('valor_aluguel')
        if valor is not None and valor <= 0:
            raise ValidationError('Valor do aluguel deve ser maior que zero.')
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
    incluir_despesas = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': CobrancaBaseForm.CSS_CLASSES['checkbox']
        }),
        label='Incluir Despesas do Contrato',
        help_text='Incluir automaticamente as despesas ativas do contrato no valor total'
    )
    
    despesas_selecionadas = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
        help_text='IDs das despesas selecionadas (separadas por vírgula)'
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
    
    class Meta(CobrancaBaseForm.Meta):
        fields = CobrancaBaseForm.Meta.fields + ['valor_total']
        
        labels = dict(CobrancaBaseForm.Meta.labels, **{
            'valor_total': 'Valor Total (R$)'
        })
        
        help_texts = dict(CobrancaBaseForm.Meta.help_texts, **{
            'valor_total': 'Valor total incluindo aluguel e despesas (calculado automaticamente)'
        })
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Configurar valor total como readonly
        if 'valor_total' in self.fields:
            self.fields['valor_total'].widget.attrs.update({
                'class': self.CSS_CLASSES['readonly'],
                'readonly': True,
                'placeholder': 'Calculado automaticamente'
            })
    
    def clean(self):
        """Validação geral do formulário de criação"""
        cleaned_data = super().clean()
        
        # Verificar duplicata
        self._verificar_duplicata()
        
        # Calcular valor total se incluir despesas
        contrato = cleaned_data.get('contrato')
        incluir_despesas = cleaned_data.get('incluir_despesas', False)
        valor_aluguel = cleaned_data.get('valor_aluguel', Decimal('0.00'))
        
        if contrato and incluir_despesas:
            from financeiro.services.cobranca.cobranca_calculadora_service import CobrancaCalculadoraService
            
            # Buscar despesas do contrato
            mes = cleaned_data.get('mes_referencia')
            ano = cleaned_data.get('ano_referencia')
            
            if mes and ano:
                despesas = CobrancaCalculadoraService.buscar_despesas_periodo(contrato, mes, ano)
                valor_despesas = CobrancaCalculadoraService.calcular_valor_despesas(despesas)
                valor_total = valor_aluguel + valor_despesas
                cleaned_data['valor_total'] = valor_total
            else:
                cleaned_data['valor_total'] = valor_aluguel
        else:
            cleaned_data['valor_total'] = valor_aluguel
        
        # Pré-carregar valor do aluguel do contrato se não informado
        if contrato and not valor_aluguel:
            valor_contrato = getattr(contrato, 'valor_aluguel', None) or getattr(contrato, 'valor_base', None)
            if valor_contrato:
                cleaned_data['valor_aluguel'] = valor_contrato
        
        return cleaned_data
    
    def save(self, commit=True):
        """Save customizado para criação"""
        cobranca = super().save(commit=False)
        
        # Garantir que valor_total está definido
        if not cobranca.valor_total:
            cobranca.valor_total = cobranca.valor_aluguel or Decimal('0.00')
        
        # Gerar descrição automática se solicitado
        if self.cleaned_data.get('gerar_descricao_automatica', True):
            from ..services.cobranca_descricao_service import CobrancaDescricaoService
            
            # Criar objeto temporário para gerar descrição
            temp_cobranca = Cobranca(
                contrato=cobranca.contrato,
                mes_referencia=cobranca.mes_referencia,
                ano_referencia=cobranca.ano_referencia,
                valor_aluguel=cobranca.valor_aluguel,
                valor_total=cobranca.valor_total
            )
            
            cobranca.descricao = CobrancaDescricaoService.gerar_descricao_completa(temp_cobranca)
        
        if commit:
            cobranca.save()
            
            # Atualizar valor total incluindo despesas após salvar
            if self.cleaned_data.get('incluir_despesas', False):
                cobranca.atualizar_valor_total()
        
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
        fields = CobrancaBaseForm.Meta.fields + ['valor_total', 'status']
        
        labels = dict(CobrancaBaseForm.Meta.labels, **{
            'valor_total': 'Valor Total (R$)',
            'status': 'Status da Cobrança'
        })
        
        help_texts = dict(CobrancaBaseForm.Meta.help_texts, **{
            'valor_total': 'Valor total da cobrança',
            'status': 'Status atual da cobrança'
        })
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Configurar campos baseado no status atual
        if self.instance.pk:
            self._configurar_campos_por_status()
    
    def _configurar_campos_por_status(self):
        """Configura campos baseado no status da cobrança"""
        
        # Se já foi integrada com Asaas, limitar edições
        if hasattr(self.instance, 'asaas_integracao') and self.instance.asaas_integracao.asaas_id:
            # Campos que não podem ser alterados após integração
            campos_readonly = ['valor_aluguel', 'valor_total', 'data_vencimento']
            
            for campo in campos_readonly:
                if campo in self.fields:
                    self.fields[campo].widget.attrs.update({
                        'class': self.CSS_CLASSES['readonly'],
                        'readonly': True
                    })
                    self.fields[campo].help_text += " (Não pode ser alterado - cobrança já integrada)"
        
        # Se já foi paga, bloquear alterações críticas
        if self.instance.status == 'paga':
            campos_readonly = ['valor_aluguel', 'valor_total', 'contrato', 'mes_referencia', 'ano_referencia']
            
            for campo in campos_readonly:
                if campo in self.fields:
                    self.fields[campo].widget.attrs.update({
                        'class': self.CSS_CLASSES['readonly'],
                        'readonly': True
                    })
                    self.fields[campo].help_text += " (Não pode ser alterado - cobrança já foi paga)"
    
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
            campos_criticos = ['valor_total', 'contrato']
            for campo in campos_criticos:
                if campo in cleaned_data and cleaned_data[campo] != getattr(self.instance, campo):
                    raise ValidationError(f'Não é possível alterar {campo} de uma cobrança já paga.')
        
        return cleaned_data
    
    def save(self, commit=True):
        """Save customizado para edição"""
        cobranca = super().save(commit=False)
        
        # Recalcular valores se solicitado
        if self.cleaned_data.get('recalcular_valores', False):
            from financeiro.services.cobranca.cobranca_calculadora_service import CobrancaCalculadoraService
            
            despesas = CobrancaCalculadoraService.buscar_despesas_periodo(
                cobranca.contrato, cobranca.mes_referencia, cobranca.ano_referencia
            )
            valor_despesas = CobrancaCalculadoraService.calcular_valor_despesas(despesas)
            cobranca.valor_total = cobranca.valor_aluguel + valor_despesas
        
        # Atualizar descrição se solicitado
        if self.cleaned_data.get('atualizar_descricao', False):
            from ..services.cobranca_descricao_service import CobrancaDescricaoService
            cobranca.descricao = CobrancaDescricaoService.gerar_descricao_completa(cobranca)
        
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