# financeiro/views/lembrete_views.py - VERSÃO COMPLETA CORRIGIDA
import locale
import requests
import os
import logging
import uuid
from datetime import date, timedelta, datetime
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.conf import settings

from financeiro.models.lembrete import LembreteEnviado
from financeiro.models.cobranca import Cobranca
from financeiro.forms.lembrete_forms import ConfiguracaoLembreteForm, EnvioManualForm
from financeiro.services.cobranca_service import CobrancaService

logger = logging.getLogger(__name__)

# Configurar locale brasileiro
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_ALL, 'pt_BR')
    except:
        locale.setlocale(locale.LC_ALL, 'C')

# ================================================================
# CONFIGURAÇÃO DRY RUN
# ================================================================

def is_dry_run_mode():
    """Verifica se está em modo dry run"""
    return (
        os.getenv('LEMBRETE_DRY_RUN', 'False').lower() == 'true' or
        getattr(settings, 'LEMBRETE_DRY_RUN', False)
    )

def set_dry_run_mode(enabled=True):
    """Ativa/desativa modo dry run temporariamente"""
    os.environ['LEMBRETE_DRY_RUN'] = str(enabled)
    print(f"{'🧪 MODO DRY RUN ATIVADO' if enabled else '🚀 MODO REAL ATIVADO'}")

# ================================================================
# SERVIÇO WHATSAPP Z-API COM DRY RUN
# ================================================================

class WhatsAppZAPIService:
    """Serviço WhatsApp com suporte a dry run"""
    
    def __init__(self, dry_run=None):
        self.instance_id = os.getenv('ZAPI_INSTANCE_ID') or getattr(settings, 'ZAPI_INSTANCE_ID', None)
        self.token = os.getenv('ZAPI_TOKEN') or getattr(settings, 'ZAPI_TOKEN', None)
        self.client_token = os.getenv('ZAPI_CLIENT_TOKEN') or getattr(settings, 'ZAPI_CLIENT_TOKEN', None)
        
        # Modo dry run
        self.dry_run = dry_run if dry_run is not None else is_dry_run_mode()
    
    def formatar_telefone(self, telefone):
        """Formata telefone para Z-API (5511999999999)"""
        if not telefone:
            return None
        telefone_limpo = ''.join(filter(str.isdigit, telefone))
        if not telefone_limpo.startswith('55'):
            telefone_limpo = '55' + telefone_limpo
        return telefone_limpo if len(telefone_limpo) >= 13 else None
    
    def enviar_mensagem(self, numero, mensagem):
        """Envia mensagem via Z-API (com suporte a dry run)"""
        numero_formatado = self.formatar_telefone(numero)
        if not numero_formatado:
            return {"success": False, "error": "Número de telefone inválido"}
        
        # MODO DRY RUN - NÃO ENVIA DE VERDADE
        if self.dry_run:
            return self._simular_envio_dry_run(numero_formatado, mensagem)
        
        # MODO REAL - ENVIA DE VERDADE
        return self._enviar_real(numero_formatado, mensagem)
    
    def _simular_envio_dry_run(self, numero, mensagem):
        """Simula envio em modo dry run"""
        import random
        
        print("🧪 MODO DRY RUN - SIMULANDO ENVIO")
        print("=" * 50)
        print(f"📱 Para: {numero}")
        print(f"📝 Mensagem:")
        print("-" * 30)
        print(mensagem)
        print("-" * 30)
        
        # Simular sucesso/falha baseado em probabilidade
        sucesso = random.randint(1, 100) <= 90  # 90% de sucesso
        
        if sucesso:
            fake_id = f"DRY_{uuid.uuid4().hex[:8]}"
            print(f"✅ SIMULADO - Enviado com sucesso!")
            print(f"🆔 ID simulado: {fake_id}")
            
            return {
                "success": True,
                "data": {
                    "messageId": fake_id,
                    "id": fake_id,
                    "dry_run": True
                },
                "message_id": fake_id
            }
        else:
            erros_simulados = [
                "Número inválido",
                "Usuário bloqueou bot", 
                "Limite de API atingido",
                "Instância desconectada"
            ]
            erro = random.choice(erros_simulados)
            
            print(f"❌ SIMULADO - Falha no envio!")
            print(f"💥 Erro simulado: {erro}")
            
            return {
                "success": False,
                "error": f"[DRY RUN] {erro}",
                "dry_run": True
            }
    
    def _enviar_real(self, numero, mensagem):
        """Envio real via Z-API"""
        if not all([self.instance_id, self.token, self.client_token]):
            return {"success": False, "error": "Configurações Z-API não encontradas"}
        
        url = f"https://api.z-api.io/instances/{self.instance_id}/token/{self.token}/send-messages"
        
        payload = {
            "phone": numero,
            "message": mensagem
        }
        
        headers = {
            "Content-Type": "application/json",
            "client-token": self.client_token
        }
        
        try:
            logger.info(f"Enviando WhatsApp para {numero} via Z-API")
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('messageId') or result.get('id'):
                    message_id = result.get('messageId') or result.get('id')
                    logger.info(f"WhatsApp enviado com sucesso via Z-API - ID: {message_id}")
                    return {
                        "success": True, 
                        "data": result,
                        "message_id": message_id
                    }
                else:
                    error_msg = result.get('message') or result.get('error') or 'Resposta sem ID'
                    logger.error(f"Erro Z-API: {error_msg}")
                    return {"success": False, "error": error_msg}
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"Erro HTTP Z-API: {error_msg}")
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            error_msg = f"Erro Z-API: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

# ================================================================
# FUNÇÕES AUXILIARES CORRIGIDAS (Many-to-Many)
# ================================================================

def _buscar_inquilino_cobranca(cobranca):
    """
    Busca inquilino/cliente de uma cobrança usando o relacionamento CORRETO
    DESCOBERTO: contrato.inquilino.all() (Many-to-Many)
    """
    resultado = {
        'nome': 'Cliente',
        'telefone': None,
        'objeto': None
    }
    
    try:
        contrato = cobranca.contrato
        if not contrato:
            return resultado
        
        # ESTRATÉGIA PRINCIPAL: Many-to-Many inquilinos (CORRETO!)
        try:
            inquilinos = contrato.inquilino.all()
            
            if inquilinos.exists():
                # Pegar o primeiro inquilino
                inquilino = inquilinos.first()
                resultado['objeto'] = inquilino
                resultado['nome'] = getattr(inquilino, 'nome', 'Cliente')
                resultado['telefone'] = _buscar_telefone_objeto(inquilino)
                
                # Se encontrou telefone, retorna sucesso
                if resultado['telefone']:
                    return resultado
                
                # Se não tem telefone, tentar outros inquilinos
                for inquilino in inquilinos:
                    telefone = _buscar_telefone_objeto(inquilino)
                    if telefone:
                        resultado['objeto'] = inquilino
                        resultado['nome'] = getattr(inquilino, 'nome', 'Cliente')
                        resultado['telefone'] = telefone
                        return resultado
                
                # Se nenhum inquilino tem telefone, pelo menos retorna o nome
                return resultado
                
        except Exception as e:
            logger.warning(f"Erro ao acessar contrato.inquilino: {e}")
        
        # ESTRATÉGIA ALTERNATIVA: Via repasse (fallback)
        try:
            repasse = contrato.repasses_contrato.first()
            if repasse and hasattr(repasse, 'proprietario') and repasse.proprietario:
                cliente = repasse.proprietario
                resultado['objeto'] = cliente
                resultado['nome'] = getattr(cliente, 'nome', 'Cliente')
                resultado['telefone'] = _buscar_telefone_objeto(cliente)
                if resultado['telefone']:
                    return resultado
        except Exception as e:
            logger.warning(f"Erro ao acessar repasse: {e}")
        
        # ESTRATÉGIA FINAL: Extrair nome da string
        cobranca_str = str(cobranca)
        nome_extraido = _extrair_nome_da_string(cobranca_str)
        if nome_extraido and nome_extraido != 'Cliente':
            resultado['nome'] = nome_extraido
    
    except Exception as e:
        logger.warning(f"Erro geral ao buscar inquilino da cobrança {cobranca.pk}: {e}")
    
    return resultado


