# financeiro/mixins/asaas_mixin.py
# Mixin para adicionar funcionalidades de integração Asaas

from django.utils import timezone
from datetime import date
import logging

logger = logging.getLogger(__name__)


class AsaasIntegracaoMixin:
    """
    Mixin para adicionar métodos de integração Asaas ao modelo AsaasIntegracao
    """
    
    def pode_ser_integrada(self):
        """
        Verifica se a cobrança pode ser integrada com o Asaas
        
        Returns:
            tuple: (pode_integrar: bool, erros: list)
        """
        erros = []
        
        # Verificar se já foi integrada
        if self.asaas_id:
            erros.append("Cobrança já foi integrada com o Asaas")
        
        # Verificar se cobrança existe
        if not self.cobranca:
            erros.append("Integração não possui cobrança associada")
            return False, erros
        
        # Verificar status da cobrança
        if self.cobranca.status not in ['pendente', 'rascunho']:
            erros.append(f"Status da cobrança deve ser 'pendente' ou 'rascunho', atual: {self.cobranca.status}")
        
        # Verificar valor da cobrança
        if not self.cobranca.valor or self.cobranca.valor <= 0:
            erros.append("Valor da cobrança deve ser maior que zero")
        
        # Verificar data de vencimento
        if not self.cobranca.data_vencimento:
            erros.append("Cobrança deve ter data de vencimento")
        elif self.cobranca.data_vencimento < date.today():
            erros.append("Data de vencimento não pode ser anterior a hoje")
        
        # Verificar dados do contrato e cliente
        if not self.cobranca.contrato:
            erros.append("Cobrança deve ter contrato associado")
        else:
            contrato = self.cobranca.contrato
            
            # Verificar se tem inquilino
            if not contrato.inquilino.exists():
                erros.append("Contrato deve ter inquilino cadastrado")
            else:
                inquilino = contrato.inquilino.first()
                
                # Verificar dados obrigatórios do cliente
                if not getattr(inquilino, 'nome', None) and not getattr(inquilino, 'razao_social', None):
                    erros.append("Cliente deve ter nome ou razão social")
                
                if not getattr(inquilino, 'email', None):
                    erros.append("Cliente deve ter email cadastrado")
                
                cpf = getattr(inquilino, 'CPF', None)
                cnpj = getattr(inquilino, 'cnpj', None)
                if not cpf and not cnpj:
                    erros.append("Cliente deve ter CPF ou CNPJ cadastrado")
        
        return len(erros) == 0, erros
    
    def integrar_asaas(self, opcoes=None):
        """
        Integra a cobrança com o Asaas
        
        Args:
            opcoes (dict): Opções de integração
                - formas_pagamento (list): ['BOLETO', 'PIX', 'CREDIT_CARD']
                - enviar_por_email (bool): Enviar boleto por email
                - enviar_por_whatsapp (bool): Enviar por WhatsApp
                - observacoes (str): Observações adicionais
        
        Returns:
            dict: Resultado da integração
        """
        opcoes = opcoes or {}
        
        try:
            # Verificar se pode ser integrada
            pode_integrar, erros = self.pode_ser_integrada()
            if not pode_integrar:
                logger.warning(f"Integração {self.id} não pode ser processada: {erros}")
                return {
                    'success': False,
                    'errors': erros
                }
            
            # Importar serviço
            from financeiro.services.asaas_service import AsaasService
            service = AsaasService()
            
            logger.info(f"Iniciando integração da cobrança {self.cobranca.id} com Asaas")
            
            # 1. Criar/atualizar cliente no Asaas
            resultado_cliente = self._criar_atualizar_cliente_asaas(service)
            if not resultado_cliente['success']:
                return resultado_cliente
            
            cliente_asaas_id = resultado_cliente['cliente_id']
            logger.info(f"Cliente Asaas: {cliente_asaas_id}")
            
            # 2. Criar cobrança no Asaas
            resultado_cobranca = self._criar_cobranca_asaas(service, cliente_asaas_id, opcoes)
            if not resultado_cobranca['success']:
                return resultado_cobranca
            
            # 3. Salvar dados da integração
            payment_data = resultado_cobranca['data']
            self.asaas_id = payment_data['id']
            self.gateway_status = payment_data['status']
            self.boleto_url = payment_data.get('bankSlipUrl')
            self.data_ultima_atualizacao = timezone.now()
            
            # Dados PIX (se disponível)
            pix_transaction = payment_data.get('pixTransaction')
            if pix_transaction:
                self.pix_copia_cola = pix_transaction.get('qrCode')
                self.pix_qrcode = pix_transaction.get('qrCodeImage')
                self.pix_url = pix_transaction.get('qrCodeUrl')
            
            self.save()
            
            # 4. Atualizar status da cobrança local se necessário
            if self.cobranca.status == 'rascunho':
                self.cobranca.status = 'pendente'
                self.cobranca.save()
            
            logger.info(f"Integração concluída - Asaas ID: {self.asaas_id}")
            
            return {
                'success': True,
                'asaas_id': self.asaas_id,
                'status': self.gateway_status,
                'boleto_url': self.boleto_url,
                'pix_copia_cola': self.pix_copia_cola,
                'valor': payment_data.get('value'),
                'vencimento': payment_data.get('dueDate')
            }
            
        except Exception as e:
            logger.error(f"Erro na integração da cobrança {self.cobranca.id}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _criar_atualizar_cliente_asaas(self, service):
        """Cria ou atualiza cliente no Asaas"""
        try:
            contrato = self.cobranca.contrato
            inquilino = contrato.inquilino.first()
            
            # Preparar dados do cliente
            dados_cliente = {
                'name': getattr(inquilino, 'nome', None) or getattr(inquilino, 'razao_social', ''),
                'email': getattr(inquilino, 'email', ''),
                'cpfCnpj': getattr(inquilino, 'CPF', None) or getattr(inquilino, 'cnpj', ''),
                'phone': getattr(inquilino, 'telefone', ''),
                'mobilePhone': getattr(inquilino, 'celular', ''),
                'externalReference': str(inquilino.id)
            }
            
            # Dados do endereço (se disponível)
            if hasattr(contrato, 'imovel') and contrato.imovel:
                imovel = contrato.imovel
                dados_cliente.update({
                    'address': getattr(imovel, 'endereco', ''),
                    'addressNumber': getattr(imovel, 'numero', ''),
                    'complement': getattr(imovel, 'complemento', ''),
                    'province': getattr(imovel, 'bairro', ''),
                    'postalCode': getattr(imovel, 'cep', '').replace('-', ''),
                    'cityName': getattr(imovel, 'cidade', ''),
                    'state': getattr(imovel, 'estado', '')
                })
            
            # Criar/atualizar cliente
            response = service.criar_cliente(dados_cliente)
            
            return {
                'success': True,
                'cliente_id': response['id'],
                'cliente_data': response
            }
            
        except Exception as e:
            logger.error(f"Erro ao criar cliente no Asaas: {str(e)}")
            return {
                'success': False,
                'error': f"Erro ao criar/atualizar cliente: {str(e)}"
            }
    
    def _criar_cobranca_asaas(self, service, cliente_id, opcoes):
        """Cria cobrança no Asaas"""
        try:
            cobranca = self.cobranca
            
            # Determinar tipo de cobrança
            formas_pagamento = opcoes.get('formas_pagamento', ['BOLETO'])
            billing_type = formas_pagamento[0] if formas_pagamento else 'BOLETO'
            
            # Preparar dados da cobrança
            dados_cobranca = {
                'customer': cliente_id,
                'billingType': billing_type,
                'value': float(cobranca.valor),
                'dueDate': cobranca.data_vencimento.strftime('%Y-%m-%d'),
                'description': cobranca.descricao or f"Cobrança #{cobranca.id}",
                'externalReference': str(cobranca.id),
                'installmentCount': 1,
                'installmentValue': float(cobranca.valor)
            }
            
            # Configurações de notificação
            if opcoes.get('enviar_por_email', True):
                dados_cobranca['postalService'] = False  # Não enviar boleto pelos correios
            
            # Observações adicionais
            if opcoes.get('observacoes'):
                dados_cobranca['notes'] = opcoes['observacoes']
            
            # Criar cobrança
            response = service.criar_cobranca(dados_cobranca)
            
            return {
                'success': True,
                'data': response
            }
            
        except Exception as e:
            logger.error(f"Erro ao criar cobrança no Asaas: {str(e)}")
            return {
                'success': False,
                'error': f"Erro ao criar cobrança: {str(e)}"
            }
    
    def processar_webhook(self, dados_webhook):
        """
        Processa webhook recebido do Asaas
        
        Args:
            dados_webhook (dict): Dados do webhook recebido
        
        Returns:
            dict: Resultado do processamento
        """
        try:
            # Validar estrutura do webhook
            if 'event' not in dados_webhook or 'payment' not in dados_webhook:
                return {
                    'success': False,
                    'error': 'Webhook inválido - campos obrigatórios ausentes'
                }
            
            event = dados_webhook['event']
            payment_data = dados_webhook['payment']
            
            logger.info(f"Processando webhook - Event: {event}, Payment: {payment_data.get('id')}")
            
            # Verificar se é a cobrança correta
            if payment_data.get('id') != self.asaas_id:
                return {
                    'success': False,
                    'error': 'Webhook não corresponde a esta integração'
                }
            
            # Atualizar dados da integração
            status_anterior = self.gateway_status
            self.gateway_status = payment_data.get('status')
            self.data_ultima_atualizacao = timezone.now()
            
            # Atualizar URLs se disponível
            if payment_data.get('bankSlipUrl'):
                self.boleto_url = payment_data['bankSlipUrl']
            
            # Atualizar dados PIX se disponível
            pix_transaction = payment_data.get('pixTransaction')
            if pix_transaction:
                self.pix_copia_cola = pix_transaction.get('qrCode')
                self.pix_qrcode = pix_transaction.get('qrCodeImage')
            
            self.save()
            
            # Atualizar status da cobrança local baseado no status do Asaas
            if self.gateway_status in ['CONFIRMED', 'RECEIVED'] and self.cobranca.status != 'paga':
                self.cobranca.status = 'paga'
                self.cobranca.data_pagamento = timezone.now().date()
                self.cobranca.save()
                logger.info(f"Cobrança {self.cobranca.id} marcada como paga")
            
            elif self.gateway_status == 'OVERDUE' and self.cobranca.status == 'pendente':
                self.cobranca.status = 'atrasada'
                self.cobranca.save()
                logger.info(f"Cobrança {self.cobranca.id} marcada como atrasada")
            
            logger.info(f"Webhook processado - Status: {status_anterior} -> {self.gateway_status}")
            
            return {
                'success': True,
                'event': event,
                'status_anterior': status_anterior,
                'status_atual': self.gateway_status,
                'cobranca_id': self.cobranca.id
            }
            
        except Exception as e:
            logger.error(f"Erro ao processar webhook: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def cancelar_integracao(self):
        """
        Cancela a integração com o Asaas
        """
        try:
            if not self.asaas_id:
                return {
                    'success': False,
                    'error': 'Integração não possui ID do Asaas'
                }
            
            # Importar serviço
            from financeiro.services.asaas_service import AsaasService
            service = AsaasService()
            
            # Cancelar no Asaas
            response = service.cancelar_cobranca(self.asaas_id)
            
            # Atualizar status local
            self.gateway_status = 'DELETED'
            self.data_ultima_atualizacao = timezone.now()
            self.save()
            
            # Atualizar cobrança local
            if self.cobranca.status not in ['paga', 'cancelada']:
                self.cobranca.status = 'cancelada'
                self.cobranca.save()
            
            logger.info(f"Integração {self.id} cancelada no Asaas")
            
            return {
                'success': True,
                'asaas_response': response
            }
            
        except Exception as e:
            logger.error(f"Erro ao cancelar integração: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def atualizar_status_asaas(self):
        """
        Consulta e atualiza o status atual no Asaas
        """
        try:
            if not self.asaas_id:
                return {
                    'success': False,
                    'error': 'Integração não possui ID do Asaas'
                }
            
            # Importar serviço
            from financeiro.services.asaas_service import AsaasService
            service = AsaasService()
            
            # Consultar status atual
            status_info = service.verificar_status_cobranca(self.asaas_id)
            
            # Atualizar dados locais
            status_anterior = self.gateway_status
            self.gateway_status = status_info['status']
            self.data_ultima_atualizacao = timezone.now()
            
            if status_info.get('bankSlipUrl'):
                self.boleto_url = status_info['bankSlipUrl']
            
            self.save()
            
            logger.info(f"Status atualizado: {status_anterior} -> {self.gateway_status}")
            
            return {
                'success': True,
                'status_anterior': status_anterior,
                'status_atual': self.gateway_status,
                'dados_completos': status_info
            }
            
        except Exception as e:
            logger.error(f"Erro ao atualizar status: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }