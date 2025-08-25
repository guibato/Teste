import logging
from django.utils import timezone

logger = logging.getLogger(__name__)

def atualizar_integracao_asaas_completa(cobranca):
    """
    Atualiza o modelo AsaasIntegracao com código de barras e PIX
    """
    from financeiro.services.asaas_service import AsaasService
    
    # Verificar se tem integração Asaas
    if not hasattr(cobranca, 'asaas_integracao') or not cobranca.asaas_integracao.asaas_id:
        logger.warning(f"Cobrança {cobranca.pk} não tem integração Asaas")
        return None
    
    asaas_id = cobranca.asaas_integracao.asaas_id
    logger.info(f"Atualizando integração Asaas para cobrança {cobranca.pk}, Asaas ID: {asaas_id}")
    
    try:
        # Inicializar serviço Asaas
        asaas_service = AsaasService()
        
        # Buscar dados completos
        dados = asaas_service.atualizar_dados_pagamento_completos(asaas_id)

        if dados['success']:
            # Atualizar modelo AsaasIntegracao
            integracao = cobranca.asaas_integracao

            # Atualizar códigos de barras
            integracao.codigo_barras = dados.get('codigo_barras')
            integracao.linha_digitavel = dados.get('linha_digitavel') or dados.get('codigo_barras')
            
            # Atualizar status se disponível
            if dados.get('status'):
                integracao.gateway_status = dados['status']

            # Atualizar URL do boleto se disponível
            if dados.get('boleto_url'):
                integracao.boleto_url = dados['boleto_url']

            # Atualizar PIX se disponível
            pix_dados = {}
            if dados.get('pix_dados') and dados['pix_dados']['success']:
                pix_dados = dados['pix_dados']
                if pix_dados.get('pix_copia_cola'):
                    integracao.pix_copia_cola = pix_dados['pix_copia_cola']
                if pix_dados.get('qr_code'):
                    integracao.pix_qrcode = pix_dados['qr_code']

            # Salvar as atualizações
            integracao.save(update_fields=['gateway_status', 'boleto_url', 'pix_copia_cola', 'pix_qrcode', 'codigo_barras', 'linha_digitavel'])

            logger.info(f"Integração Asaas atualizada com sucesso para cobrança {cobranca.pk}")

            return {
                'success': True,
                'dados_atualizados': {
                    'status': dados.get('status'),
                    'boleto_url': dados.get('boleto_url'),
                    'codigo_barras': dados.get('codigo_barras'),
                    'linha_digitavel': dados.get('linha_digitavel') or dados.get('codigo_barras'),
                    'pix_copia_cola': pix_dados.get('pix_copia_cola'),
                    'pix_qrcode': pix_dados.get('qr_code'),
                },
                'erros': dados.get('erros', [])
            }
        else:
            logger.error(f"Falha ao buscar dados do Asaas para {asaas_id}: {dados.get('erros')}")
            return {
                'success': False,
                'erros': dados.get('erros', ['Erro desconhecido'])
            }
            
    except Exception as e:
        logger.error(f"Erro ao atualizar integração Asaas para cobrança {cobranca.pk}: {str(e)}")
        return {
            'success': False,
            'erros': [f"Erro: {str(e)}"]
        }

def gerar_mensagem_cobranca_com_asaas(cobranca):
    """
    Gera mensagem de cobrança incluindo código de barras e PIX do Asaas
    """
    from financeiro.views.lembrete_views import gerar_mensagem_cobranca
    
    # Gerar mensagem base
    mensagem = gerar_mensagem_cobranca(cobranca)