# services/cobranca_service.py
import datetime
import requests
from decimal import Decimal
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.apps import apps

from financeiro.models import Cobranca
Contrato = apps.get_model("sisimob", "Contrato")


class CobrancaService:
    """Service para gerenciamento de cobranças"""
    
    @staticmethod
    def listar_contratos_sem_cobranca(mes, ano):
        """Lista contratos ativos que não possuem cobrança para o período"""
        Contrato = apps.get_model('sisimob', 'Contrato')
        
        # Buscar contratos ativos
        contratos_ativos = Contrato.objects.filter(
            status='ativo'  # Assumindo que existe um campo status
        ).select_related('inquilino', 'propriedade')
        
        # Filtrar contratos que não possuem cobrança no período
        contratos_sem_cobranca = []
        for contrato in contratos_ativos:
            if not Cobranca.objects.filter(
                contrato=contrato,
                mes_referencia=mes,
                ano_referencia=ano
            ).exists():
                contratos_sem_cobranca.append(contrato)
        
        return contratos_sem_cobranca
    
    @staticmethod
    def calcular_data_vencimento(contrato, mes, ano):
        """Calcula data de vencimento baseada no contrato"""
        dia_vencimento = getattr(contrato, 'dia_vencimento', 10)  # Default dia 10
        
        try:
            data_vencimento = datetime.date(ano, mes, dia_vencimento)
        except ValueError:
            # Se o dia não existe no mês (ex: 31 em fevereiro), usar último dia do mês
            if mes == 12:
                proximo_mes = datetime.date(ano + 1, 1, 1)
            else:
                proximo_mes = datetime.date(ano, mes + 1, 1)
            data_vencimento = proximo_mes - datetime.timedelta(days=1)
        
        return data_vencimento
    
    @staticmethod
    def criar_cobranca_preview(contrato, mes, ano):
        """Cria preview de cobrança sem salvar no banco"""
        # Calcular valor do aluguel
        valor_aluguel = getattr(contrato, 'valor_aluguel', Decimal('0.00'))
        if hasattr(contrato, 'valor_aluguel_atual'):
            valor_aluguel = contrato.valor_aluguel_atual()
        
        # Calcular despesas
        Despesa = apps.get_model('financeiro', 'Despesa')
        data_referencia = datetime.date(ano, mes, 1)
        
        despesas_inquilino = Despesa.objects.filter(
            contrato=contrato,
            is_ativa=True,
            paga_por='inquilino'
        )
        
        valor_despesas = sum(
            d.calcular_valor_parcela()
            for d in despesas_inquilino
            if d.parcela_ativa_em_data(data_referencia)
        )
        
        valor_total = valor_aluguel + valor_despesas
        data_vencimento = CobrancaService.calcular_data_vencimento(contrato, mes, ano)
        
        # Criar objeto temporário
        cobranca_preview = {
            'contrato': contrato,
            'contrato_id': contrato.id,
            'inquilino': getattr(contrato, 'inquilino', None),
            'mes_referencia': mes,
            'ano_referencia': ano,
            'valor_aluguel': valor_aluguel,
            'valor_despesas': valor_despesas,
            'valor_total': valor_total,
            'data_vencimento': data_vencimento,
            'descricao': CobrancaService.gerar_descricao_cobranca(
                contrato, mes, ano, valor_aluguel, despesas_inquilino, data_referencia
            )
        }
        
        return cobranca_preview
    
    @staticmethod
    def gerar_descricao_cobranca(contrato, mes, ano, valor_aluguel, despesas, data_referencia):
        """Gera descrição detalhada da cobrança"""
        meses = {
            1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
            5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
            9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
        }
        
        mes_nome = meses.get(mes, f'Mês {mes}')
        
        descricao_partes = [
            
            f"Valor do aluguel: R$ {valor_aluguel:,.2f}".replace('.', ',').replace(',', '.', 1)
        ]
        
        # Adicionar despesas se houver
        despesas_ativas = [
            d for d in despesas 
            if d.parcela_ativa_em_data(data_referencia)
        ]
        
        if despesas_ativas:
            descricao_partes.append("\nDespesas incluídas:")
            for despesa in despesas_ativas:
                valor_despesa = despesa.calcular_valor_parcela()
                valor_formatado = f"R$ {valor_despesa:,.2f}".replace('.', ',').replace(',', '.', 1)
                descricao_partes.append(f"• {despesa.nome}: {valor_formatado}")
        
        valor_total = valor_aluguel + sum(d.calcular_valor_parcela() for d in despesas_ativas)
        valor_total_formatado = f"R$ {valor_total:,.2f}".replace('.', ',').replace(',', '.', 1)
        descricao_partes.append(f"\nValor total: {valor_total_formatado}")
        
        return '\n'.join(descricao_partes)
    
    @staticmethod
    def listar_cobrancas_sugeridas(mes, ano, contrato_id=None):
        """Lista cobranças sugeridas para criação"""
        contratos = CobrancaService.listar_contratos_sem_cobranca(mes, ano)
        
        if contrato_id:
            contratos = [c for c in contratos if c.id == contrato_id]
        
        cobrancas_sugeridas = []
        for contrato in contratos:
            preview = CobrancaService.criar_cobranca_preview(contrato, mes, ano)
            cobrancas_sugeridas.append(preview)
        
        return cobrancas_sugeridas
    
    @staticmethod
    @transaction.atomic
    def criar_cobrancas_em_lote(cobrancas_data):
        """Cria múltiplas cobranças em uma transação"""
        cobrancas_criadas = []
        erros = []
        
        for cobranca_data in cobrancas_data:
            try:
                contrato = get_object_or_404(Contrato, id=cobranca_data['contrato_id'])
                
                # Verificar se já existe
                if Cobranca.objects.filter(
                    contrato=contrato,
                    mes_referencia=cobranca_data['mes_referencia'],
                    ano_referencia=cobranca_data['ano_referencia']
                ).exists():
                    erros.append(f"Cobrança já existe para contrato {contrato.id}")
                    continue
                
                # Criar cobrança
                cobranca = Cobranca.objects.create(
                    contrato=contrato,
                    inquilino=cobranca_data.get('inquilino') or getattr(contrato, 'inquilino', None),
                    mes_referencia=cobranca_data['mes_referencia'],
                    ano_referencia=cobranca_data['ano_referencia'],
                    valor_aluguel=cobranca_data['valor_aluguel'],
                    valor_total=cobranca_data['valor_total'],
                    data_vencimento=cobranca_data['data_vencimento'],
                    descricao=cobranca_data['descricao']
                )
                
                cobrancas_criadas.append(cobranca)
                
            except Exception as e:
                erros.append(f"Erro ao criar cobrança para contrato {cobranca_data.get('contrato_id')}: {str(e)}")
        
        return cobrancas_criadas, erros
    
    @staticmethod
    def integrar_cobranca_asaas(cobranca):
        """Integra cobrança individual com Asaas"""
        pode_integrar, erros_validacao = cobranca.pode_ser_integrada()
        
        if not pode_integrar:
            return {'status': 'error', 'erros': erros_validacao}
        
        try:
            # Verificar se inquilino tem ID do Asaas
            if not hasattr(cobranca.inquilino, 'asaas_id') or not cobranca.inquilino.asaas_id:
                return {
                    'status': 'error', 
                    'erros': ['Inquilino não possui ID do Asaas cadastrado']
                }
            
            payload = {
                "customer": cobranca.inquilino.asaas_id,
                "billingType": "BOLETO",
                "dueDate": cobranca.data_vencimento.strftime('%Y-%m-%d'),
                "value": float(cobranca.valor_total),
                "description": cobranca.descricao or cobranca.gerar_descricao_automatica(),
                "externalReference": f"cobranca_{cobranca.id}",
                "postalService": False
            }
            
            # Fazer requisição para Asaas (substituir pela implementação real)
            resultado = cobranca.gerar_cobranca_gateway()
            return resultado
            
        except Exception as e:
            return {'status': 'error', 'erros': [f'Erro na integração: {str(e)}']}
    
    @staticmethod
    @transaction.atomic
    def integrar_cobrancas_em_lote(cobranca_ids):
        """Integra múltiplas cobranças com Asaas"""
        cobrancas = Cobranca.objects.filter(id__in=cobranca_ids, integrada_asaas=False)
        
        sucessos = []
        erros = []
        
        for cobranca in cobrancas:
            resultado = CobrancaService.integrar_cobranca_asaas(cobranca)
            
            if resultado['status'] == 'success':
                sucessos.append(cobranca)
            else:
                erros.append({
                    'cobranca_id': cobranca.id,
                    'erros': resultado['erros']
                })
        
        return sucessos, erros
    
    @staticmethod
    def gerar_mensagem_whatsapp(cobranca):
        """Gera mensagem formatada para WhatsApp - VERSÃO CORRIGIDA"""
        
        # Verificar se a cobrança tem os dados necessários
        if not cobranca:
            return None
        
        try:
            # Saudação baseada no horário
            hora_atual = datetime.datetime.now().hour
            if 5 <= hora_atual < 12:
                saudacao = "Bom dia"
            elif 12 <= hora_atual < 18:
                saudacao = "Boa tarde"
            else:
                saudacao = "Boa noite"

            # Buscar nome do inquilino
            nome = "Cliente"
            if hasattr(cobranca, 'inquilino') and cobranca.inquilino:
                nome = getattr(cobranca.inquilino, 'nome', 'Cliente')
            
            # Se não tem inquilino, tentar buscar via contrato
            if nome == "Cliente" and hasattr(cobranca, 'contrato') and cobranca.contrato:
                try:
                    # Tentar buscar inquilinos via many-to-many
                    inquilinos = cobranca.contrato.inquilino.all()
                    if inquilinos.exists():
                        nome = inquilinos.first().nome
                except:
                    pass
            
            primeiro_nome = nome.split()[0] if nome and nome != "Cliente" else "Cliente"
            
            # Formatação de data e valor
            vencimento = cobranca.data_vencimento.strftime('%d/%m/%Y')
            
            # Formatar valor total
            valor_total = cobranca.valor_total or 0
            if hasattr(valor_total, 'amount'):
                valor_total = valor_total.amount
            valor_total_formatado = f"R$ {float(valor_total):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            
            # Verbo baseado na data
            hoje = datetime.date.today()
            if cobranca.data_vencimento > hoje:
                verbo = "vencerá"
            elif cobranca.data_vencimento == hoje:
                verbo = "vence"
            else:
                verbo = "venceu"
            
            # Construir mensagem básica
            mensagem_partes = [
                f"{saudacao} {primeiro_nome}, tudo bem?",
                "",
                f"O aluguel {verbo} em {vencimento}, no valor de {valor_total_formatado}."
            ]
            
            # Tentar adicionar descrição detalhada
            descricao = None
            
            # 1. Tentar campo 'descricao' se existir
            if hasattr(cobranca, 'descricao') and cobranca.descricao:
                descricao = cobranca.descricao
            
            # 2. Tentar gerar descrição automática se o método existir
            elif hasattr(cobranca, 'gerar_descricao_automatica'):
                try:
                    descricao = cobranca.gerar_descricao_automatica()
                except:
                    pass
            
            # 3. Fallback: gerar descrição básica
            if not descricao:
                descricao_partes = []
                
                # Adicionar valor do aluguel se disponível
                if hasattr(cobranca, 'valor_aluguel') and cobranca.valor_aluguel:
                    valor_aluguel = cobranca.valor_aluguel
                    if hasattr(valor_aluguel, 'amount'):
                        valor_aluguel = valor_aluguel.amount
                    valor_aluguel_formatado = f"R$ {float(valor_aluguel):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                    descricao_partes.append(f"Aluguel: {valor_aluguel_formatado}")
                
                # Adicionar outras despesas se disponíveis
                campos_despesas = [
                    ('valor_condominio', 'Condomínio'),
                    ('valor_iptu', 'IPTU'),
                    ('valor_agua', 'Água'),
                    ('valor_luz', 'Luz'),
                    ('valor_gas', 'Gás'),
                    ('valor_internet', 'Internet'),
                    ('valor_seguro', 'Seguro'),
                    ('valor_taxa', 'Taxa'),
                    ('valor_multa', 'Multa'),
                    ('valor_juros', 'Juros'),
                    ('valor_desconto', 'Desconto'),
                    ('valor_ajuste', 'Ajuste')
                ]
                
                for campo, label in campos_despesas:
                    if hasattr(cobranca, campo):
                        valor = getattr(cobranca, campo)
                        if valor and valor > 0:
                            if hasattr(valor, 'amount'):
                                valor = valor.amount
                            valor_formatado = f"R$ {float(valor):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                            descricao_partes.append(f"{label}: {valor_formatado}")
                
                if descricao_partes:
                    descricao = '\n'.join(descricao_partes)
            
            # Adicionar descrição se houver
            if descricao:
                mensagem_partes.extend(["", descricao])
            
            # Adicionar informações de pagamento se disponíveis e cobrança integrada
            if hasattr(cobranca, 'integrada_asaas') and cobranca.integrada_asaas:
                
                # Link do boleto
                boleto_url = None
                campos_boleto = ['boleto_url', 'asaas_boleto_url', 'url_boleto', 'link_boleto']
                for campo in campos_boleto:
                    if hasattr(cobranca, campo):
                        url = getattr(cobranca, campo)
                        if url and ('http' in str(url) or 'www.' in str(url)):
                            boleto_url = str(url)
                            break
                
                if boleto_url:
                    mensagem_partes.extend([
                        "",
                        "🔗 Link do boleto:",
                        boleto_url
                    ])
                
                # Código de barras
                if hasattr(cobranca, 'codigo_barras') and cobranca.codigo_barras:
                    mensagem_partes.extend([
                        "",
                        "📊 Código de barras:",
                        cobranca.codigo_barras
                    ])
                
                # PIX
                pix_campos = ['pix_copia_cola', 'pix_codigo', 'asaas_pix']
                for campo in pix_campos:
                    if hasattr(cobranca, campo):
                        pix = getattr(cobranca, campo)
                        if pix:
                            mensagem_partes.extend([
                                "",
                                "💳 PIX (copiar e colar):",
                                str(pix)
                            ])
                            break

            return '\n'.join(mensagem_partes)
            
        except Exception as e:
            # Em caso de erro, retornar None para usar fallback
            print(f"Erro ao gerar mensagem WhatsApp: {e}")
            return None
        
    @staticmethod
    def listar_cobrancas_ordenadas(filtros=None):
        """Lista cobranças com filtros opcionais"""
        queryset = Cobranca.objects.select_related(
            'contrato', 'inquilino'
        ).prefetch_related(
            'contrato__despesas'
        )
        
        if filtros:
            if filtros.get('contrato_id'):
                queryset = queryset.filter(contrato_id=filtros['contrato_id'])
            
            if filtros.get('status'):
                queryset = queryset.filter(status=filtros['status'])
            
            if filtros.get('mes_referencia'):
                queryset = queryset.filter(mes_referencia=filtros['mes_referencia'])
            
            if filtros.get('ano_referencia'):
                queryset = queryset.filter(ano_referencia=filtros['ano_referencia'])
            
            if filtros.get('atrasadas_apenas'):
                queryset = queryset.filter(
                    status__in=['pendente', 'atrasada'],
                    data_vencimento__lt=timezone.now().date()
                )
        
        return queryset.order_by('-ano_referencia', '-mes_referencia', 'data_vencimento')
    
    @staticmethod
    def marcar_cobranca_como_paga(cobranca_id, data_pagamento=None):
        """Marca cobrança como paga"""
        cobranca = get_object_or_404(Cobranca, pk=cobranca_id)
        
        if not data_pagamento:
            data_pagamento = timezone.now().date()
        
        cobranca.marcar_como_paga(data_pagamento)
        return cobranca
    
    @staticmethod
    def obter_detalhes_cobranca(cobranca_id):
        """Obtém detalhes completos de uma cobrança"""
        cobranca = get_object_or_404(
            Cobranca.objects.select_related('contrato', 'inquilino'),
            pk=cobranca_id
        )
        
        # Buscar lembretes enviados (assumindo que existe um modelo de Lembrete)
        lembretes = []
        try:
            Lembrete = apps.get_model('financeiro', 'Lembrete')
            lembretes = Lembrete.objects.filter(
                cobranca=cobranca
            ).order_by('-data_envio')
        except:
            pass  # Modelo não existe ainda
        
        return cobranca, lembretes
    
    @staticmethod
    def obter_estatisticas_cobrancas(mes=None, ano=None):
        """Obtém estatísticas das cobranças"""
        queryset = Cobranca.objects.all()
        
        if mes and ano:
            queryset = queryset.filter(mes_referencia=mes, ano_referencia=ano)
        elif ano:
            queryset = queryset.filter(ano_referencia=ano)
        
        # Calcular estatísticas
        total_cobrancas = queryset.count()
        total_pagas = queryset.filter(status='paga').count()
        total_pendentes = queryset.filter(status='pendente').count()
        total_atrasadas = queryset.filter(status='atrasada').count()
        
        valor_total = sum(c.valor_total for c in queryset)
        valor_recebido = sum(c.valor_total for c in queryset.filter(status='paga'))
        valor_pendente = sum(c.valor_total for c in queryset.filter(status__in=['pendente', 'atrasada']))
        
        return {
            'total_cobrancas': total_cobrancas,
            'total_pagas': total_pagas,
            'total_pendentes': total_pendentes,
            'total_atrasadas': total_atrasadas,
            'percentual_pagamento': (total_pagas / total_cobrancas * 100) if total_cobrancas > 0 else 0,
            'valor_total': valor_total,
            'valor_recebido': valor_recebido,
            'valor_pendente': valor_pendente,
            'percentual_recebimento': (valor_recebido / valor_total * 100) if valor_total > 0 else 0
        }
    
    @staticmethod
    def processar_webhook_asaas(dados_webhook):
        """Processa webhook do Asaas para atualização de status"""
        try:
            asaas_id = dados_webhook.get('payment', {}).get('id')
            if not asaas_id:
                return {'status': 'error', 'message': 'ID do pagamento não encontrado'}
            
            cobranca = Cobranca.objects.filter(asaas_id=asaas_id).first()
            if not cobranca:
                return {'status': 'error', 'message': 'Cobrança não encontrada'}
            
            evento = dados_webhook.get('event')
            
            if evento == 'PAYMENT_RECEIVED':
                data_pagamento = dados_webhook.get('payment', {}).get('dateReceived')
                if data_pagamento:
                    data_pagamento = datetime.datetime.strptime(data_pagamento, '%Y-%m-%d').date()
                cobranca.marcar_como_paga(data_pagamento)
                
            elif evento == 'PAYMENT_OVERDUE':
                cobranca.status = 'atrasada'
                cobranca.save(update_fields=['status'])
            
            # Atualizar status do gateway
            gateway_status = dados_webhook.get('payment', {}).get('status')
            if gateway_status and cobranca.gateway_status != gateway_status:
                cobranca.gateway_status = gateway_status
                cobranca.save(update_fields=['gateway_status'])
            
            return {'status': 'success', 'message': 'Webhook processado com sucesso'}
            
        except Exception as e:
            return {'status': 'error', 'message': f'Erro ao processar webhook: {str(e)}'}


