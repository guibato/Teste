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


# ============================================================================
# COMANDO ATUALIZADO COM VALIDAÇÃO DE AMBIENTE
# ============================================================================

# Atualize o comando para incluir validação do ambiente:

def _verificar_configuracao_asaas(self):
    """Verifica se as configurações do Asaas estão corretas"""
    from django.conf import settings
    
    api_key = getattr(settings, 'ASAAS_API_KEY', None)
    environment = getattr(settings, 'ASAAS_ENVIRONMENT', 'sandbox')
    
    if not api_key:
        self.stdout.write(self.style.ERROR("❌ ASAAS_API_KEY não configurada!"))
        return False
    
    # Validar ambiente
    if environment not in ['sandbox', 'production']:
        self.stdout.write(self.style.ERROR("❌ ASAAS_ENVIRONMENT deve ser 'sandbox' ou 'production'"))
        return False
    
    # Mostrar ambiente atual
    if environment == 'production':
        self.stdout.write(self.style.WARNING("⚠️  ATENÇÃO: Executando em PRODUÇÃO!"))
        self.stdout.write("   Dados reais serão importados.")
        
        if not self.dry_run:
            resposta = input("   Confirma execução em PRODUÇÃO? (digite 'SIM' para confirmar): ")
            if resposta != 'SIM':
                self.stdout.write(self.style.ERROR("❌ Execução cancelada pelo usuário"))
                return False
    else:
        self.stdout.write(self.style.SUCCESS("✅ Executando em SANDBOX (ambiente de testes)"))
    
    # Testar conexão
    try:
        asaas_service = AsaasService()
        teste = asaas_service.testar_conexao()
        
        if teste['sucesso']:
            self.stdout.write(self.style.SUCCESS(f"✅ {teste['mensagem']}"))
            self.stdout.write(f"   Total de clientes: {teste.get('total_clientes', 0)}")
        else:
            self.stdout.write(self.style.ERROR(f"❌ {teste['mensagem']}"))
            self.stdout.write(f"   Erro: {teste['erro']}")
            return False
            
    except Exception as e:
        self.stdout.write(self.style.ERROR(f"❌ Erro ao testar conexão: {str(e)}"))
        return False
    
    return True