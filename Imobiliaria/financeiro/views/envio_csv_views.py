# financeiro/views/envio_csv_views.py
import csv
import io
import logging
import pandas as pd
from datetime import datetime
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings
import os

# Importar classes existentes
from financeiro.views.lembrete_views import WhatsAppZAPIService, is_dry_run_mode
from financeiro.models.lembrete import LembreteEnviado

logger = logging.getLogger(__name__)

# ================================================================
# FORMULÁRIOS PARA UPLOAD CSV
# ================================================================

from django import forms

class UploadCSVForm(forms.Form):
    """Formulário para upload de arquivo CSV de leads"""
    
    DELIMITADORES = [
        (',', 'Vírgula (,)'),
        (';', 'Ponto e vírgula (;)'),
        ('\t', 'Tab'),
        ('|', 'Pipe (|)'),
    ]
    
    CODIFICACOES = [
        ('utf-8', 'UTF-8'),
        ('latin-1', 'Latin-1 (ISO-8859-1)'),
        ('cp1252', 'Windows-1252'),
    ]
    
    # Upload do arquivo
    arquivo_csv = forms.FileField(
        label="Arquivo CSV",
        help_text="Selecione um arquivo CSV com os dados dos leads",
        widget=forms.FileInput(attrs={
            'accept': '.csv,.txt',
            'class': 'form-control'
        })
    )
    
    # Configurações de parsing
    delimitador = forms.ChoiceField(
        choices=DELIMITADORES,
        initial=',',
        label="Delimitador",
        help_text="Como os campos são separados no arquivo"
    )
    
    codificacao = forms.ChoiceField(
        choices=CODIFICACOES,
        initial='utf-8',
        label="Codificação",
        help_text="Codificação do arquivo CSV"
    )
    
    primeira_linha_cabecalho = forms.BooleanField(
        initial=True,
        required=False,
        label="Primeira linha contém cabeçalhos",
        help_text="Marque se a primeira linha do CSV contém os nomes das colunas"
    )