# Funções auxiliares para manter compatibilidade com código existente
def gerar_cobrancas_manualmente(ids_contratos, mes, ano):
    """Função de compatibilidade - usar CobrancaService.criar_cobrancas_em_lote"""
    mes = int(mes)
    ano = int(ano)
    
    cobrancas_data = []
    for contrato_id in ids_contratos:
        try:
            contrato = get_object_or_404(Contrato, id=contrato_id)
            preview = CobrancaService.criar_cobranca_preview(contrato, mes, ano)
            cobrancas_data.append(preview)
        except:
            continue
    
    cobrancas_criadas, erros = CobrancaService.criar_cobrancas_em_lote(cobrancas_data)
    return len(cobrancas_criadas)

def listar_cobrancas_sugeridas(mes, ano, contrato_id=None):
    """Função de compatibilidade"""
    return CobrancaService.listar_cobrancas_sugeridas(mes, ano, contrato_id)

def integrar_cobranca_asaas(cobranca):
    """Função de compatibilidade"""
    return CobrancaService.integrar_cobranca_asaas(cobranca)

def gerar_mensagem_cobranca(cobranca):
    """Função de compatibilidade"""
    return CobrancaService.gerar_mensagem_whatsapp(cobranca)

def listar_cobrancas_ordenadas():
    """Função de compatibilidade"""
    return CobrancaService.listar_cobrancas_ordenadas()

def marcar_cobranca_como_paga(cobranca_id, data_pagamento):
    """Função de compatibilidade"""
    return CobrancaService.marcar_cobranca_como_paga(cobranca_id, data_pagamento)