def _buscar_telefone_objeto(obj):
    """Busca telefone em um objeto (Cliente) de forma otimizada"""
    if not obj:
        return None
    
    campos_telefone = [
        'whatsapp', 'celular', 'telefone_celular', 'telefone',
        'phone', 'mobile', 'cel', 'tel', 'fone', 'contato'
    ]
    
    for campo in campos_telefone:
        if hasattr(obj, campo):
            telefone = getattr(obj, campo)
            if telefone:
                telefone_str = str(telefone).strip()
                telefone_limpo = ''.join(filter(str.isdigit, telefone_str))
                
                if len(telefone_limpo) >= 10:  # Mínimo 10 dígitos
                    return telefone_str
    
    return None


def _extrair_nome_da_string(texto):
    """Extrai nome de pessoa das strings de cobrança"""
    import re
    
    if not texto:
        return None
    
    # Padrão: "COB... - #24 - Nome Pessoa - Rua..."
    match = re.search(r'#\d+ - ([^-]+) - ', texto)
    if match:
        nome = match.group(1).strip()
        if _validar_nome(nome):
            return nome
    
    return None


def _validar_nome(nome):
    """Valida se é um nome de pessoa válido"""
    if not nome or len(nome) < 3:
        return False
    
    nome = nome.strip()
    
    if nome.isdigit() or ',' in nome:
        return False
    
    palavras_endereco = ['Rua', 'Av', 'Avenida', 'Alameda', 'Travessa', 'Praça']
    if any(palavra in nome for palavra in palavras_endereco):
        return False
    
    if ' ' not in nome or not any(c.isalpha() for c in nome):
        return False
    
    return True


def _buscar_cliente_com_telefone(nome):
    """Busca cliente pelo nome que tenha telefone válido"""
    if not nome:
        return None
    
    try:
        from sisimob.models import Cliente
        
        # Busca exata
        clientes = Cliente.objects.filter(nome__iexact=nome)
        for cliente in clientes:
            if _buscar_telefone_objeto(cliente):
                return cliente
        
        # Busca por partes do nome
        palavras = nome.split()
        if len(palavras) >= 2:
            primeiro_nome = palavras[0]
            clientes = Cliente.objects.filter(nome__icontains=primeiro_nome)
            for cliente in clientes:
                if _buscar_telefone_objeto(cliente):
                    return cliente
    
    except Exception as e:
        logger.warning(f"Erro ao buscar cliente com telefone '{nome}': {e}")
    
    return None


# ================================================================
# FUNÇÕES PRINCIPAIS CORRIGIDAS
# ================================================================

def simular_envio_lembrete(cobranca, tipo, template=None):
    """
    Função de envio com suporte a dry run (VERSÃO CORRIGIDA)
    """
    
    # Verificar modo dry run
    dry_run_ativo = is_dry_run_mode()
    
    # Para outros tipos que não WhatsApp, manter simulação
    if tipo != 'whatsapp':
        import random
        if dry_run_ativo:
            print(f"🧪 DRY RUN - Simulando envio {tipo}")
            return random.choice([True, True, True, False])
        else:
            return random.choice([True, True, True, False])
    
    # ENVIO WHATSAPP COM DRY RUN - USANDO A NOVA FUNÇÃO
    try:
        inquilino_info = _buscar_inquilino_cobranca(cobranca)
        
        if not inquilino_info['telefone']:
            logger.warning(f"Telefone não encontrado para {inquilino_info['nome']}")
            return False
        
        # Gerar mensagem
        if template:
            mensagem = template.format(
                nome=inquilino_info['nome'],
                primeiro_nome=inquilino_info['nome'].split()[0] if inquilino_info['nome'] else "Cliente",
                valor=cobranca.valor_total,
                vencimento=cobranca.data_vencimento.strftime('%d/%m/%y'),
            )
        else:
            mensagem = gerar_mensagem_completa_corrigida(cobranca)  # ← USAR A COMPLETA
        
        # Enviar via Z-API (com dry run)
        whatsapp_service = WhatsAppZAPIService(dry_run=dry_run_ativo)
        resultado = whatsapp_service.enviar_mensagem(inquilino_info['telefone'], mensagem)
        
        if resultado.get('success'):
            message_id = resultado.get('message_id', 'N/A')
            modo = "DRY RUN" if dry_run_ativo else "REAL"
            logger.info(f"{modo} - Lembrete para {inquilino_info['nome']} - ID: {message_id}")
            return True
        else:
            error_msg = resultado.get('error', 'Erro desconhecido')
            modo = "DRY RUN" if dry_run_ativo else "REAL"
            logger.error(f"{modo} - Falha para {inquilino_info['nome']}: {error_msg}")
            return False
            
    except Exception as e:
        logger.error(f"Erro no envio: {str(e)}")
        return False


