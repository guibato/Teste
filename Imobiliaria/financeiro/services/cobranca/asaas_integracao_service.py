from decimal import Decimal
import requests
from django.conf import settings


class AsaasIntegracaoService:
    """Service para integração com gateway Asaas"""
    
    @staticmethod
    def criar_cobranca(asaas_integracao, opcoes=None):
        """
        Cria cobrança no Asaas
        """
        try:
            from sisimob.utils.cobrancas_asaas import gerar_cobranca
            
            cobranca = asaas_integracao.cobranca
            opcoes = opcoes or {}
            
            # Verificar se inquilino tem ID do Asaas
            inquilino = cobranca.inquilino
            if not inquilino or not getattr(inquilino, 'asaas_id', None):
                return {
                    'status': 'error',
                    'erros': ['Inquilino não possui ID do Asaas cadastrado']
                }
            
            # Preparar dados da cobrança
            payload = {
                "customer": inquilino.asaas_id,
                "billingType": "BOLETO",  # Será sobrescrito pelas formas de pagamento
                "dueDate": cobranca.data_vencimento.strftime('%Y-%m-%d'),
                "value": float(cobranca.valor_total),
                "description": cobranca.descricao or cobranca.gerar_descricao_automatica(),
                "externalReference": f"cobranca_{cobranca.id}",
                "postalService": False
            }
            
            # Aplicar opções específicas
            if opcoes.get('formas_pagamento'):
                payload["billingType"] = opcoes['formas_pagamento'][0]  # Primeira forma como padrão
            
            if opcoes.get('observacoes'):
                payload["description"] += f"\n\n{opcoes['observacoes']}"
            
            # Fazer requisição para Asaas
            resposta = gerar_cobranca(cobranca)
            
            if resposta and isinstance(resposta, dict) and resposta.get('id'):
                # Salvar dados da integração
                asaas_integracao.asaas_id = resposta.get('id')
                asaas_integracao.boleto_url = resposta.get('bankSlipUrl')
                asaas_integracao.pix_copia_cola = resposta.get('pixCopiaeCola')
                asaas_integracao.pix_qrcode = resposta.get('pixQrCodeBase64')
                asaas_integracao.pix_url = resposta.get('pixUrl')
                asaas_integracao.codigo_barras = resposta.get('barCode')
                asaas_integracao.fatura_url = resposta.get('invoiceUrl')
                asaas_integracao.gateway_status = resposta.get('status')
                asaas_integracao.formas_pagamento = opcoes.get('formas_pagamento', ['BOLETO'])
                asaas_integracao.envio_email = opcoes.get('enviar_por_email', True)
                asaas_integracao.envio_whatsapp = opcoes.get('enviar_por_whatsapp', False)
                
                asaas_integracao.save()
                
                return {'status': 'success', 'data': resposta}
            else:
                return {'status': 'error', 'erros': ['Erro na integração com Asaas']}
                
        except Exception as e:
            return {'status': 'error', 'erros': [f'Erro inesperado: {str(e)}']}
    
    @staticmethod
    def processar_webhook(asaas_integracao, dados_webhook):
        """
        Processa webhook recebido do Asaas
        """
        try:
            from django.utils import timezone
            
            # Registrar webhook recebido
            asaas_integracao.webhooks_recebidos.append({
                'data': timezone.now().isoformat(),
                'evento': dados_webhook.get('event'),
                'dados': dados_webhook
            })
            
            cobranca = asaas_integracao.cobranca
            evento = dados_webhook.get('event')
            
            if evento == 'PAYMENT_RECEIVED':
                data_pagamento = dados_webhook.get('payment', {}).get('dateReceived')
                if data_pagamento:
                    from datetime import datetime
                    data_pagamento = datetime.strptime(data_pagamento, '%Y-%m-%d').date()
                else:
                    data_pagamento = timezone.now().date()
                
                cobranca.marcar_como_paga(data_pagamento)
                
            elif evento == 'PAYMENT_OVERDUE':
                cobranca.status = 'atrasada'
                cobranca.save(update_fields=['status'])
            
            # Atualizar status do gateway
            gateway_status = dados_webhook.get('payment', {}).get('status')
            if gateway_status and asaas_integracao.gateway_status != gateway_status:
                asaas_integracao.gateway_status = gateway_status
            
            asaas_integracao.save()
            
            return {'status': 'success', 'message': 'Webhook processado com sucesso'}
            
        except Exception as e:
            return {'status': 'error', 'message': f'Erro ao processar webhook: {str(e)}'}
    
    @staticmethod
    def integrar_cobrancas_lote(cobrancas_ids, opcoes):
        """
        Integra múltiplas cobranças em lote
        """
        from ..models import Cobranca, AsaasIntegracao
        
        cobrancas = Cobranca.objects.filter(id__in=cobrancas_ids)
        sucessos = []
        erros = []
        
        for cobranca in cobrancas:
            try:
                # Criar ou obter integração
                asaas_integracao, created = AsaasIntegracao.objects.get_or_create(
                    cobranca=cobranca
                )
                
                if asaas_integracao.asaas_id:
                    erros.append({
                        'cobranca_id': cobranca.id,
                        'erros': ['Cobrança já foi integrada']
                    })
                    continue
                
                resultado = AsaasIntegracaoService.criar_cobranca(asaas_integracao, opcoes)
                
                if resultado['status'] == 'success':
                    sucessos.append(cobranca)
                else:
                    erros.append({
                        'cobranca_id': cobranca.id,
                        'erros': resultado['erros']
                    })
                    
            except Exception as e:
                erros.append({
                    'cobranca_id': cobranca.id,
                    'erros': [f'Erro inesperado: {str(e)}']
                })
        
        return sucessos, erros