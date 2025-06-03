# financeiro/forms/lembrete_forms.py
from django import forms
from django.core.exceptions import ValidationError
from financeiro.models.lembrete import LembreteEnviado
from financeiro.models.cobranca import Cobranca


class ConfiguracaoLembreteForm(forms.Form):
    """Formulário para configuração de lembretes automáticos"""
    
    # Configurações gerais
    lembretes_ativos = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500'
        }),
        label='Ativar lembretes automáticos'
    )
    
    # Configurações de timing
    dias_lembrete_1 = forms.IntegerField(
        initial=10,
        min_value=1,
        max_value=30,
        widget=forms.NumberInput(attrs={
            'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500',
            'placeholder': '10'
        }),
        label='Primeiro lembrete (dias antes do vencimento)',
        help_text='Número de dias antes do vencimento para enviar o primeiro lembrete'
    )
    
    dias_lembrete_2 = forms.IntegerField(
        initial=3,
        min_value=1,
        max_value=30,
        widget=forms.NumberInput(attrs={
            'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500',
            'placeholder': '3'
        }),
        label='Segundo lembrete (dias antes do vencimento)',
        help_text='Número de dias antes do vencimento para enviar o segundo lembrete'
    )
    
    dias_lembrete_3 = forms.IntegerField(
        initial=0,
        min_value=0,
        max_value=30,
        widget=forms.NumberInput(attrs={
            'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500',
            'placeholder': '0'
        }),
        label='Terceiro lembrete (dias antes/no vencimento)',
        help_text='0 = no dia do vencimento, valores positivos = dias antes'
    )
    
    # Canais de envio
    canais_ativos = forms.MultipleChoiceField(
        choices=LembreteEnviado.CANAIS,
        initial=['whatsapp'],
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'space-y-2'
        }),
        label='Canais de envio ativos'
    )
    
    # Templates de mensagem
    template_whatsapp = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500',
            'rows': 6,
            'placeholder': 'Olá {nome_inquilino}, seu aluguel de {mes_referencia} vence em {dias_vencimento} dias...'
        }),
        label='Template WhatsApp',
        help_text='Variáveis disponíveis: {nome_inquilino}, {mes_referencia}, {dias_vencimento}, {valor_total}, {data_vencimento}',
        initial='''Olá {nome_inquilino}! 

Lembramos que seu aluguel referente a {mes_referencia} vence em {dias_vencimento} dias ({data_vencimento}).

Valor: R$ {valor_total}

Para pagamento via PIX ou boleto, acesse: {link_pagamento}

Qualquer dúvida, estamos à disposição!'''
    )
    
    template_email = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500',
            'rows': 6,
            'placeholder': 'Assunto: Lembrete de Vencimento...'
        }),
        label='Template Email',
        required=False,
        help_text='Template do email de lembrete'
    )
    
    template_sms = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500',
            'rows': 3,
            'placeholder': 'SMS: Aluguel vence em {dias_vencimento} dias...'
        }),
        label='Template SMS',
        required=False,
        help_text='Template do SMS (máximo 160 caracteres)',
        max_length=160
    )
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validar ordem dos lembretes
        dias_1 = cleaned_data.get('dias_lembrete_1')
        dias_2 = cleaned_data.get('dias_lembrete_2')
        dias_3 = cleaned_data.get('dias_lembrete_3')
        
        if dias_1 and dias_2 and dias_1 <= dias_2:
            raise ValidationError('O primeiro lembrete deve ser enviado antes do segundo.')
        
        if dias_2 and dias_3 and dias_2 <= dias_3:
            raise ValidationError('O segundo lembrete deve ser enviado antes do terceiro.')
        
        # Validar templates dos canais ativos
        canais_ativos = cleaned_data.get('canais_ativos', [])
        
        if 'whatsapp' in canais_ativos and not cleaned_data.get('template_whatsapp'):
            raise ValidationError('Template do WhatsApp é obrigatório quando o canal está ativo.')
        
        if 'email' in canais_ativos and not cleaned_data.get('template_email'):
            raise ValidationError('Template do Email é obrigatório quando o canal está ativo.')
        
        if 'sms' in canais_ativos and not cleaned_data.get('template_sms'):
            raise ValidationError('Template do SMS é obrigatório quando o canal está ativo.')
        
        return cleaned_data


class EnvioManualForm(forms.Form):
    """Formulário para envio manual de lembretes"""
    
    cobrancas = forms.ModelMultipleChoiceField(
        queryset=Cobranca.objects.none(),  # Será definido no __init__
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'space-y-2'
        }),
        label='Cobranças para envio',
        help_text='Selecione as cobranças que devem receber o lembrete'
    )
    
    tipo = forms.ChoiceField(
        choices=LembreteEnviado.CANAIS,
        initial='whatsapp',
        widget=forms.RadioSelect(attrs={
            'class': 'space-y-2'
        }),
        label='Canal de envio'
    )
    
    template_personalizado = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500',
            'rows': 6,
            'placeholder': 'Deixe em branco para usar o template padrão ou digite uma mensagem personalizada...'
        }),
        required=False,
        label='Mensagem personalizada (opcional)',
        help_text='Se preenchido, esta mensagem será usada no lugar do template padrão'
    )
    
    enviar_imediatamente = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500'
        }),
        label='Enviar imediatamente',
        help_text='Se desmarcado, os lembretes serão agendados para envio posterior'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Carregar apenas cobranças pendentes ou atrasadas
        self.fields['cobrancas'].queryset = Cobranca.objects.filter(
            status__in=['pendente', 'atrasada']
        ).select_related('inquilino', 'contrato').order_by('data_vencimento')
    
    def clean_cobrancas(self):
        cobrancas = self.cleaned_data.get('cobrancas')
        
        if not cobrancas:
            raise ValidationError('Selecione pelo menos uma cobrança.')
        
        # Verificar se todas as cobranças têm inquilino com contato
        for cobranca in cobrancas:
            if not cobranca.inquilino:
                raise ValidationError(f'Cobrança {cobranca} não possui inquilino associado.')
            
            # Aqui você pode adicionar validações específicas por canal
            # Por exemplo, verificar se o inquilino tem WhatsApp, email, etc.
        
        return cobrancas


class FiltroLembretesForm(forms.Form):
    """Formulário para filtros da lista de lembretes"""
    
    tipo = forms.ChoiceField(
        choices=[('', 'Todos os tipos')] + LembreteEnviado.CANAIS,
        required=False,
        widget=forms.Select(attrs={
            'class': 'block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500'
        })
    )
    
    status = forms.ChoiceField(
        choices=[('', 'Todos os status')] + LembreteEnviado.STATUS,
        required=False,
        widget=forms.Select(attrs={
            'class': 'block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500'
        })
    )
    
    data_inicio = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500'
        }),
        label='Data início'
    )
    
    data_fim = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500'
        }),
        label='Data fim'
    )
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500',
            'placeholder': 'Buscar por inquilino, endereço ou observação...'
        }),
        label='Buscar'
    )