def gerar_mensagem_cobranca(cobranca):
    """Gera mensagem de cobrança personalizada (VERSÃO CORRIGIDA)"""
    agora = timezone.localtime()
    hora = agora.hour
    
    # USAR A NOVA FUNÇÃO PARA BUSCAR INQUILINO
    inquilino_info = _buscar_inquilino_cobranca(cobranca)
    nome = inquilino_info['nome']
    primeiro_nome = nome.split()[0] if nome else "Cliente"
    
    # Saudação baseada no horário
    if hora < 12:
        saudacao = "Bom dia"
    elif hora < 18:
        saudacao = "Boa tarde"
    else:
        saudacao = "Boa noite"
    
    # Verbo flexionado
    hoje = date.today()
    vencimento = cobranca.data_vencimento
    if vencimento > hoje:
        verbo = "vencerá"
    elif vencimento == hoje:
        verbo = "vence"
    else:
        verbo = "venceu"
    
    # Valores monetários
    try:
        valor_total = getattr(cobranca, 'valor_total', 0) or 0
        valor_aluguel = getattr(cobranca, 'valor_aluguel', 0) or 0
        
        # Converter para Decimal
        if hasattr(valor_total, 'amount'):
            valor_total = valor_total.amount
        if hasattr(valor_aluguel, 'amount'):
            valor_aluguel = valor_aluguel.amount
            
        valor_total = Decimal(str(valor_total))
        valor_aluguel = Decimal(str(valor_aluguel))
        
        # Formatar valores
        valor_total_formatado = locale.currency(valor_total, grouping=True, symbol=None)
        valor_aluguel_formatado = locale.currency(valor_aluguel, grouping=True, symbol=None)
        
    except Exception as e:
        logger.error(f"Erro ao processar valores: {str(e)}")
        valor_total_formatado = f"{float(valor_total):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        valor_aluguel_formatado = f"{float(valor_aluguel):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    
    # Mensagem principal
    corpo = f"""{saudacao} {primeiro_nome}, tudo bem?

O aluguel {verbo} em {vencimento.strftime('%d/%m/%y')}, no valor de R$ {valor_total_formatado}.

Aluguel : R$ {valor_aluguel_formatado}"""
    
    # Valores adicionais (adaptar conforme seus campos)
    campos_extras = [
        ('valor_iptu', 'IPTU'),
        ('valor_condominio', 'Condomínio'),
        ('valor_agua', 'Água'),
        ('valor_luz', 'Luz'),
        ('valor_ajuste', 'Ajuste'),
        ('valor_multa', 'Multa'),
        ('valor_juros', 'Juros'),
    ]
    
    for campo, label in campos_extras:
        valor = getattr(cobranca, campo, 0) or 0
        if valor > 0:
            try:
                if hasattr(valor, 'amount'):
                    valor = valor.amount
                valor = Decimal(str(valor))
                valor_formatado = locale.currency(valor, grouping=True, symbol=None)
                corpo += f"\n{label} : R$ {valor_formatado}"
            except:
                pass
    
    # Buscar link do boleto
    link_boleto = None
    
    # 1. Primeiro tentar buscar na integração Asaas
    if hasattr(cobranca, 'asaas_integracao') and cobranca.asaas_integracao.boleto_url:
        link_boleto = cobranca.asaas_integracao.boleto_url
    
    # 2. Se não encontrou, buscar em outros campos
    if not link_boleto:
        campos_boleto = [
            'boleto_url', 'link_boleto', 'asaas_boleto_url', 
            'url_boleto', 'boleto_link', 'url_pagamento',
            'link_pagamento', 'boleto', 'url'
        ]
        
        for campo in campos_boleto:
            if hasattr(cobranca, campo):
                valor = getattr(cobranca, campo)
                if valor and ('http' in str(valor) or 'www.' in str(valor)):
                    link_boleto = str(valor)
                    break
    
    # Adicionar link do boleto se encontrado
    if link_boleto:
        corpo += f"\n\nSegue o link do boleto:\n{link_boleto}"
    
    return corpo

def lembrete_list(request):
    """Lista de lembretes enviados com filtros"""
    lembretes = LembreteEnviado.objects.select_related('cobranca', 'cobranca__contrato').all()
    
    # Filtros
    tipo_filtro = request.GET.get('tipo', '')
    status_filtro = request.GET.get('status', '')
    data_inicio = request.GET.get('data_inicio', '')
    data_fim = request.GET.get('data_fim', '')
    search = request.GET.get('search', '')
    
    if tipo_filtro:
        lembretes = lembretes.filter(tipo=tipo_filtro)
    
    if status_filtro:
        lembretes = lembretes.filter(status=status_filtro)
    
    if data_inicio:
        lembretes = lembretes.filter(data_envio__gte=data_inicio)
    
    if data_fim:
        lembretes = lembretes.filter(data_envio__lte=data_fim)
    
    if search:
        lembretes = lembretes.filter(
            Q(observacao__icontains=search)
        )
    
    # Paginação
    paginator = Paginator(lembretes, 20)
    page_number = request.GET.get('page')
    lembretes_page = paginator.get_page(page_number)
    
    # Estatísticas
    stats = {
        'total': lembretes.count(),
        'enviados': lembretes.filter(status='enviado').count(),
        'falhas': lembretes.filter(status='falha').count(),
        'hoje': lembretes.filter(data_envio__date=timezone.now().date()).count()
    }
    
    context = {
        'lembretes': lembretes_page,
        'stats': stats,
        'filtros': {
            'tipo': tipo_filtro,
            'status': status_filtro,
            'data_inicio': data_inicio,
            'data_fim': data_fim,
            'search': search
        },
        'tipos_choices': LembreteEnviado.CANAIS,
        'status_choices': LembreteEnviado.STATUS,
        'dry_run_ativo': is_dry_run_mode(),
    }
    
    return render(request, 'financeiro/lembretes/lembrete_list.html', context)


def lembrete_detail(request, pk):
    """Detalhes de um lembrete específico"""
    lembrete = get_object_or_404(LembreteEnviado, pk=pk)
    
    # Outros lembretes da mesma cobrança
    outros_lembretes = LembreteEnviado.objects.filter(
        cobranca=lembrete.cobranca
    ).exclude(pk=pk).order_by('-data_envio')
    
    context = {
        'lembrete': lembrete,
        'outros_lembretes': outros_lembretes,
    }
    
    return render(request, 'financeiro/lembretes/detail.html', context)


def configuracao_lembretes(request):
    """Configuração de lembretes automáticos"""
    if request.method == 'POST':
        form = ConfiguracaoLembreteForm(request.POST)
        if form.is_valid():
            # Salvar configurações (implementar modelo de configuração se necessário)
            messages.success(request, 'Configurações de lembretes atualizadas com sucesso!')
            return redirect('financeiro:configuracao_lembretes')
    else:
        # Carregar configurações existentes
        form = ConfiguracaoLembreteForm()
    
    context = {
        'form': form,
        'dry_run_ativo': is_dry_run_mode(),
    }
    
    return render(request, 'financeiro/lembretes/configuracao.html', context)


def envio_manual(request):
    """Envio manual de lembretes"""
    if request.method == 'POST':
        form = EnvioManualForm(request.POST)
        if form.is_valid():
            cobrancas = form.cleaned_data['cobrancas']
            tipo_envio = form.cleaned_data['tipo']
            template_personalizado = form.cleaned_data.get('template_personalizado')
            
            # Verificar se está em modo dry run
            dry_run_ativo = is_dry_run_mode()
            
            if dry_run_ativo:
                messages.info(request, '🧪 MODO DRY RUN ATIVO - Mensagens não serão enviadas de verdade!')
            
            # Processar envio para cada cobrança
            enviados = 0
            falhas = 0
            
            for cobranca in cobrancas:
                try:
                    # USAR FUNÇÃO CORRIGIDA
                    sucesso = simular_envio_lembrete(cobranca, tipo_envio, template_personalizado)
                    
                    # Registrar lembrete
                    dias_antes = (cobranca.data_vencimento - timezone.now().date()).days
                    
                    # Observação mais detalhada
                    observacao = ""
                    if dry_run_ativo:
                        observacao = "[DRY RUN] "
                    
                    if template_personalizado:
                        observacao += f"Template personalizado: {template_personalizado[:100]}..."
                    elif tipo_envio == 'whatsapp':
                        observacao += "Enviado via Z-API WhatsApp"
                    else:
                        observacao += f"Enviado via {tipo_envio}"
                    
                    LembreteEnviado.objects.create(
                        cobranca=cobranca,
                        tipo=tipo_envio,
                        dias_antes_vencimento=dias_antes,
                        status='enviado' if sucesso else 'falha',
                        observacao=observacao
                    )
                    
                    if sucesso:
                        enviados += 1
                        # Usar nome do inquilino da nova função
                        inquilino_info = _buscar_inquilino_cobranca(cobranca)
                        logger.info(f"Lembrete {tipo_envio} enviado para {inquilino_info['nome']}")
                    else:
                        falhas += 1
                        inquilino_info = _buscar_inquilino_cobranca(cobranca)
                        logger.warning(f"Falha no envio {tipo_envio} para {inquilino_info['nome']}")
                        
                except Exception as e:
                    falhas += 1
                    inquilino_info = _buscar_inquilino_cobranca(cobranca)
                    logger.error(f"Erro no envio para {inquilino_info['nome']}: {str(e)}")
            
            # Mensagem de sucesso com indicação do modo
            modo_texto = " (DRY RUN)" if dry_run_ativo else ""
            messages.success(
                request, 
                f'Envio concluído{modo_texto}! {enviados} enviados com sucesso, {falhas} falhas.'
            )
            return redirect('financeiro:lembrete_list')
    else:
        form = EnvioManualForm()
    
    context = {
        'form': form,
        'dry_run_ativo': is_dry_run_mode(),
    }
    
    return render(request, 'financeiro/lembretes/envio_programado.html', context)


@require_http_methods(["GET"])
def cobrancas_pendentes_api(request):
    """API para buscar cobranças pendentes (para AJAX)"""
    term = request.GET.get('term', '')
    
    cobrancas = Cobranca.objects.filter(
        status__in=['pendente', 'atrasada']
    ).select_related('contrato')
    
    if term:
        cobrancas = cobrancas.filter(
            Q(contrato__imovel__endereco__icontains=term)
        )
    
    cobrancas = cobrancas[:20]  # Limitar resultados
    
    results = []
    for cobranca in cobrancas:
        # Usar a nova função para buscar inquilino
        inquilino_info = _buscar_inquilino_cobranca(cobranca)
        
        results.append({
            'id': cobranca.pk,
            'text': f"{inquilino_info['nome']} - Venc: {cobranca.data_vencimento.strftime('%d/%m/%Y')}",
            'vencimento': cobranca.data_vencimento.strftime('%Y-%m-%d'),
            'valor': str(cobranca.valor_total)
        })
    
    return JsonResponse({'results': results})


def dashboard_lembretes(request):
    """Dashboard com estatísticas de lembretes"""
    hoje = timezone.now().date()
    ultima_semana = hoje - timedelta(days=7)
    ultimo_mes = hoje - timedelta(days=30)
    
    # Estatísticas gerais
    stats = {
        'total_ultima_semana': LembreteEnviado.objects.filter(
            data_envio__gte=ultima_semana
        ).count(),
        'total_ultimo_mes': LembreteEnviado.objects.filter(
            data_envio__gte=ultimo_mes
        ).count(),
        'taxa_sucesso_semana': 0,
        'taxa_sucesso_mes': 0,
    }
    
    # Taxa de sucesso
    lembretes_semana = LembreteEnviado.objects.filter(data_envio__gte=ultima_semana)
    if lembretes_semana.exists():
        enviados_semana = lembretes_semana.filter(status='enviado').count()
        stats['taxa_sucesso_semana'] = round((enviados_semana / lembretes_semana.count()) * 100, 1)
    
    lembretes_mes = LembreteEnviado.objects.filter(data_envio__gte=ultimo_mes)
    if lembretes_mes.exists():
        enviados_mes = lembretes_mes.filter(status='enviado').count()
        stats['taxa_sucesso_mes'] = round((enviados_mes / lembretes_mes.count()) * 100, 1)
    
    # Estatísticas por canal
    stats_por_canal = LembreteEnviado.objects.filter(
        data_envio__gte=ultimo_mes
    ).values('tipo').annotate(
        total=Count('id'),
        enviados=Count('id', filter=Q(status='enviado')),
        falhas=Count('id', filter=Q(status='falha'))
    )
    
    # Cobranças que precisam de lembrete
    cobrancas_pendentes = Cobranca.objects.filter(
        status__in=['pendente', 'atrasada'],
        data_vencimento__lte=hoje + timedelta(days=10)
    ).count()
    
    context = {
        'stats': stats,
        'stats_por_canal': stats_por_canal,
        'cobrancas_pendentes': cobrancas_pendentes,
        'dry_run_ativo': is_dry_run_mode(),
    }
    
    return render(request, 'financeiro/lembretes/dashboard.html', context)


# ================================================================
# FUNÇÕES AUXILIARES PARA TESTES
# ================================================================

def testar_dry_run():
    """Função para testar dry run via shell"""
    print("🧪 TESTE DRY RUN - LEMBRETES")
    print("=" * 50)
    
    # Ativar modo dry run
    set_dry_run_mode(True)
    
    # Buscar cobranças para teste
    cobrancas = Cobranca.objects.filter(status='pendente')[:3]
    
    if not cobrancas.exists():
        print("❌ Nenhuma cobrança pendente encontrada")
        return
    
    print(f"📋 Testando com {cobrancas.count()} cobranças")
    
    sucessos = 0
    falhas = 0
    
    for cobranca in cobrancas:
        inquilino_info = _buscar_inquilino_cobranca(cobranca)
        print(f"\n👤 Testando: {inquilino_info['nome']}")
        resultado = simular_envio_lembrete(cobranca, 'whatsapp')
        
        if resultado:
            sucessos += 1
        else:
            falhas += 1
    
    print(f"\n📊 RESULTADO DO TESTE:")
    print(f"✅ Sucessos: {sucessos}")
    print(f"❌ Falhas: {falhas}")
    print(f"📈 Taxa de sucesso: {(sucessos/(sucessos+falhas)*100):.1f}%")
    
    # Desativar modo dry run
    set_dry_run_mode(False)

def gerar_mensagem_completa_melhorada(cobranca):
    """
    Gera mensagem completa incluindo PIX, código de barras e boleto
    Combina a função original com informações de pagamento
    """
    agora = timezone.localtime()
    hora = agora.hour
    
    # USAR A FUNÇÃO EXISTENTE PARA BUSCAR INQUILINO
    inquilino_info = _buscar_inquilino_cobranca(cobranca)
    nome = inquilino_info['nome']
    primeiro_nome = nome.split()[0] if nome else "Cliente"
    
    # Saudação baseada no horário
    if hora < 12:
        saudacao = "Bom dia"
    elif hora < 18:
        saudacao = "Boa tarde"
    else:
        saudacao = "Boa noite"
    
    # Verbo flexionado
    hoje = date.today()
    vencimento = cobranca.data_vencimento
    if vencimento > hoje:
        verbo = "vencerá"
    elif vencimento == hoje:
        verbo = "vence"
    else:
        verbo = "venceu"
    
    # Valores monetários
    try:
        valor_total = getattr(cobranca, 'valor_total', 0) or 0
        valor_aluguel = getattr(cobranca, 'valor_aluguel', 0) or 0
        
        # Converter para Decimal
        if hasattr(valor_total, 'amount'):
            valor_total = valor_total.amount
        if hasattr(valor_aluguel, 'amount'):
            valor_aluguel = valor_aluguel.amount
            
        valor_total = Decimal(str(valor_total))
        valor_aluguel = Decimal(str(valor_aluguel))
        
        # Formatar valores
        try:
            valor_total_formatado = locale.currency(valor_total, grouping=True, symbol=None)
            valor_aluguel_formatado = locale.currency(valor_aluguel, grouping=True, symbol=None)
        except:
            valor_total_formatado = f"{float(valor_total):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            valor_aluguel_formatado = f"{float(valor_aluguel):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        
    except Exception as e:
        logger.error(f"Erro ao processar valores: {str(e)}")
        valor_total_formatado = f"{float(valor_total):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        valor_aluguel_formatado = f"{float(valor_aluguel):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    
    # Mensagem principal
    corpo = f"""{saudacao} {primeiro_nome}, tudo bem?

O aluguel {verbo} em {vencimento.strftime('%d/%m/%y')}, no valor de R$ {valor_total_formatado}.

Aluguel: R$ {valor_aluguel_formatado}"""
    
    # Valores adicionais (adaptar conforme seus campos)
    campos_extras = [
        ('valor_iptu', 'IPTU'),
        ('valor_condominio', 'Condomínio'),
        ('valor_agua', 'Água'),
        ('valor_luz', 'Luz'),
        ('valor_gas', 'Gás'),
        ('valor_internet', 'Internet'),
        ('valor_seguro', 'Seguro'),
        ('valor_taxa', 'Taxa'),
        ('valor_ajuste', 'Ajuste'),
        ('valor_multa', 'Multa'),
        ('valor_juros', 'Juros'),
        ('valor_desconto', 'Desconto'),
    ]
    
    for campo, label in campos_extras:
        if hasattr(cobranca, campo):
            valor = getattr(cobranca, campo, 0) or 0
            if valor > 0:
                try:
                    if hasattr(valor, 'amount'):
                        valor = valor.amount
                    valor = Decimal(str(valor))
                    try:
                        valor_formatado = locale.currency(valor, grouping=True, symbol=None)
                    except:
                        valor_formatado = f"{float(valor):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                    corpo += f"\n{label}: R$ {valor_formatado}"
                except:
                    pass
    
    # ========================================================
    # INFORMAÇÕES DE PAGAMENTO - PARTE NOVA E IMPORTANTE!
    # ========================================================
    
    # 1. BOLETO - Buscar link do boleto
    link_boleto = None
    
    # Tentar buscar na integração Asaas primeiro
    if hasattr(cobranca, 'asaas_integracao') and cobranca.asaas_integracao:
        if hasattr(cobranca.asaas_integracao, 'boleto_url') and cobranca.asaas_integracao.boleto_url:
            link_boleto = cobranca.asaas_integracao.boleto_url
    
    # Se não encontrou, buscar em outros campos possíveis
    if not link_boleto:
        campos_boleto = [
            'boleto_url', 'link_boleto', 'asaas_boleto_url', 
            'url_boleto', 'boleto_link', 'url_pagamento',
            'link_pagamento', 'boleto', 'url', 'asaas_url'
        ]
        
        for campo in campos_boleto:
            if hasattr(cobranca, campo):
                valor = getattr(cobranca, campo)
                if valor and ('http' in str(valor) or 'www.' in str(valor)):
                    link_boleto = str(valor)
                    break
    
    # 2. CÓDIGO DE BARRAS
    codigo_barras = None
    campos_codigo_barras = [
        'codigo_barras', 'nosso_numero', 'linha_digitavel', 
        'asaas_codigo_barras', 'barcode', 'codigo_pagamento'
    ]
    
    for campo in campos_codigo_barras:
        if hasattr(cobranca, campo):
            codigo = getattr(cobranca, campo)
            if codigo and str(codigo).strip():
                codigo_barras = str(codigo).strip()
                break
    
    # 3. PIX - Buscar código PIX
    codigo_pix = None
    campos_pix = [
        'pix_copia_cola', 'pix_codigo', 'asaas_pix', 'pix_qr_code_text',
        'pix_payload', 'codigo_pix', 'pix_string', 'pix_emv'
    ]
    
    for campo in campos_pix:
        if hasattr(cobranca, campo):
            pix = getattr(cobranca, campo)
            if pix and str(pix).strip():
                codigo_pix = str(pix).strip()
                break
    
    # ========================================================
    # ADICIONAR INFORMAÇÕES DE PAGAMENTO À MENSAGEM
    # ========================================================
    
    # Adicionar link do boleto se encontrado
    if link_boleto:
        corpo += f"\n\n🔗 *Link do boleto:*\n{link_boleto}"
    
    # Adicionar código de barras se encontrado
    if codigo_barras:
        corpo += f"\n\n📊 *Código de barras:*\n`{codigo_barras}`"
    
    # Adicionar código PIX se encontrado
    if codigo_pix:
        corpo += f"\n\n💳 *PIX (copiar e colar):*\n`{codigo_pix}`"
    
    # Se nenhuma forma de pagamento foi encontrada, adicionar orientação
    if not any([link_boleto, codigo_barras, codigo_pix]):
        corpo += f"\n\n📞 Entre em contato para obter as informações de pagamento."
    
    return corpo


# ========================================================
# VERSÃO ALTERNATIVA - Mais robusta com logs
# ========================================================

def gerar_mensagem_completa_com_debug(cobranca):
    """Versão com logs para debug - ajuda a identificar quais campos existem"""
    
    print(f"\n🔍 DEBUG - Gerando mensagem para cobrança {cobranca.pk}")
    print(f"📋 Campos disponíveis na cobrança:")
    
    # Listar todos os campos da cobrança para debug
    for field in cobranca._meta.fields:
        field_name = field.name
        try:
            field_value = getattr(cobranca, field_name)
            if field_value:
                print(f"   ✅ {field_name}: {field_value}")
            else:
                print(f"   ⚪ {field_name}: (vazio)")
        except:
            print(f"   ❌ {field_name}: (erro ao acessar)")
    
    # Verificar se tem integração Asaas
    if hasattr(cobranca, 'asaas_integracao'):
        print(f"🔗 Integração Asaas encontrada")
        if cobranca.asaas_integracao:
            for field in cobranca.asaas_integracao._meta.fields:
                field_name = field.name
                try:
                    field_value = getattr(cobranca.asaas_integracao, field_name)
                    if field_value:
                        print(f"   ✅ asaas.{field_name}: {field_value}")
                except:
                    pass
    else:
        print(f"❌ Sem integração Asaas")
    
    # Gerar mensagem usando função melhorada
    mensagem = gerar_mensagem_completa_melhorada(cobranca)
    
    print(f"📝 Mensagem gerada:")
    print("-" * 50)
    print(mensagem)
    print("-" * 50)
    
    return mensagem

def gerar_mensagem_completa_corrigida(cobranca):
    """
    Gera mensagem completa incluindo PIX e boleto via AsaasIntegracao
    VERSÃO CORRIGIDA baseada na investigação
    """
    agora = timezone.localtime()
    hora = agora.hour
    
    # USAR A FUNÇÃO EXISTENTE PARA BUSCAR INQUILINO
    inquilino_info = _buscar_inquilino_cobranca(cobranca)
    nome = inquilino_info['nome']
    primeiro_nome = nome.split()[0] if nome else "Cliente"
    
    # Saudação baseada no horário
    if hora < 12:
        saudacao = "Bom dia"
    elif hora < 18:
        saudacao = "Boa tarde"
    else:
        saudacao = "Boa noite"
    
    # Verbo flexionado
    hoje = date.today()
    vencimento = cobranca.data_vencimento
    if vencimento > hoje:
        verbo = "vencerá"
    elif vencimento == hoje:
        verbo = "vence"
    else:
        verbo = "venceu"
    
    # Usar o campo 'valor' que existe no modelo
    try:
        valor_total = getattr(cobranca, 'valor', 0) or 0
        
        # Converter para Decimal se necessário
        if hasattr(valor_total, 'amount'):
            valor_total = valor_total.amount
            
        valor_total = Decimal(str(valor_total))
        
        # Formatar valor
        try:
            valor_total_formatado = locale.currency(valor_total, grouping=True, symbol=None)
        except:
            valor_total_formatado = f"{float(valor_total):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        
    except Exception as e:
        logger.error(f"Erro ao processar valor: {str(e)}")
        valor_total_formatado = "N/A"
    
    # Mensagem principal básica
    corpo = f"""{saudacao} {primeiro_nome}, tudo bem?

O aluguel {verbo} em {vencimento.strftime('%d/%m/%Y')}, no valor de R$ {valor_total_formatado}."""
    
    # Tentar adicionar descrição se existir
    if hasattr(cobranca, 'descricao') and cobranca.descricao:
        # Extrair apenas a parte útil da descrição (sem quebras de linha excessivas)
        descricao = cobranca.descricao.strip()
        if descricao and len(descricao) > 10:
            # Limitar tamanho da descrição para não ficar muito longa
            if len(descricao) > 300:
                descricao = descricao[:297] + "..."
            corpo += f"\n\n{descricao}"
    
    # ========================================================
    # BUSCAR INFORMAÇÕES DE PAGAMENTO VIA ASAAS_INTEGRACAO
    # ========================================================
    
    try:
        # Verificar se tem integração Asaas
        if hasattr(cobranca, 'asaas_integracao') and cobranca.asaas_integracao:
            integracao = cobranca.asaas_integracao
            
            print(f"🔍 DEBUG: Encontrou integração Asaas para cobrança {cobranca.pk}")
            
            # 1. BOLETO URL
            boleto_url = getattr(integracao, 'boleto_url', None)
            if boleto_url and str(boleto_url).strip():
                corpo += f"\n\n🔗 *Link do boleto:*\n{boleto_url}"
                print(f"✅ Boleto URL encontrado: {boleto_url}")
            
            # 2. PIX COPIA E COLA
            pix_copia_cola = getattr(integracao, 'pix_copia_cola', None)
            if pix_copia_cola and str(pix_copia_cola).strip():
                corpo += f"\n\n💳 *PIX (copiar e colar):*\n`{pix_copia_cola}`"
                print(f"✅ PIX encontrado: {pix_copia_cola[:50]}...")
            
            # 3. CÓDIGO DE BARRAS (se existir)
            # Vamos verificar se existe esse campo na integração
            campos_codigo_possiveis = [
                'codigo_barras', 'linha_digitavel', 'nosso_numero', 
                'barcode', 'codigo_pagamento'
            ]
            
            codigo_barras = None
            for campo in campos_codigo_possiveis:
                if hasattr(integracao, campo):
                    valor = getattr(integracao, campo)
                    if valor and str(valor).strip():
                        codigo_barras = str(valor).strip()
                        print(f"✅ Código de barras encontrado em {campo}: {codigo_barras}")
                        break
            
            if codigo_barras:
                corpo += f"\n\n📊 *Código de barras:*\n`{codigo_barras}`"
            
            # 4. INFORMAÇÕES ADICIONAIS
            asaas_id = getattr(integracao, 'asaas_id', None)
            gateway_status = getattr(integracao, 'gateway_status', None)
            
            if not any([boleto_url, pix_copia_cola, codigo_barras]):
                if asaas_id:
                    corpo += f"\n\n📋 *ID de pagamento:* {asaas_id}"
                    if gateway_status:
                        corpo += f"\n*Status:* {gateway_status}"
                
        else:
            print(f"❌ Cobrança {cobranca.pk} não tem integração Asaas")
            # Adicionar orientação se não tem integração
            corpo += f"\n\n📞 Entre em contato para obter as informações de pagamento."
            
    except Exception as e:
        print(f"❌ Erro ao acessar integração Asaas: {e}")
        logger.error(f"Erro ao buscar dados Asaas para cobrança {cobranca.pk}: {str(e)}")
        # Se der erro, pelo menos manter a mensagem básica
    
    return corpo


# ========================================================
# VERSÃO DE TESTE COM LOGS DETALHADOS
# ========================================================

def gerar_mensagem_com_debug_detalhado(cobranca):
    """Versão com logs super detalhados para debug"""
    
    print(f"\n🧪 DEBUG DETALHADO - Cobrança ID: {cobranca.pk}")
    print("=" * 50)
    
    # Verificar integração Asaas
    print(f"🔍 Verificando asaas_integracao...")
    
    if hasattr(cobranca, 'asaas_integracao'):
        print(f"✅ Atributo asaas_integracao existe")
        
        integracao = cobranca.asaas_integracao
        if integracao:
            print(f"✅ Objeto de integração encontrado: {type(integracao)}")
            
            # Listar TODOS os campos da integração
            print(f"📋 Campos disponíveis na integração:")
            for field in integracao._meta.fields:
                field_name = field.name
                try:
                    valor = getattr(integracao, field_name)
                    if valor not in [None, '', 0, False]:
                        valor_str = str(valor)
                        if len(valor_str) > 80:
                            valor_str = valor_str[:77] + "..."
                        print(f"   ✅ {field_name:<20}: {valor_str}")
                    else:
                        print(f"   ⚪ {field_name:<20}: (vazio)")
                except Exception as e:
                    print(f"   ❌ {field_name:<20}: erro - {e}")
        else:
            print(f"❌ asaas_integracao é None")
    else:
        print(f"❌ Atributo asaas_integracao não existe")
    
    # Gerar mensagem usando função corrigida
    mensagem = gerar_mensagem_completa_corrigida(cobranca)
    
    print(f"\n📝 MENSAGEM FINAL:")
    print("-" * 30)
    print(mensagem)
    print("-" * 30)
    
    return mensagem


# ========================================================
# FUNÇÃO PARA TESTAR NO SHELL
# ========================================================

def testar_mensagem_cobranca(cobranca_id=None):
    """Função para testar a geração de mensagem no shell"""
    
    if cobranca_id:
        cobranca = Cobranca.objects.get(pk=cobranca_id)
    else:
        # Pegar uma cobrança que tem integração
        cobranca = Cobranca.objects.filter(asaas_integracao__isnull=False).first()
    
    if not cobranca:
        print("❌ Nenhuma cobrança encontrada")
        return
    
    print(f"🧪 Testando com cobrança ID: {cobranca.pk}")
    
    # Testar versão com debug
    mensagem = gerar_mensagem_com_debug_detalhado(cobranca)
    
    return mensagem

# Para testar no shell:
# testar_mensagem_cobranca(127)  # Usar ID específico
# testar_mensagem_cobranca()     # Usar primeira disponível

def envio_programado(request):
    """
    Interface para conferir e enviar lembretes programados 
    VERSÃO FINAL CORRIGIDA: Permite múltiplos lembretes por cobrança
    """
    from financeiro.utils.data_utils import dia_util_bancario_anterior, is_dia_util_bancario, proximo_dia_util_bancario

    print(f"🐛 REQUEST.GET completo: {dict(request.GET)}")
    configuracao_recebida = request.GET.get('configuracao_dias', 'NENHUMA')
    print(f"🐛 Configuração recebida: '{configuracao_recebida}'")
    
    # ================================================================
    # FUNÇÃO AUXILIAR PARA VERIFICAÇÃO CATEGORIZADA
    # ================================================================
    def verificar_lembrete_categorizado(cobranca, dias_config):
        """
        Verifica se um tipo específico de lembrete já foi enviado
        usando categorização inteligente para lidar com diferenças entre dias úteis e corridos
        """
        if dias_config == 10:
            # Lembretes de "longo prazo" (7-17 dias antes)
            range_min, range_max = 7, 17
        elif dias_config == 3:
            # Lembretes de "médio prazo" (2-6 dias antes)
            range_min, range_max = 2, 6
        elif dias_config == 0:
            # Lembretes do "dia do vencimento" (vencidos ou no dia)
            range_min, range_max = -30, 1
        else:
            # Para outros valores, usar tolerância padrão
            range_min = dias_config - 3
            range_max = dias_config + 3
        
        ja_enviado = LembreteEnviado.objects.filter(
            cobranca=cobranca,
            status='enviado',
            dias_antes_vencimento__range=[range_min, range_max]
        ).exists()
        
        return ja_enviado
    
    # ================================================================
    # PROCESSAMENTO DOS PARÂMETROS
    # ================================================================
    data_referencia_str = request.GET.get('data_referencia')
    configuracao_dias_str = request.GET.get('configuracao_dias', '10,3,0')
    dias_personalizados_str = request.GET.get('dias_personalizados', '')
    incluir_ja_enviados = request.GET.get('incluir_ja_enviados') == 'on'
    apenas_em_atraso = request.GET.get('apenas_em_atraso') == 'on'
    valor_minimo_str = request.GET.get('valor_minimo', '')
    
    # Definir data de referência
    if data_referencia_str:
        try:
            data_referencia = datetime.strptime(data_referencia_str, '%Y-%m-%d').date()
        except ValueError:
            data_referencia = date.today()
            messages.error(request, 'Data inválida! Usando data atual.')
    else:
        data_referencia = date.today()
    
    # Datas auxiliares
    hoje = date.today()
    ontem = hoje - timedelta(days=1)
    amanha = hoje + timedelta(days=1)
    
    # Configurar dias antes do vencimento
    if configuracao_dias_str == 'personalizado' and dias_personalizados_str:
        try:
            dias_antes = [int(d.strip()) for d in dias_personalizados_str.split(',') if d.strip().isdigit()]
            if not dias_antes:
                dias_antes = [10, 3, 0]  # ← CORRIGIDO
                messages.warning(request, 'Configuração personalizada inválida! Usando padrão.')
        except:
            dias_antes = [10, 3, 0]  # ← CORRIGIDO
            messages.error(request, 'Erro na configuração personalizada! Usando padrão.')
    else:
        configuracoes = {
            '10,3,0': [10, 3, 0],  # ← CORRIGIDO: Padrão é 10, 3, 0 (sem 1 dia)
            '15,7,3,1,0': [15, 7, 3, 1, 0],
            '7,3,0': [7, 3, 0]
        }
        dias_antes = configuracoes.get(configuracao_dias_str, [10, 3, 0])  # ← CORRIGIDO
    
    # Filtro de valor mínimo
    valor_minimo = None
    if valor_minimo_str:
        try:
            valor_minimo = Decimal(valor_minimo_str)
        except:
            valor_minimo = None

    print(f"\n🔍 DEBUG ENVIO PROGRAMADO CORRIGIDO:")
    print(f"📅 Data de referência: {data_referencia}")
    print(f"📋 Configuração dias: {dias_antes}")
    print(f"📊 Incluir já enviados: {incluir_ja_enviados}")
    
    # ================================================================
    # PROCESSAMENTO POST (ENVIO DOS LEMBRETES)
    # ================================================================
    if request.method == 'POST':
        cobrancas_ids = request.POST.getlist('cobrancas_selecionadas')
        data_referencia_post = request.POST.get('data_referencia')
        
        if data_referencia_post:
            try:
                data_referencia = datetime.strptime(data_referencia_post, '%Y-%m-%d').date()
            except ValueError:
                data_referencia = hoje
        
        if not cobrancas_ids:
            messages.error(request, 'Nenhuma cobrança selecionada!')
            return redirect('financeiro:envio_programado')
        
        dry_run_ativo = is_dry_run_mode()
        enviados = 0
        falhas = 0
        
        for cobranca_id in cobrancas_ids:
            try:
                cobranca = Cobranca.objects.get(pk=cobranca_id)
                dias_antes_vencimento = (cobranca.data_vencimento - data_referencia).days
                sucesso = simular_envio_lembrete(cobranca, 'whatsapp')
                
                observacao = f"Enviado via interface - Data ref: {data_referencia.strftime('%d/%m/%Y')}"
                if dias_antes_vencimento < 0:
                    observacao += f" (COBRANÇA VENCIDA - {abs(dias_antes_vencimento)} dias)"
                elif dias_antes_vencimento == 0:
                    observacao += " (DIA DO VENCIMENTO)"
                else:
                    observacao += f" ({dias_antes_vencimento} dias antes)"
                
                if dry_run_ativo:
                    observacao = "[DRY RUN] " + observacao
                
                LembreteEnviado.objects.create(
                    cobranca=cobranca,  # ← CORRIGIDO: era "cobrança" com acento
                    tipo='whatsapp',
                    dias_antes_vencimento=max(0, dias_antes_vencimento),
                    status='enviado' if sucesso else 'falha',
                    observacao=observacao
                )
                
                if sucesso:
                    enviados += 1
                else:
                    falhas += 1
                    
            except Exception as e:
                falhas += 1
                logger.error(f"Erro no envio para cobranca {cobranca_id}: {str(e)}")
        
        modo_texto = " (DRY RUN)" if dry_run_ativo else ""
        data_texto = f" para {data_referencia.strftime('%d/%m/%Y')}" if data_referencia != hoje else ""
        
        if enviados > 0:
            messages.success(request, f'Envio concluído{modo_texto}{data_texto}! {enviados} enviados com sucesso.')
        
        if falhas > 0:
            messages.warning(request, f'{falhas} falhas no envio.')
        
        return redirect('financeiro:lembrete_list')
    
    # ================================================================
    # PROCESSAMENTO GET (BUSCAR LEMBRETES PROGRAMADOS)
    # ================================================================
    
    lembretes_programados = []
    total_geral = 0
    valor_total_geral = Decimal('0')
    clientes_unicos = set()
    
    # Buscar todas as cobranças pendentes
    todas_cobrancas = Cobranca.objects.filter(
        status__in=['pendente', 'atrasada']
    ).select_related('contrato').prefetch_related('contrato__inquilino')
    
    # Aplicar filtros básicos
    if valor_minimo:
        todas_cobrancas = todas_cobrancas.filter(valor_total__gte=valor_minimo)
    
    if apenas_em_atraso:
        todas_cobrancas = todas_cobrancas.filter(data_vencimento__lt=hoje)
    
    print(f"📋 Total de cobranças encontradas: {todas_cobrancas.count()}")
    
    # ================================================================
    # LÓGICA PRINCIPAL: VERIFICAR CADA TIPO DE LEMBRETE SEPARADAMENTE
    # ================================================================
    
    for dias in dias_antes:
        print(f"\n🔄 Processando lembretes para {dias} dias antes...")
        cobrancas_para_mostrar = []
        
        for cobranca in todas_cobrancas:
            
            # ============================================================
            # CÁLCULO DA DATA IDEAL DE ENVIO (híbrido: dias úteis + fallback)
            # ============================================================
            
            data_envio_ideal = None
            metodo_calculo = "desconhecido"
            
            try:
                # TENTATIVA 1: DIAS ÚTEIS
                if dias == 0:
                    data_envio_ideal = cobranca.data_vencimento
                    if not is_dia_util_bancario(data_envio_ideal):
                        data_envio_ideal = dia_util_bancario_anterior(cobranca.data_vencimento, 1)
                    metodo_calculo = "dia_vencimento_util"
                else:
                    data_envio_ideal = dia_util_bancario_anterior(cobranca.data_vencimento, dias)
                    metodo_calculo = f"dias_uteis_{dias}"
                
                if not data_envio_ideal or not isinstance(data_envio_ideal, date):
                    raise ValueError("Função de dias úteis retornou data inválida")
                    
            except Exception as e:
                # FALLBACK: DIAS CORRIDOS
                print(f"⚠️ Erro ao calcular dias úteis: {e}")
                if dias == 0:
                    data_envio_ideal = cobranca.data_vencimento
                    metodo_calculo = "dia_vencimento_corrido"
                else:
                    data_envio_ideal = cobranca.data_vencimento - timedelta(days=dias)
                    metodo_calculo = f"dias_corridos_{dias}"
            
            # ============================================================
            # VERIFICAÇÃO ESPECÍFICA: ESTE TIPO JÁ FOI ENVIADO? (CORRIGIDO)
            # ============================================================
            
            ja_enviado_este_tipo = verificar_lembrete_categorizado(cobranca, dias)
            
            print(f"💰 Cobrança ID {cobranca.pk} ({dias} dias):")
            print(f"   📅 Vencimento: {cobranca.data_vencimento}")
            print(f"   🎯 Data envio ideal: {data_envio_ideal}")
            print(f"   📤 Já enviado ESTE tipo ({dias} dias): {ja_enviado_este_tipo}")
            
            # ============================================================
            # LÓGICA DE COMPARAÇÃO DE DATAS
            # ============================================================
            
            dias_corridos_ate_vencimento = (cobranca.data_vencimento - data_referencia).days
            diferenca_envio = (data_envio_ideal - data_referencia).days
            
            # Condição de inclusão
            deve_incluir = False
            motivo_inclusao = ""
            
            if diferenca_envio <= 0:
                deve_incluir = True
                motivo_inclusao = f"hora_chegou (diferença: {diferenca_envio})"
            elif diferenca_envio == 1 and data_referencia.weekday() == 4:  # Sexta
                deve_incluir = True
                motivo_inclusao = "sexta_feira_antecipacao"
            elif dias == 0 and dias_corridos_ate_vencimento <= 1:
                deve_incluir = True
                motivo_inclusao = f"vencimento_proximo ({dias_corridos_ate_vencimento} dias)"
            
            print(f"   🎲 Deve incluir: {deve_incluir} - {motivo_inclusao}")
            
            if not deve_incluir:
                print(f"   ❌ PULANDO: {motivo_inclusao}")
                continue
            
            # ============================================================
            # VERIFICAR SE DEVE INCLUIR BASEADO NO FILTRO
            # ============================================================
            
            if ja_enviado_este_tipo and not incluir_ja_enviados:
                print(f"   ❌ PULANDO: Já enviado este tipo ({dias} dias) e não incluir enviados")
                continue
            
            # ============================================================
            # Buscar informações do inquilino
            # ============================================================
            
            inquilino_info = _buscar_inquilino_cobranca(cobranca)
            
            if not inquilino_info['telefone']:
                print(f"   ❌ PULANDO: Sem telefone válido")
                continue
            
            print(f"   ✅ INCLUINDO: {inquilino_info['nome']} - {motivo_inclusao}")
            
            # ============================================================
            # Adicionar à lista
            # ============================================================
            
            try:
                nome_curto = inquilino_info['nome'].split()[0] if inquilino_info['nome'] else 'Cliente'
                if dias == 0:
                    if cobranca.data_vencimento < data_referencia:
                        mensagem_preview = f"Olá {nome_curto}, seu aluguel VENCEU em {cobranca.data_vencimento.strftime('%d/%m/%Y')}..."
                    elif cobranca.data_vencimento == data_referencia:
                        mensagem_preview = f"Olá {nome_curto}, seu aluguel VENCE HOJE..."
                    else:
                        mensagem_preview = f"Olá {nome_curto}, seu aluguel vence em {cobranca.data_vencimento.strftime('%d/%m/%Y')}..."
                else:
                    mensagem_preview = f"Olá {nome_curto}, seu aluguel vence em {dias} dias..."
            except:
                mensagem_preview = "Erro ao gerar preview"
            
            dias_atraso_envio = max(0, (data_referencia - data_envio_ideal).days)
            
            cobrancas_para_mostrar.append({
                'cobranca': cobranca,
                'telefone': inquilino_info['telefone'],
                'mensagem_preview': mensagem_preview,
                'mensagem_completa': gerar_mensagem_completa_corrigida(cobranca),
                'ja_enviado': ja_enviado_este_tipo,  # ← Agora é específico para este tipo
                'nome_inquilino': inquilino_info['nome'],
                'inquilino': inquilino_info['objeto'],
                'data_envio_ideal': data_envio_ideal,
                'dias_corridos_ate_vencimento': dias_corridos_ate_vencimento,
                'esta_atrasado': dias_atraso_envio > 0,
                'dias_atraso': abs(diferenca_envio) if diferenca_envio < 0 else 0,
                'metodo_calculo': metodo_calculo,
                'motivo_inclusao': motivo_inclusao,
                'dias_antes_tipo': dias,  # ← Adicionar para referência
            })
            
            # Só contar valor uma vez por cobrança (no primeiro tipo)
            if dias == dias_antes[0]:  # Primeiro tipo da configuração
                valor_total_geral += cobranca.valor_total or Decimal('0')
                if inquilino_info['objeto']:
                    clientes_unicos.add(inquilino_info['objeto'].pk)
        
        print(f"📊 Encontradas {len(cobrancas_para_mostrar)} cobranças para {dias} dias antes")
        
        # ============================================================
        # Se encontrou cobranças para este grupo, adicionar
        # ============================================================
        
        if cobrancas_para_mostrar:
            
            # Ordenar por prioridade
            cobrancas_ordenadas = sorted(
                cobrancas_para_mostrar, 
                key=lambda x: (
                    0 if x['cobranca'].data_vencimento < data_referencia else 1,
                    0 if x['esta_atrasado'] else 1,
                    x['dias_corridos_ate_vencimento']
                )
            )
            
            pendentes_atrasados = [c for c in cobrancas_para_mostrar if c['esta_atrasado'] and not c['ja_enviado']]
            ja_enviados = [c for c in cobrancas_para_mostrar if c['ja_enviado']]
            
            datas_vencimento = [c['cobranca'].data_vencimento for c in cobrancas_para_mostrar]
            data_vencimento_display = min(datas_vencimento) if datas_vencimento else data_referencia
            
            valor_total_grupo = sum([c['cobranca'].valor_total or Decimal('0') for c in cobrancas_para_mostrar])
            
            lembretes_programados.append({
                'dias_antes': dias,
                'data_vencimento': data_vencimento_display,
                'cobrancas': cobrancas_ordenadas,
                'total': len(cobrancas_para_mostrar),
                'valor_total_grupo': valor_total_grupo,
                'pendentes_atrasados': len(pendentes_atrasados),
                'ja_enviados': len(ja_enviados)
            })
            
            total_geral += len(cobrancas_para_mostrar)
    
    print(f"\n📈 RESULTADO FINAL:")
    print(f"📋 Total de lembretes: {total_geral}")
    print(f"💰 Valor total: {valor_total_geral}")
    print(f"👥 Clientes únicos: {len(clientes_unicos)}")
    
    # ================================================================
    # PREPARAR CONTEXTO PARA O TEMPLATE
    # ================================================================
    
    # Verificar se é dia útil
    eh_dia_util_data = is_dia_util_bancario(data_referencia)
    proximo_util = proximo_dia_util_bancario(data_referencia) if not eh_dia_util_data else None
    
    # Formatar valor total
    valor_total_formatado = f"{valor_total_geral:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    
    context = {
        'lembretes_programados': lembretes_programados,
        'total_geral': total_geral,
        'valor_total_formatado': valor_total_formatado,
        'total_clientes': len(clientes_unicos),
        
        # Datas
        'data_selecionada': data_referencia,
        'data_hoje': hoje,
        'data_ontem': ontem,
        'data_amanha': amanha,
        'eh_dia_util': eh_dia_util_data,
        'proximo_dia_util': proximo_util,
        
        # Configurações
        'configuracao_dias': configuracao_dias_str,
        'dias_personalizados': dias_personalizados_str,
        'incluir_ja_enviados': incluir_ja_enviados,
        'apenas_em_atraso': apenas_em_atraso,
        'valor_minimo': valor_minimo_str,
        
        # Sistema
        'dry_run_ativo': is_dry_run_mode(),
    }
    
    return render(request, 'financeiro/lembretes/envio_programado.html', context)