class ConfigurarEnvioCSVForm(forms.Form):
    """Formulário para configurar o envio após upload do CSV"""
    
    TIPOS_ENVIO = [
        ('whatsapp', 'WhatsApp'),
        ('sms', 'SMS'),
        ('email', 'E-mail'),
    ]
    
    TIPOS_CAMPANHA = [
        ('promocional', 'Promocional'),
        ('informativo', 'Informativo'),
        ('follow_up', 'Follow-up'),
        ('apresentacao', 'Apresentação'),
        ('personalizado', 'Personalizado'),
    ]
    
    # Configurações básicas
    tipo_envio = forms.ChoiceField(
        choices=TIPOS_ENVIO,
        initial='whatsapp',
        label="Canal de Envio"
    )
    
    tipo_campanha = forms.ChoiceField(
        choices=TIPOS_CAMPANHA,
        initial='follow_up',
        label="Tipo de Campanha"
    )
    
    nome_campanha = forms.CharField(
        max_length=200,
        label="Nome da Campanha",
        help_text="Nome para identificar esta campanha nos relatórios",
        widget=forms.TextInput(attrs={
            'placeholder': 'Ex: Campanha Leads Junho 2025'
        })
    )
    
    # Mapeamento de campos
    campo_nome = forms.ChoiceField(
        label="Campo com o Nome",
        help_text="Selecione a coluna que contém o nome do lead"
    )
    
    campo_telefone = forms.ChoiceField(
        label="Campo com o Telefone",
        help_text="Selecione a coluna que contém o telefone do lead"
    )
    
    campo_email = forms.ChoiceField(
        required=False,
        label="Campo com o E-mail (opcional)",
        help_text="Para envios por e-mail ou logs"
    )
    
    campo_adicional_1 = forms.ChoiceField(
        required=False,
        label="Campo Adicional 1 (opcional)",
        help_text="Para usar em placeholders personalizados como {campo1}"
    )
    
    campo_adicional_2 = forms.ChoiceField(
        required=False,
        label="Campo Adicional 2 (opcional)",
        help_text="Para usar em placeholders personalizados como {campo2}"
    )
    
    # Conteúdo da mensagem
    assunto = forms.CharField(
        max_length=200,
        required=False,
        label="Assunto (para e-mail)",
        widget=forms.TextInput(attrs={
            'placeholder': 'Ex: Oportunidade Exclusiva para Você'
        })
    )
    
    mensagem = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 12,
            'placeholder': '''Olá {nome}!

Obrigado por demonstrar interesse em nossos imóveis.

Temos algumas opções que podem ser perfeitas para você:

🏢 Sobrados comerciais em localizações estratégicas
📍 Região dos médicos - Alto padrão
💰 Condições especiais de locação

Gostaria de agendar uma visita?

Entre em contato conosco:
📞 WhatsApp: (11) 99999-9999
📧 E-mail: contato@exemplo.com

Placeholders disponíveis:
{nome} - Nome do lead
{primeiro_nome} - Primeiro nome
{email} - E-mail do lead
{telefone} - Telefone
{campo1} - Campo adicional 1
{campo2} - Campo adicional 2
{data_atual} - Data atual'''
        }),
        label="Mensagem",
        help_text="Use {nome}, {primeiro_nome}, {email}, {telefone}, {campo1}, {campo2}, {data_atual} para personalizar"
    )
    
    # Filtros
    filtrar_por_estagio = forms.BooleanField(
        required=False,
        label="Filtrar por estágio específico"
    )
    
    estagio_selecionado = forms.CharField(
        max_length=100,
        required=False,
        label="Estágio",
        widget=forms.TextInput(attrs={
            'placeholder': 'Ex: Em análise, Novo lead, etc.'
        })
    )
    
    # Opções de envio
    testar_antes = forms.BooleanField(
        initial=True,
        required=False,
        label="Testar com primeiros 3 leads antes de enviar tudo",
        help_text="Recomendado para validar a mensagem"
    )
    
    ignorar_telefones_invalidos = forms.BooleanField(
        initial=True,
        required=False,
        label="Ignorar leads com telefones inválidos",
        help_text="Pular automaticamente leads sem telefone válido"
    )
    
    def __init__(self, *args, colunas_csv=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        if colunas_csv:
            # Criar choices para os campos de mapeamento
            choices = [('', '--- Selecione ---')] + [(col, col) for col in colunas_csv]
            
            self.fields['campo_nome'].choices = choices
            self.fields['campo_telefone'].choices = choices
            self.fields['campo_email'].choices = choices
            self.fields['campo_adicional_1'].choices = choices
            self.fields['campo_adicional_2'].choices = choices
            
            # Tentar detectar campos automaticamente
            for col in colunas_csv:
                col_lower = col.lower()
                
                # Detectar campo nome
                if 'nome' in col_lower and not self.fields['campo_nome'].initial:
                    self.fields['campo_nome'].initial = col
                
                # Detectar campo telefone
                if any(word in col_lower for word in ['telefone', 'phone', 'celular', 'whatsapp']) and not self.fields['campo_telefone'].initial:
                    self.fields['campo_telefone'].initial = col
                
                # Detectar campo email
                if 'email' in col_lower and not self.fields['campo_email'].initial:
                    self.fields['campo_email'].initial = col

# ================================================================
# SERVIÇO DE PROCESSAMENTO CSV
# ================================================================

class CSVLeadsService:
    """Serviço para processar CSV de leads"""
    
    def __init__(self):
        self.whatsapp_service = WhatsAppZAPIService()
    
    def processar_csv(self, arquivo, delimitador=',', codificacao='utf-8', tem_cabecalho=True):
        """Processa arquivo CSV e retorna dados estruturados"""
        
        try:
            # Ler conteúdo do arquivo
            if hasattr(arquivo, 'read'):
                conteudo = arquivo.read()
            else:
                with open(arquivo, 'rb') as f:
                    conteudo = f.read()
            
            # Decodificar
            if isinstance(conteudo, bytes):
                texto = conteudo.decode(codificacao)
            else:
                texto = conteudo
            
            # Usar pandas para parsing mais robusto
            df = pd.read_csv(
                io.StringIO(texto),
                delimiter=delimitador,
                encoding=codificacao if isinstance(conteudo, str) else None,
                header=0 if tem_cabecalho else None
            )
            
            # Limpar dados
            df = df.fillna('')  # Substituir NaN por string vazia
            
            # Converter para lista de dicionários
            leads = df.to_dict('records')
            colunas = list(df.columns)
            
            logger.info(f"CSV processado: {len(leads)} leads, {len(colunas)} colunas")
            
            return {
                'sucesso': True,
                'leads': leads,
                'colunas': colunas,
                'total': len(leads)
            }
            
        except Exception as e:
            logger.error(f"Erro ao processar CSV: {str(e)}")
            return {
                'sucesso': False,
                'erro': str(e),
                'leads': [],
                'colunas': [],
                'total': 0
            }
    
    def validar_telefone(self, telefone):
        """Valida se o telefone está em formato válido"""
        if not telefone:
            return False
        
        # Remover caracteres não numéricos
        numero_limpo = ''.join(filter(str.isdigit, str(telefone)))
        
        # Verificar se tem pelo menos 10 dígitos
        if len(numero_limpo) < 10:
            return False
        
        # Verificar se tem código do país (55 para Brasil)
        if not numero_limpo.startswith('55'):
            numero_limpo = '55' + numero_limpo
        
        # Verificar tamanho final (13 dígitos para celular brasileiro)
        return len(numero_limpo) >= 12
    
    def formatar_telefone_zapi(self, telefone):
        """Formata telefone para Z-API"""
        if not telefone:
            return None
        
        numero_limpo = ''.join(filter(str.isdigit, str(telefone)))
        
        if not numero_limpo.startswith('55'):
            numero_limpo = '55' + numero_limpo
        
        return numero_limpo if len(numero_limpo) >= 12 else None
    
    def personalizar_mensagem_lead(self, template, lead_data, mapeamento):
        """Personaliza mensagem com dados do lead"""
        
        # Extrair dados mapeados
        nome = lead_data.get(mapeamento.get('campo_nome', ''), 'Lead')
        telefone = lead_data.get(mapeamento.get('campo_telefone', ''), '')
        email = lead_data.get(mapeamento.get('campo_email', ''), '')
        campo1 = lead_data.get(mapeamento.get('campo_adicional_1', ''), '')
        campo2 = lead_data.get(mapeamento.get('campo_adicional_2', ''), '')
        
        # Processar nome
        primeiro_nome = nome.split()[0] if nome and ' ' in nome else nome
        
        # Preparar substituições
        substituicoes = {
            '{nome}': nome,
            '{primeiro_nome}': primeiro_nome,
            '{email}': email,
            '{telefone}': telefone,
            '{campo1}': str(campo1),
            '{campo2}': str(campo2),
            '{data_atual}': datetime.now().strftime('%d/%m/%Y'),
            '{data_atual_extenso}': datetime.now().strftime('%d de %B de %Y'),
        }
        
        # Aplicar substituições
        mensagem_final = template
        for placeholder, valor in substituicoes.items():
            mensagem_final = mensagem_final.replace(placeholder, valor)
        
        return mensagem_final
    
    def enviar_para_lead(self, lead_data, mensagem_template, mapeamento, tipo_envio, nome_campanha):
        """Envia mensagem para um lead específico"""
        
        # Extrair telefone
        telefone_original = lead_data.get(mapeamento.get('campo_telefone', ''), '')
        telefone_formatado = self.formatar_telefone_zapi(telefone_original)
        
        if not telefone_formatado:
            return {
                'sucesso': False,
                'erro': f'Telefone inválido: {telefone_original}',
                'telefone_usado': telefone_original
            }
        
        # Personalizar mensagem
        mensagem_final = self.personalizar_mensagem_lead(mensagem_template, lead_data, mapeamento)
        
        # Enviar
        try:
            if tipo_envio == 'whatsapp':
                resultado = self.whatsapp_service.enviar_mensagem(telefone_formatado, mensagem_final)
                sucesso = resultado.get('success', False)
                erro = resultado.get('error') if not sucesso else None
                message_id = resultado.get('message_id')
                
            elif tipo_envio == 'sms':
                # Implementar SMS se necessário
                if is_dry_run_mode():
                    sucesso = True
                    erro = None
                    message_id = f"SMS_DRY_{telefone_formatado}"
                else:
                    sucesso = False
                    erro = "SMS não implementado"
                    message_id = None
                    
            elif tipo_envio == 'email':
                # Implementar e-mail se necessário
                if is_dry_run_mode():
                    sucesso = True
                    erro = None
                    message_id = f"EMAIL_DRY_{telefone_formatado}"
                else:
                    sucesso = False
                    erro = "E-mail não implementado"
                    message_id = None
            
            # Registrar envio
            nome_lead = lead_data.get(mapeamento.get('campo_nome', ''), 'Lead')
            observacao = f"[CSV] {nome_campanha} - {nome_lead} - Tel: {telefone_original}"
            
            if erro:
                observacao += f" - ERRO: {erro}"
            
            LembreteEnviado.objects.create(
                tipo=tipo_envio,
                dias_antes_vencimento=0,
                status='enviado' if sucesso else 'falha',
                observacao=observacao
            )
            
            return {
                'sucesso': sucesso,
                'erro': erro,
                'message_id': message_id,
                'telefone_usado': telefone_formatado,
                'mensagem_enviada': mensagem_final if sucesso else None
            }
            
        except Exception as e:
            erro_str = str(e)
            logger.error(f"Erro no envio para lead {lead_data}: {erro_str}")
            
            return {
                'sucesso': False,
                'erro': erro_str,
                'telefone_usado': telefone_formatado
            }

# ================================================================
# VIEWS
# ================================================================


def upload_csv_leads(request):
    """View para upload de CSV de leads"""
    
    if request.method == 'POST':
        form = UploadCSVForm(request.POST, request.FILES)
        
        if form.is_valid():
            return processar_upload_csv(request, form)
    else:
        form = UploadCSVForm()
    
    context = {
        'form': form,
        'dry_run_ativo': is_dry_run_mode(),
    }
    
    return render(request, 'financeiro/csv/upload_csv.html', context)

def processar_upload_csv(request, form):
    """Processa o upload do CSV"""
    
    arquivo = request.FILES['arquivo_csv']
    delimitador = form.cleaned_data['delimitador']
    codificacao = form.cleaned_data['codificacao']
    tem_cabecalho = form.cleaned_data['primeira_linha_cabecalho']
    
    # Processar CSV
    service = CSVLeadsService()
    resultado = service.processar_csv(
        arquivo=arquivo,
        delimitador=delimitador,
        codificacao=codificacao,
        tem_cabecalho=tem_cabecalho
    )
    
    if not resultado['sucesso']:
        messages.error(request, f"Erro ao processar CSV: {resultado['erro']}")
        return render(request, 'financeiro/csv/upload_csv.html', {'form': form})
    
    # Salvar dados na sessão
    request.session['csv_leads'] = resultado['leads']
    request.session['csv_colunas'] = resultado['colunas']
    request.session['csv_total'] = resultado['total']
    
    messages.success(request, f"CSV processado com sucesso! {resultado['total']} leads encontrados.")
    
    return redirect('financeiro:configurar_envio_csv')


def configurar_envio_csv(request):
    """View para configurar o envio após upload do CSV"""
    
    # Verificar se há dados na sessão
    leads = request.session.get('csv_leads', [])
    colunas = request.session.get('csv_colunas', [])
    total = request.session.get('csv_total', 0)
    
    if not leads:
        messages.error(request, 'Nenhum dado de CSV encontrado. Faça o upload novamente.')
        return redirect('financeiro:upload_csv_leads')
    
    if request.method == 'POST':
        form = ConfigurarEnvioCSVForm(request.POST, colunas_csv=colunas)
        
        if form.is_valid():
            return processar_envio_csv(request, form, leads)
    else:
        form = ConfigurarEnvioCSVForm(colunas_csv=colunas)
    
    # Análise dos dados para preview
    preview_leads = leads[:5]  # Primeiros 5 para preview
    
    context = {
        'form': form,
        'preview_leads': preview_leads,
        'total_leads': total,
        'colunas': colunas,
        'dry_run_ativo': is_dry_run_mode(),
    }
    
    return render(request, 'financeiro/csv/configurar_envio.html', context)

def processar_envio_csv(request, form, leads):
    """Processa o envio das mensagens para os leads"""
    
    data = form.cleaned_data
    
    # Preparar mapeamento de campos
    mapeamento = {
        'campo_nome': data['campo_nome'],
        'campo_telefone': data['campo_telefone'],
        'campo_email': data.get('campo_email'),
        'campo_adicional_1': data.get('campo_adicional_1'),
        'campo_adicional_2': data.get('campo_adicional_2'),
    }
    
    # Filtrar leads se necessário
    leads_filtrados = leads
    
    if data.get('filtrar_por_estagio') and data.get('estagio_selecionado'):
        # Assumindo que há uma coluna 'Estágio' ou similar
        estagio_campo = None
        for coluna in leads[0].keys() if leads else []:
            if 'estágio' in coluna.lower() or 'estagio' in coluna.lower() or 'status' in coluna.lower():
                estagio_campo = coluna
                break
        
        if estagio_campo:
            leads_filtrados = [
                lead for lead in leads 
                if data['estagio_selecionado'].lower() in str(lead.get(estagio_campo, '')).lower()
            ]
            messages.info(request, f"Filtro aplicado: {len(leads_filtrados)} leads com estágio '{data['estagio_selecionado']}'")
    
    # Filtrar telefones inválidos se solicitado
    if data.get('ignorar_telefones_invalidos'):
        service = CSVLeadsService()
        leads_validos = []
        
        for lead in leads_filtrados:
            telefone = lead.get(mapeamento['campo_telefone'], '')
            if service.validar_telefone(telefone):
                leads_validos.append(lead)
        
        leads_filtrados = leads_validos
        messages.info(request, f"Filtro de telefones: {len(leads_filtrados)} leads com telefones válidos")
    
    if not leads_filtrados:
        messages.error(request, 'Nenhum lead válido encontrado após aplicar os filtros!')
        return redirect('financeiro:configurar_envio_csv')
    
    # Modo teste - enviar apenas para os primeiros 3
    if data.get('testar_antes'):
        leads_para_envio = leads_filtrados[:3]
        modo_teste = True
    else:
        leads_para_envio = leads_filtrados
        modo_teste = False
    
    # Processar envios
    service = CSVLeadsService()
    resultados = []
    enviados = 0
    falhas = 0
    
    dry_run_ativo = is_dry_run_mode()
    
    for lead in leads_para_envio:
        resultado = service.enviar_para_lead(
            lead_data=lead,
            mensagem_template=data['mensagem'],
            mapeamento=mapeamento,
            tipo_envio=data['tipo_envio'],
            nome_campanha=data['nome_campanha']
        )
        
        nome_lead = lead.get(mapeamento['campo_nome'], 'Lead')
        
        resultados.append({
            'lead': lead,
            'nome': nome_lead,
            'resultado': resultado
        })
        
        if resultado['sucesso']:
            enviados += 1
        else:
            falhas += 1
    
    # Salvar resultados na sessão
    request.session['resultados_csv'] = {
        'resultados': [
            {
                'nome': r['nome'],
                'telefone': r['lead'].get(mapeamento['campo_telefone'], ''),
                'sucesso': r['resultado']['sucesso'],
                'erro': r['resultado'].get('erro'),
                'mensagem': r['resultado'].get('mensagem_enviada')
            }
            for r in resultados
        ],
        'enviados': enviados,
        'falhas': falhas,
        'modo_teste': modo_teste,
        'nome_campanha': data['nome_campanha'],
        'dry_run': dry_run_ativo
    }
    
    # Limpar dados do CSV da sessão se não for teste
    if not modo_teste:
        for key in ['csv_leads', 'csv_colunas', 'csv_total']:
            if key in request.session:
                del request.session[key]
    
    # Mensagens de resultado
    modo_texto = " (DRY RUN)" if dry_run_ativo else ""
    teste_texto = " - MODO TESTE" if modo_teste else ""
    
    if enviados > 0:
        messages.success(
            request, 
            f'Envio concluído{modo_texto}{teste_texto}! {enviados} mensagens enviadas com sucesso.'
        )
    
    if falhas > 0:
        messages.warning(request, f'{falhas} falhas no envio.')
    
    if modo_teste:
        messages.info(
            request, 
            'Modo teste ativo. Apenas os primeiros 3 leads receberam mensagens. '
            'Se estiver tudo correto, refaça o processo desmarcando "Testar antes".'
        )
    
    return redirect('financeiro:resultados_csv')


def resultados_csv(request):
    """Exibe resultados do envio CSV"""
    
    resultados_data = request.session.get('resultados_csv')
    
    if not resultados_data:
        messages.info(request, 'Nenhum resultado de envio encontrado.')
        return redirect('financeiro:upload_csv_leads')
    
    # Limpar resultados da sessão após exibir
    if 'resultados_csv' in request.session:
        del request.session['resultados_csv']
    
    context = {
        'resultados': resultados_data['resultados'],
        'total_enviados': resultados_data['enviados'],
        'total_falhas': resultados_data['falhas'],
        'modo_teste': resultados_data['modo_teste'],
        'nome_campanha': resultados_data['nome_campanha'],
        'dry_run': resultados_data['dry_run'],
    }
    
    return render(request, 'financeiro/csv/resultados_csv.html', context)