# financeiro/management/commands/sync_asaas_cobrancas.py
"""
Comando para sincronizar cobranças existentes no Asaas com o banco de dados local
VERSÃO ADAPTADA - Para estrutura com AsaasIntegracao
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from datetime import datetime, timedelta
import requests
from decimal import Decimal
import logging

# Importações adaptadas para sua estrutura
from financeiro.models.cobranca import Cobranca, AsaasIntegracao

# Tentar importar outros modelos
try:
    from core.models import Cliente, Contrato
except ImportError:
    try:
        from financeiro.models import Cliente, Contrato
    except ImportError:
        Cliente = None
        Contrato = None

# AsaasService básico se não existir
try:
    from financeiro.services.asaas_service import AsaasService
except ImportError:
    class AsaasService:
        def __init__(self):
            from django.conf import settings
            self.api_key = getattr(settings, 'ASAAS_API_KEY', '')
            self.base_url = 'https://www.asaas.com/api/v3/'
            self.headers = {
                'Content-Type': 'application/json',
                'access_token': self.api_key
            }
        
        def _fazer_requisicao(self, method, endpoint, params=None, data=None):
            import requests
            url = f"{self.base_url}{endpoint}"
            
            if method == 'GET':
                response = requests.get(url, headers=self.headers, params=params)
            elif method == 'POST':
                response = requests.post(url, headers=self.headers, json=data)
            
            response.raise_for_status()
            return response.json()

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Sincroniza cobranças existentes no Asaas com o banco de dados local'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--data-inicio',
            type=str,
            help='Data de início para buscar cobranças (YYYY-MM-DD). Padrão: 30 dias atrás'
        )
        parser.add_argument(
            '--data-fim',
            type=str,
            help='Data fim para buscar cobranças (YYYY-MM-DD). Padrão: hoje'
        )
        parser.add_argument(
            '--status',
            type=str,
            choices=['PENDING', 'RECEIVED', 'CONFIRMED', 'OVERDUE', 'REFUNDED', 'RECEIVED_IN_CASH'],
            help='Filtrar por status específico'
        )
        parser.add_argument(
            '--cliente-asaas-id',
            type=str,
            help='ID específico do cliente no Asaas'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Executar sem salvar no banco (apenas simulação)'
        )
        parser.add_argument(
            '--force-update',
            action='store_true',
            help='Forçar atualização de cobranças já existentes'
        )
        parser.add_argument(
            '--debug-models',
            action='store_true',
            help='Mostrar quais modelos foram encontrados'
        )

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.force_update = options['force_update']
        
        # Debug dos modelos disponíveis
        if options['debug_models']:
            self._debug_models()
            return
        
        # Verificar configurações
        if not self._verificar_configuracao_asaas():
            return
        
        # Configurar datas
        data_fim = datetime.strptime(options['data_fim'], '%Y-%m-%d').date() if options['data_fim'] else timezone.now().date()
        data_inicio = datetime.strptime(options['data_inicio'], '%Y-%m-%d').date() if options['data_inicio'] else data_fim - timedelta(days=30)
        
        self.stdout.write(f"🔄 Iniciando sincronização de cobranças do Asaas...")
        self.stdout.write(f"📅 Período: {data_inicio} até {data_fim}")
        
        if self.dry_run:
            self.stdout.write(self.style.WARNING("⚠️  MODO SIMULAÇÃO - Nenhuma alteração será salva"))
        
        try:
            asaas_service = AsaasService()
            
            # Buscar cobranças no Asaas
            cobrancas_asaas = self._buscar_cobrancas_asaas(
                asaas_service, 
                data_inicio, 
                data_fim, 
                options.get('status'),
                options.get('cliente_asaas_id')
            )
            
            self.stdout.write(f"📊 Encontradas {len(cobrancas_asaas)} cobranças no Asaas")
            
            if len(cobrancas_asaas) == 0:
                self.stdout.write(self.style.WARNING("⚠️  Nenhuma cobrança encontrada no período especificado"))
                return
            
            # Processar cada cobrança
            resultados = self._processar_cobrancas(cobrancas_asaas, asaas_service)
            
            # Exibir resultados
            self._exibir_relatorio(resultados)
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Erro durante sincronização: {str(e)}"))
            logger.error(f"Erro na sincronização Asaas: {str(e)}", exc_info=True)

    def _debug_models(self):
        """Mostra informações sobre os modelos encontrados"""
        self.stdout.write("🔍 DEBUG - Modelos encontrados:")
        self.stdout.write("=" * 50)
        
        # Verificar Cobranca
        self.stdout.write(f"✅ Cobranca: {Cobranca}")
        self.stdout.write(f"   Módulo: {Cobranca.__module__}")
        campos = [field.name for field in Cobranca._meta.fields]
        self.stdout.write(f"   Campos: {', '.join(campos[:10])}...")
        
        # Verificar AsaasIntegracao
        self.stdout.write(f"✅ AsaasIntegracao: {AsaasIntegracao}")
        self.stdout.write(f"   Módulo: {AsaasIntegracao.__module__}")
        
        # Verificar relação
        self.stdout.write("✅ Cobrança tem property asaas_id através de AsaasIntegracao")
        
        # Verificar Cliente e Contrato
        if Cliente:
            self.stdout.write(f"✅ Cliente: {Cliente}")
        else:
            self.stdout.write("❌ Cliente: Não encontrado")
        
        if Contrato:
            self.stdout.write(f"✅ Contrato: {Contrato}")
        else:
            self.stdout.write("❌ Contrato: Não encontrado")
        
        # Verificar configurações do Asaas
        self.stdout.write("\n🔧 Configurações Asaas:")
        from django.conf import settings
        api_key = getattr(settings, 'ASAAS_API_KEY', None)
        if api_key:
            self.stdout.write(f"   ✅ ASAAS_API_KEY: {'*' * (len(api_key) - 4) + api_key[-4:]}")
        else:
            self.stdout.write("   ❌ ASAAS_API_KEY: Não configurada")

    def _verificar_configuracao_asaas(self):
        """Verifica se as configurações do Asaas estão corretas"""
        from django.conf import settings
        
        api_key = getattr(settings, 'ASAAS_API_KEY', None)
        if not api_key:
            self.stdout.write(self.style.ERROR("❌ ASAAS_API_KEY não configurada!"))
            self.stdout.write("Adicione em settings.py:")
            self.stdout.write("ASAAS_API_KEY = os.getenv('ASAAS_API_KEY', '')")
            return False
        
        return True

    def _buscar_cobrancas_asaas(self, asaas_service, data_inicio, data_fim, status, cliente_id):
        """Busca cobranças no Asaas com paginação"""
        cobrancas = []
        offset = 0
        limit = 100
        
        while True:
            try:
                params = {
                    'dateCreated[ge]': data_inicio.strftime('%Y-%m-%d'),
                    'dateCreated[le]': data_fim.strftime('%Y-%m-%d'),
                    'offset': offset,
                    'limit': limit
                }
                
                if status:
                    params['status'] = status
                if cliente_id:
                    params['customer'] = cliente_id
                
                self.stdout.write(f"📡 Buscando cobranças... (offset: {offset})")
                response = asaas_service._fazer_requisicao('GET', 'payments', params=params)
                
                if not response.get('data'):
                    break
                
                cobrancas.extend(response['data'])
                
                # Verificar se há mais páginas
                if response.get('hasMore', False):
                    offset += limit
                    self.stdout.write(f"📄 Carregadas {len(cobrancas)} cobranças até agora...")
                else:
                    break
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Erro ao buscar cobranças: {str(e)}"))
                break
        
        return cobrancas

    def _processar_cobrancas(self, cobrancas_asaas, asaas_service):
        """Processa e sincroniza cada cobrança"""
        resultados = {
            'criadas': 0,
            'atualizadas': 0,
            'erros': 0,
            'ignoradas': 0,
            'detalhes_erros': []
        }
        
        for i, cobranca_data in enumerate(cobrancas_asaas, 1):
            try:
                self.stdout.write(f"🔄 Processando {i}/{len(cobrancas_asaas)}: {cobranca_data.get('id')}")
                
                resultado = self._sincronizar_cobranca(cobranca_data, asaas_service)
                resultados[resultado] += 1
                
                # Mostrar progresso a cada 10 cobranças
                if i % 10 == 0:
                    self.stdout.write(f"   📊 Progresso: {i}/{len(cobrancas_asaas)} ({(i/len(cobrancas_asaas)*100):.1f}%)")
                
            except Exception as e:
                resultados['erros'] += 1
                erro_msg = f"Cobrança {cobranca_data.get('id', 'N/A')}: {str(e)}"
                resultados['detalhes_erros'].append(erro_msg)
                self.stdout.write(self.style.ERROR(f"❌ {erro_msg}"))
        
        return resultados

    def _sincronizar_cobranca(self, cobranca_data, asaas_service):
        """Sincroniza uma cobrança específica"""
        asaas_id = cobranca_data.get('id')
        
        # Verificar se já existe uma integração com este asaas_id
        integracao_existente = AsaasIntegracao.objects.filter(asaas_id=asaas_id).first()
        
        if integracao_existente and not self.force_update:
            return 'ignoradas'
        
        # Buscar ou criar cliente (se modelo existe)
        cliente = None
        if Cliente:
            cliente = self._buscar_ou_criar_cliente(cobranca_data.get('customer'), asaas_service)
        
        # Buscar contrato (se modelo existe)
        contrato = None
        if Contrato and cliente:
            contrato = self._buscar_contrato(cliente, cobranca_data)
        
        if not self.dry_run:
            with transaction.atomic():
                if integracao_existente:
                    # Atualizar cobrança e integração existentes
                    self._atualizar_cobranca_existente(integracao_existente, cobranca_data)
                    return 'atualizadas'
                else:
                    # Criar nova cobrança e integração
                    self._criar_nova_cobranca(cobranca_data, cliente, contrato, asaas_service)
                    return 'criadas'
        else:
            action = 'atualizada' if integracao_existente else 'criada'
            self.stdout.write(f"  💡 Cobrança seria {action}: {asaas_id}")
            return 'criadas' if not integracao_existente else 'atualizadas'

    def _criar_nova_cobranca(self, cobranca_data, cliente, contrato, asaas_service):
        """Cria nova cobrança com integração Asaas"""
        
        # Mapear dados básicos da cobrança
        dados_cobranca = self._mapear_dados_cobranca(cobranca_data, cliente, contrato)
        
        # Criar cobrança
        cobranca = Cobranca.objects.create(**dados_cobranca)
        
        # Criar integração Asaas
        dados_integracao = self._mapear_dados_integracao(cobranca_data)
        AsaasIntegracao.objects.create(
            cobranca=cobranca,
            **dados_integracao
        )
        
        self.stdout.write(f"  ✅ Nova cobrança criada: {cobranca}")

    def _atualizar_cobranca_existente(self, integracao, cobranca_data):
        """Atualiza cobrança existente"""
        
        # Atualizar dados da cobrança
        cobranca = integracao.cobranca
        
        # Mapear status
        status_map = {
            'PENDING': 'pendente',
            'RECEIVED': 'paga',
            'CONFIRMED': 'paga',
            'OVERDUE': 'atrasada',
            'REFUNDED': 'cancelada',
            'RECEIVED_IN_CASH': 'paga',
        }
        
        novo_status = status_map.get(cobranca_data.get('status'), cobranca.status)
        if novo_status != cobranca.status:
            cobranca.status = novo_status
            
            # Se foi paga, adicionar data de pagamento
            if novo_status == 'paga' and cobranca_data.get('paymentDate'):
                cobranca.data_pagamento = datetime.strptime(
                    cobranca_data.get('paymentDate'), '%Y-%m-%d'
                ).date()
            
            cobranca.save()
        
        # Atualizar dados da integração
        integracao.gateway_status = cobranca_data.get('status')
        
        # Atualizar URLs se disponíveis
        if cobranca_data.get('bankSlipUrl'):
            integracao.boleto_url = cobranca_data.get('bankSlipUrl')
        if cobranca_data.get('invoiceUrl'):
            integracao.fatura_url = cobranca_data.get('invoiceUrl')
        
        integracao.save()
        
        self.stdout.write(f"  🔄 Cobrança atualizada: {cobranca}")

    def _mapear_dados_cobranca(self, cobranca_data, cliente, contrato):
        """Mapeia dados do Asaas para o modelo Cobranca"""
        
        # Mapear status
        status_map = {
            'PENDING': 'pendente',
            'RECEIVED': 'paga',
            'CONFIRMED': 'paga',
            'OVERDUE': 'atrasada',
            'REFUNDED': 'cancelada',
            'RECEIVED_IN_CASH': 'paga',
        }
        
        # Extrair mês e ano da data de vencimento
        data_vencimento = datetime.strptime(cobranca_data.get('dueDate'), '%Y-%m-%d').date()
        
        dados = {
            'contrato': contrato,
            'mes_referencia': data_vencimento.month,
            'ano_referencia': data_vencimento.year,
            'descricao': cobranca_data.get('description', 'Importado do Asaas'),
            'valor_aluguel': Decimal(str(cobranca_data.get('value', 0))),
            'valor_despesas': Decimal('0.00'),  # Será calculado depois se necessário
            'valor_total': Decimal(str(cobranca_data.get('value', 0))),
            'data_vencimento': data_vencimento,
            'status': status_map.get(cobranca_data.get('status'), 'pendente'),
            'observacoes': f"Importado do Asaas em {timezone.now().strftime('%d/%m/%Y %H:%M')}",
        }
        
        # Adicionar data de pagamento se disponível
        if cobranca_data.get('paymentDate'):
            dados['data_pagamento'] = datetime.strptime(
                cobranca_data.get('paymentDate'), '%Y-%m-%d'
            ).date()
        
        return dados

    def _mapear_dados_integracao(self, cobranca_data):
        """Mapeia dados do Asaas para o modelo AsaasIntegracao"""
        
        return {
            'asaas_id': cobranca_data.get('id'),
            'gateway_status': cobranca_data.get('status'),
            'boleto_url': cobranca_data.get('bankSlipUrl'),
            'fatura_url': cobranca_data.get('invoiceUrl'),
            'codigo_barras': cobranca_data.get('nossoNumero'),
            'formas_pagamento': cobranca_data.get('billingType', []),
            'envio_email': True,  # Padrão
            'envio_whatsapp': False,  # Padrão
        }

    def _buscar_ou_criar_cliente(self, cliente_asaas_id, asaas_service):
        """Busca cliente existente ou cria novo baseado no Asaas"""
        if not cliente_asaas_id or not Cliente:
            return None
        
        # Tentar encontrar cliente existente por asaas_id (se o campo existir)
        if hasattr(Cliente, 'asaas_id'):
            cliente = Cliente.objects.filter(asaas_id=cliente_asaas_id).first()
            if cliente:
                return cliente
        
        # Buscar dados do cliente no Asaas
        try:
            cliente_data = asaas_service._fazer_requisicao('GET', f'customers/{cliente_asaas_id}')
            
            # Verificar se cliente existe localmente por CPF/CNPJ
            documento = cliente_data.get('cpfCnpj', '').replace('.', '').replace('-', '').replace('/', '')
            if documento:
                # Tentar diferentes nomes de campos para CPF/CNPJ
                for campo_cpf in ['cpf_cnpj', 'cpf', 'cnpj', 'documento']:
                    if hasattr(Cliente, campo_cpf):
                        cliente = Cliente.objects.filter(**{campo_cpf: documento}).first()
                        if cliente:
                            return cliente
            
            # Se não encontrou e não estiver em modo simulação, avisar
            if self.dry_run:
                self.stdout.write(f"  💡 Cliente seria criado: {cliente_data.get('name')}")
            else:
                self.stdout.write(f"  ⚠️ Cliente não encontrado: {cliente_data.get('name')} - usando None")
            
            return None
                
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"⚠️  Erro ao buscar cliente {cliente_asaas_id}: {str(e)}"))
            return None

    def _buscar_contrato(self, cliente, cobranca_data):
        """Tenta identificar o contrato baseado nos dados da cobrança"""
        if not cliente or not Contrato:
            return None
        
        # Buscar contratos do cliente
        # Tentar diferentes nomes de campos para relacionamento com cliente
        for campo_cliente in ['inquilino', 'cliente', 'locatario']:
            if hasattr(Contrato, campo_cliente):
                try:
                    contratos = Contrato.objects.filter(**{campo_cliente: cliente})
                    
                    if contratos.exists():
                        # Se há apenas um contrato, retornar ele
                        if contratos.count() == 1:
                            return contratos.first()
                        
                        # Se há múltiplos, tentar identificar pelo valor
                        valor = Decimal(str(cobranca_data.get('value', 0)))
                        for contrato in contratos:
                            for campo_valor in ['valor_aluguel', 'valor', 'preco']:
                                if hasattr(contrato, campo_valor):
                                    valor_contrato = getattr(contrato, campo_valor)
                                    if valor_contrato and abs(valor_contrato - valor) < Decimal('0.01'):
                                        return contrato
                        
                        # Se não encontrou pelo valor, retornar o primeiro ativo
                        if hasattr(Contrato, 'ativo'):
                            contrato_ativo = contratos.filter(ativo=True).first()
                            if contrato_ativo:
                                return contrato_ativo
                        
                        # Última opção: retornar o primeiro
                        return contratos.first()
                        
                except Exception as e:
                    continue
                break
        
        return None

    def _exibir_relatorio(self, resultados):
        """Exibe relatório final da sincronização"""
        self.stdout.write("\n" + "="*50)
        self.stdout.write("📊 RELATÓRIO DE SINCRONIZAÇÃO")
        self.stdout.write("="*50)
        
        self.stdout.write(self.style.SUCCESS(f"✅ Cobranças criadas: {resultados['criadas']}"))
        self.stdout.write(self.style.WARNING(f"🔄 Cobranças atualizadas: {resultados['atualizadas']}"))
        self.stdout.write(self.style.HTTP_INFO(f"⏭️  Cobranças ignoradas: {resultados['ignoradas']}"))
        
        if resultados['erros'] > 0:
            self.stdout.write(self.style.ERROR(f"❌ Erros encontrados: {resultados['erros']}"))
            self.stdout.write("\nPrimeiros erros:")
            for erro in resultados['detalhes_erros'][:5]:
                self.stdout.write(f"  • {erro}")
            if len(resultados['detalhes_erros']) > 5:
                self.stdout.write(f"  ... e mais {len(resultados['detalhes_erros']) - 5} erros")
        
        total_processadas = resultados['criadas'] + resultados['atualizadas'] + resultados['ignoradas']
        self.stdout.write(f"\n🎯 Total processadas: {total_processadas}")
        
        if self.dry_run:
            self.stdout.write(self.style.WARNING("\n⚠️  SIMULAÇÃO CONCLUÍDA - Execute sem --dry-run para aplicar as alterações"))
        else:
            self.stdout.write(self.style.SUCCESS("\n🎉 SINCRONIZAÇÃO CONCLUÍDA COM SUCESSO!"))
            
        # Próximos passos
        self.stdout.write("\n📝 PRÓXIMOS PASSOS:")
        self.stdout.write("1. Verifique as cobranças criadas no admin Django")
        self.stdout.write("2. Confirme se as integrações AsaasIntegracao foram criadas")
        self.stdout.write("3. Configure webhooks para sincronização automática")
        self.stdout.write("4. Configure crontab para sincronização periódica")