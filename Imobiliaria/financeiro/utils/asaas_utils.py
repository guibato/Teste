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
            
            # Atualizar status se disponível
            if dados.get('status'):
                integracao.gateway_status = dados['status']
            
            # Atualizar URL do boleto se disponível
            if dados.get('boleto_url'):
                integracao.boleto_url = dados['boleto_url']
            
            # Atualizar PIX se disponível
            if dados.get('pix_dados') and dados['pix_dados']['success']:
                pix_dados = dados['pix_dados']
                if pix_dados.get('pix_copia_cola'):
                    integracao.pix_copia_cola = pix_dados['pix_copia_cola']
                if pix_dados.get('qr_code'):
                    integracao.pix_qrcode = pix_dados['qr_code']
            
            # Salvar as atualizações
            integracao.save()
            
            logger.info(f"Integração Asaas atualizada com sucesso para cobrança {cobranca.pk}")
            
            return {
                'success': True,
                'dados_atualizados': {
                    'status': dados.get('status'),
                    'boleto_url': dados.get('boleto_url'),
                    'codigo_barras': dados.get('codigo_barras'),
                    'pix_disponivel': bool(dados.get('pix_dados', {}).get('pix_copia_cola')),
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
    
    # Verificar se tem integração Asaas
    if not hasattr(cobranca, 'asaas_integracao') or not cobranca.asaas_integracao.asaas_id:
        logger.info(f"Cobrança {cobranca.pk} não tem integração Asaas")
        return mensagem
    
    # Atualizar dados do Asaas se necessário
    try:
        resultado = atualizar_integracao_asaas_completa(cobranca)
        
        if resultado and resultado['success']:
            integracao = cobranca.asaas_integracao
            
            # Adicionar código de barras se disponível
            if resultado['dados_atualizados'].get('codigo_barras'):
                codigo = resultado['dados_atualizados']['codigo_barras']
                mensagem += f"\n\n📊 *Código de barras:*\n`{codigo}`"
            
            # Adicionar PIX se disponível
            if integracao.pix_copia_cola:
                mensagem += f"\n\n💰 *PIX Copia e Cola:*\n`{integracao.pix_copia_cola}`"
            
            logger.info(f"Mensagem enriquecida com dados Asaas para cobrança {cobranca.pk}")
        else:
            logger.warning(f"Não foi possível enriquecer mensagem com dados Asaas: {resultado.get('erros') if resultado else 'Erro desconhecido'}")
    
    except Exception as e:
        logger.error(f"Erro ao enriquecer mensagem com dados Asaas: {str(e)}")
    
    return mensagem