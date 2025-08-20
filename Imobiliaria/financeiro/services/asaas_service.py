# financeiro/services/asaas_service.py
# Versão atualizada com suporte a sandbox e produção

import requests
from django.conf import settings
import logging


logger = logging.getLogger(__name__)

class AsaasService:
    """
    Serviço para integração com API do Asaas
    Suporta ambientes sandbox e produção
    """
    
    def __init__(self):
        # Configurações básicas
        self.api_key = getattr(settings, 'ASAAS_API_KEY', '')
        self.environment = getattr(settings, 'ASAAS_ENVIRONMENT', 'sandbox')
        
        # URLs baseadas no ambiente
        if self.environment == 'production':
            self.base_url = 'https://www.asaas.com/api/v3/'
        else:
            self.base_url = 'https://sandbox.asaas.com/api/v3/'
        
        # Headers para requisições
        self.headers = {
            'Content-Type': 'application/json',
            'access_token': self.api_key
        }
        
        # Validar configuração
        if not self.api_key:
            raise ValueError("ASAAS_API_KEY não configurada")
        
        # Log do ambiente sendo usado
        logger.info(f"AsaasService inicializado - Ambiente: {self.environment}")
        logger.info(f"Base URL: {self.base_url}")
    
    def _fazer_requisicao(self, method, endpoint, params=None, data=None, timeout=30):
        """
        Faz requisição para API do Asaas com tratamento de erros
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method.upper() == 'GET':
                response = requests.get(
                    url, 
                    headers=self.headers, 
                    params=params,
                    timeout=timeout
                )
            elif method.upper() == 'POST':
                response = requests.post(
                    url, 
                    headers=self.headers, 
                    json=data,
                    timeout=timeout
                )
            elif method.upper() == 'PUT':
                response = requests.put(
                    url, 
                    headers=self.headers, 
                    json=data,
                    timeout=timeout
                )
            elif method.upper() == 'DELETE':
                response = requests.delete(
                    url, 
                    headers=self.headers,
                    timeout=timeout
                )
            else:
                raise ValueError(f"Método HTTP não suportado: {method}")
            
            # Log da requisição
            logger.debug(f"{method} {url} - Status: {response.status_code}")
            
            # Verificar se a requisição foi bem-sucedida
            response.raise_for_status()
            
            # Retornar JSON se houver conteúdo
            if response.content:
                return response.json()
            else:
                return {}
                
        except requests.exceptions.Timeout:
            logger.error(f"Timeout na requisição para {url}")
            raise Exception("Timeout na comunicação com Asaas")
        
        except requests.exceptions.ConnectionError:
            logger.error(f"Erro de conexão para {url}")
            raise Exception("Erro de conexão com Asaas")
        
        except requests.exceptions.HTTPError as e:
            logger.error(f"Erro HTTP {response.status_code} para {url}: {response.text}")
            
            # Tratar erros específicos do Asaas
            if response.status_code == 401:
                raise Exception("API Key inválida ou expirada")
            elif response.status_code == 403:
                raise Exception("Acesso negado - verifique permissões da API Key")
            elif response.status_code == 429:
                raise Exception("Limite de requisições excedido")
            elif response.status_code >= 500:
                raise Exception("Erro interno do servidor Asaas")
            else:
                raise Exception(f"Erro na API Asaas: {response.status_code}")
        
        except Exception as e:
            logger.error(f"Erro inesperado na requisição para {url}: {str(e)}")
            raise
    
    def testar_conexao(self):
        """
        Testa a conexão com a API do Asaas
        """
        try:
            # Fazer uma requisição simples para testar
            response = self._fazer_requisicao('GET', 'customers', params={'limit': 1})
            
            return {
                'sucesso': True,
                'ambiente': self.environment,
                'url': self.base_url,
                'total_clientes': response.get('totalCount', 0),
                'mensagem': f'Conexão OK - Ambiente: {self.environment}'
            }
            
        except Exception as e:
            return {
                'sucesso': False,
                'ambiente': self.environment,
                'url': self.base_url,
                'erro': str(e),
                'mensagem': f'Falha na conexão - Ambiente: {self.environment}'
            }
    
    def buscar_cobrancas(self, data_inicio=None, data_fim=None, status=None, customer_id=None, limit=100, offset=0):
        """
        Busca cobranças no Asaas com filtros
        """
        params = {
            'limit': limit,
            'offset': offset
        }
        
        if data_inicio:
            params['dateCreated[ge]'] = data_inicio.strftime('%Y-%m-%d')
        if data_fim:
            params['dateCreated[le]'] = data_fim.strftime('%Y-%m-%d')
        if status:
            params['status'] = status
        if customer_id:
            params['customer'] = customer_id
        
        return self._fazer_requisicao('GET', 'payments', params=params)
    
    def buscar_cliente(self, customer_id):
        """
        Busca um cliente específico no Asaas
        """
        return self._fazer_requisicao('GET', f'customers/{customer_id}')
    
    def buscar_cobranca(self, payment_id):
        """
        Busca uma cobrança específica no Asaas
        """
        return self._fazer_requisicao('GET', f'payments/{payment_id}')
    
    def criar_cliente(self, dados_cliente):
        """
        Cria ou atualiza cliente no Asaas
        """
        # Verificar se cliente já existe por CPF/CNPJ
        cpf_cnpj = dados_cliente.get('cpfCnpj')
        if cpf_cnpj:
            try:
                # Buscar cliente existente
                response = self._fazer_requisicao('GET', 'customers', params={'cpfCnpj': cpf_cnpj})
                
                if response.get('data') and len(response['data']) > 0:
                    # Cliente existe, fazer update
                    cliente_id = response['data'][0]['id']
                    logger.info(f"Cliente existente encontrado: {cliente_id}")
                    return self._fazer_requisicao('PUT', f'customers/{cliente_id}', data=dados_cliente)
            except Exception as e:
                logger.warning(f"Erro ao buscar cliente existente: {e}")
                # Continuar para criar novo cliente
        
        # Cliente não existe, criar novo
        logger.info("Criando novo cliente")
        return self._fazer_requisicao('POST', 'customers', data=dados_cliente)
    
    def criar_cobranca(self, dados_cobranca):
        """
        Cria cobrança no Asaas
        """
        logger.info(f"Criando cobrança - Valor: {dados_cobranca.get('value')}")
        return self._fazer_requisicao('POST', 'payments', data=dados_cobranca)
    
    def cancelar_cobranca(self, payment_id):
        """
        Cancela uma cobrança no Asaas
        """
        logger.info(f"Cancelando cobrança: {payment_id}")
        return self._fazer_requisicao('DELETE', f'payments/{payment_id}')
    
    def gerar_boleto_url(self, payment_id):
        """
        Gera URL do boleto para uma cobrança
        """
        base_url = self.base_url.replace('/api/v3/', '')
        return f"{base_url}/b/pdf/{payment_id}"
    
    def gerar_pix_qrcode(self, payment_id):
        """
        Gera QR Code PIX para uma cobrança
        """
        logger.info(f"Gerando PIX QR Code para: {payment_id}")
        return self._fazer_requisicao('GET', f'payments/{payment_id}/pixQrCode')
    
    def atualizar_cobranca(self, payment_id, dados_atualizacao):
        """
        Atualiza uma cobrança existente
        """
        logger.info(f"Atualizando cobrança: {payment_id}")
        return self._fazer_requisicao('PUT', f'payments/{payment_id}', data=dados_atualizacao)
    
    def listar_cobrancas_cliente(self, customer_id, limit=50, offset=0):
        """
        Lista todas as cobranças de um cliente
        """
        params = {
            'customer': customer_id,
            'limit': limit,
            'offset': offset
        }
        return self._fazer_requisicao('GET', 'payments', params=params)
    
    def verificar_status_cobranca(self, payment_id):
        """
        Verifica o status atual de uma cobrança
        """
        response = self._fazer_requisicao('GET', f'payments/{payment_id}')
        return {
            'id': response.get('id'),
            'status': response.get('status'),
            'value': response.get('value'),
            'dueDate': response.get('dueDate'),
            'customer': response.get('customer'),
            'bankSlipUrl': response.get('bankSlipUrl'),
            'invoiceUrl': response.get('invoiceUrl')
        }
    
    def processar_webhook_pagamento(self, dados_webhook):
        """
        Processa webhook de pagamento recebido do Asaas
        """
        event = dados_webhook.get('event')
        payment = dados_webhook.get('payment', {})
        
        logger.info(f"Processando webhook - Event: {event}, Payment: {payment.get('id')}")
        
        return {
            'event': event,
            'payment_id': payment.get('id'),
            'status': payment.get('status'),
            'value': payment.get('value'),
            'customer': payment.get('customer'),
            'external_reference': payment.get('externalReference')
        }


    def verificar_configuracao_asaas():
        """
        Função utilitária para verificar configurações do Asaas
        """
        from django.conf import settings
        
        configuracoes = {
            'ASAAS_API_KEY': getattr(settings, 'ASAAS_API_KEY', None),
            'ASAAS_ENVIRONMENT': getattr(settings, 'ASAAS_ENVIRONMENT', 'sandbox'),
        }
        
        # Validações
        erros = []
        
        if not configuracoes['ASAAS_API_KEY']:
            erros.append("ASAAS_API_KEY não configurada")
        
        if configuracoes['ASAAS_ENVIRONMENT'] not in ['sandbox', 'production']:
            erros.append("ASAAS_ENVIRONMENT deve ser 'sandbox' ou 'production'")
        
        return {
            'valido': len(erros) == 0,
            'erros': erros,
            'configuracoes': configuracoes
        }

    def buscar_codigo_barras(self, payment_id):
        """
        Busca o código de barras de uma cobrança
        """
        logger.info(f"Buscando código de barras para: {payment_id}")
        
        try:
            # Endpoint para buscar código de barras
            response = self._fazer_requisicao('GET', f'payments/{payment_id}/identificationField')
            
            # O Asaas retorna o campo 'identificationField' que é o código de barras
            codigo_barras = response.get('identificationField')
            
            if codigo_barras:
                logger.info(f"Código de barras encontrado: {codigo_barras[:20]}...")
                return codigo_barras
            else:
                logger.warning(f"Código de barras não disponível para {payment_id}")
                return None
                
        except Exception as e:
            logger.error(f"Erro ao buscar código de barras para {payment_id}: {str(e)}")
            return None

    def buscar_pix_copia_cola_detalhado(self, payment_id):
        """
        Busca informações detalhadas do PIX (copia e cola + QR code)
        """
        logger.info(f"Buscando PIX detalhado para: {payment_id}")
        
        try:
            # Usar o endpoint existente
            response = self._fazer_requisicao('GET', f'payments/{payment_id}/pixQrCode')
            
            # Extrair informações do PIX
            resultado = {
                'pix_copia_cola': None,
                'qr_code': None,
                'qr_code_image': None,
                'success': False
            }
            
            if response:
                # O Asaas pode retornar diferentes formatos
                resultado['pix_copia_cola'] = (
                    response.get('payload') or
                    response.get('qrCode') or 
                    response.get('copyAndPaste') or
                    response.get('brCode')
                )
                
                resultado['qr_code'] = response.get('qrCode')
                resultado['qr_code_image'] = response.get('encodedImage')
                resultado['success'] = bool(resultado['pix_copia_cola'])
                
                if resultado['pix_copia_cola']:
                    logger.info(f"PIX copia e cola encontrado: {resultado['pix_copia_cola'][:50]}...")
                else:
                    logger.warning(f"PIX copia e cola não disponível para {payment_id}")
            
            return resultado
            
        except Exception as e:
            logger.error(f"Erro ao buscar PIX para {payment_id}: {str(e)}")
            return {
                'pix_copia_cola': None,
                'qr_code': None,
                'qr_code_image': None,
                'success': False,
                'error': str(e)
            }

    def atualizar_dados_pagamento_completos(self, payment_id):
        """
        Busca todos os dados de um pagamento: informações básicas, código de barras e PIX
        """
        logger.info(f"Atualizando dados completos para: {payment_id}")
        
        dados_completos = {
            'payment_id': payment_id,
            'cobranca': None,
            'codigo_barras': None,
            'pix_dados': None,
            'boleto_url': None,
            'status': None,
            'valor': None,
            'vencimento': None,
            'success': True,
            'erros': []
        }
        
        try:
            # 1. Buscar dados básicos da cobrança
            cobranca_dados = self.buscar_cobranca(payment_id)
            if cobranca_dados:
                dados_completos['cobranca'] = cobranca_dados
                dados_completos['status'] = cobranca_dados.get('status')
                dados_completos['valor'] = cobranca_dados.get('value')
                dados_completos['vencimento'] = cobranca_dados.get('dueDate')
                dados_completos['boleto_url'] = (
                    cobranca_dados.get('bankSlipUrl') or 
                    cobranca_dados.get('invoiceUrl') or
                    self.gerar_boleto_url(payment_id)
                )
            else:
                dados_completos['erros'].append("Não foi possível buscar dados da cobrança")
                dados_completos['success'] = False
            
            # 2. Buscar código de barras
            codigo_barras = self.buscar_codigo_barras(payment_id)
            if codigo_barras:
                dados_completos['codigo_barras'] = codigo_barras
            else:
                dados_completos['erros'].append("Código de barras não disponível")
            
            # 3. Buscar dados do PIX
            pix_dados = self.buscar_pix_copia_cola_detalhado(payment_id)
            if pix_dados['success']:
                dados_completos['pix_dados'] = pix_dados
            else:
                dados_completos['erros'].append("PIX não disponível")
            
            logger.info(f"Dados completos coletados para {payment_id} - Erros: {len(dados_completos['erros'])}")
            
        except Exception as e:
            logger.error(f"Erro ao coletar dados completos para {payment_id}: {str(e)}")
            dados_completos['success'] = False
            dados_completos['erros'].append(f"Erro geral: {str(e)}")
        
        return dados_completos
