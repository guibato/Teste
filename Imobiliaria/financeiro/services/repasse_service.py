# financeiro/services/repasse_service.py
from django.db import transaction
from django.utils import timezone
from django.db.models import Q, Sum, F, Count
from decimal import Decimal
from datetime import date, timedelta
import logging

from ..models.repasse import Repasse, PoliticaRepasse, AgendamentoRepasse
from ..models.cobranca import Cobranca
from ..models.movimento import MovimentoConta, SaldoProprietario
from sisimob.models import Contrato, Cliente

logger = logging.getLogger(__name__)


class RepasseService:
    """Service para gerenciar repasses e suas regras de negócio"""

    def __init__(self):
        self.logger = logger

    def calcular_valor_repasse(self, cobranca, politica=None):
        """
        Calcula o valor do repasse baseado na cobrança e política
        """
        try:
            if not cobranca or cobranca.status != 'paga':
                return Decimal('0.00'), {}

            # Valor base (valor pago - taxa de administração)
            valor_base = cobranca.valor_pago
            
            # Descontos e taxas
            valor_taxa_admin = cobranca.calcular_taxa_administracao()
            valor_desconto = Decimal('0.00')
            
            # Aplicar política se fornecida
            if politica:
                # Taxa de adiantamento se aplicável
                if politica.percentual_adiantamento > 0:
                    valor_adiantamento = valor_base * (politica.percentual_adiantamento / 100)
                    valor_taxa_admin += politica.taxa_adiantamento
                
                # Verificar valor mínimo
                valor_liquido_calculado = valor_base - valor_taxa_admin - valor_desconto
                if valor_liquido_calculado < politica.valor_minimo_repasse:
                    return Decimal('0.00'), {
                        'motivo': 'Valor abaixo do mínimo',
                        'minimo': politica.valor_minimo_repasse,
                        'calculado': valor_liquido_calculado
                    }

            detalhes = {
                'valor_base': valor_base,
                'valor_taxa_admin': valor_taxa_admin,
                'valor_desconto': valor_desconto,
                'valor_liquido': valor_base - valor_taxa_admin - valor_desconto
            }

            return valor_base, detalhes

        except Exception as e:
            self.logger.error(f"Erro ao calcular repasse: {str(e)}")
            return Decimal('0.00'), {'erro': str(e)}

    def criar_repasse_manual(self, dados):
        """
        Cria um repasse manual com validações
        """
        try:
            with transaction.atomic():
                # Validar se já existe repasse para o período
                existe = Repasse.objects.filter(
                    proprietario=dados['proprietario'],
                    contrato=dados['contrato'],
                    mes_referencia=dados['mes_referencia'],
                    ano_referencia=dados['ano_referencia'],
                    status__in=['pendente', 'efetuado']
                ).exists()

                if existe:
                    raise ValueError("Já existe repasse para este período")

                # Criar repasse
                repasse = Repasse.objects.create(
                    proprietario=dados['proprietario'],
                    contrato=dados['contrato'],
                    cobranca=dados.get('cobranca'),
                    valor=dados['valor'],
                    valor_desconto=dados.get('valor_desconto', Decimal('0.00')),
                    valor_taxa_admin=dados.get('valor_taxa_admin', Decimal('0.00')),
                    data_prevista=dados['data_prevista'],
                    mes_referencia=dados['mes_referencia'],
                    ano_referencia=dados['ano_referencia'],
                    tipo='manual',
                    descricao=dados.get('descricao', ''),
                    observacoes=dados.get('observacoes', '')
                )

                self.logger.info(f"Repasse manual criado: {repasse.id}")
                return repasse

        except Exception as e:
            self.logger.error(f"Erro ao criar repasse manual: {str(e)}")
            raise

    def processar_repasses_automaticos(self, data_referencia=None):
        """
        Processa repasses automáticos baseados nas políticas ativas
        """
        if not data_referencia:
            data_referencia = date.today()

        resultado = {
            'processados': 0,
            'criados': 0,
            'erros': 0,
            'detalhes': []
        }

        try:
            # Buscar agendamentos para processar
            agendamentos = AgendamentoRepasse.objects.filter(
                status='agendado',
                data_agendada__lte=data_referencia
            ).select_related('proprietario', 'contrato', 'politica')

            for agendamento in agendamentos:
                try:
                    with transaction.atomic():
                        repasse = agendamento.processar()
                        if repasse:
                            resultado['criados'] += 1
                            resultado['detalhes'].append({
                                'agendamento_id': agendamento.id,
                                'repasse_id': repasse.id,
                                'valor': repasse.valor_liquido,
                                'status': 'sucesso'
                            })
                        resultado['processados'] += 1

                except Exception as e:
                    resultado['erros'] += 1
                    resultado['detalhes'].append({
                        'agendamento_id': agendamento.id,
                        'erro': str(e),
                        'status': 'erro'
                    })
                    self.logger.error(f"Erro ao processar agendamento {agendamento.id}: {str(e)}")

            self.logger.info(f"Processamento automático concluído: {resultado}")
            return resultado

        except Exception as e:
            self.logger.error(f"Erro no processamento automático: {str(e)}")
            raise

    def agendar_repasses_futuros(self, dias_futuro=30):
        """
        Agenda repasses futuros baseados nas políticas ativas
        """
        resultado = {
            'agendados': 0,
            'erros': 0,
            'detalhes': []
        }

        try:
            politicas_ativas = PoliticaRepasse.objects.filter(ativa=True)
            data_limite = date.today() + timedelta(days=dias_futuro)

            for politica in politicas_ativas:
                try:
                    # Buscar contratos que precisam de agendamento
                    contratos = Contrato.objects.filter(
                        status='ativo',
                        data_fim__gte=date.today()
                    ).select_related('proprietario')

                    for contrato in contratos:
                        # Verificar se há cobrança paga no período
                        proxima_data = politica.calcular_proxima_data_repasse()
                        
                        if proxima_data and proxima_data <= data_limite:
                            # Verificar se já existe agendamento
                            existe = AgendamentoRepasse.objects.filter(
                                contrato=contrato,
                                data_agendada=proxima_data,
                                status__in=['agendado', 'processando']
                            ).exists()

                            if not existe:
                                # Calcular valor previsto
                                valor_previsto = self._calcular_valor_previsto(contrato, proxima_data)
                                
                                if valor_previsto > 0:
                                    agendamento = AgendamentoRepasse.objects.create(
                                        proprietario=contrato.proprietario,
                                        contrato=contrato,
                                        politica=politica,
                                        data_agendada=proxima_data,
                                        valor_previsto=valor_previsto,
                                        mes_referencia=proxima_data.month,
                                        ano_referencia=proxima_data.year
                                    )
                                    
                                    resultado['agendados'] += 1
                                    resultado['detalhes'].append({
                                        'agendamento_id': agendamento.id,
                                        'contrato_id': contrato.id,
                                        'data_agendada': proxima_data,
                                        'valor_previsto': valor_previsto
                                    })

                except Exception as e:
                    resultado['erros'] += 1
                    self.logger.error(f"Erro ao agendar para política {politica.id}: {str(e)}")

            return resultado

        except Exception as e:
            self.logger.error(f"Erro no agendamento: {str(e)}")
            raise

    def _calcular_valor_previsto(self, contrato, data_agendada):
        """
        Calcula valor previsto baseado no histórico de cobranças
        """
        try:
            # Buscar última cobrança paga
            ultima_cobranca = Cobranca.objects.filter(
                contrato=contrato,
                status='paga'
            ).order_by('-data_pagamento').first()

            if ultima_cobranca:
                valor_base, detalhes = self.calcular_valor_repasse(ultima_cobranca)
                return detalhes.get('valor_liquido', Decimal('0.00'))
            
            # Se não há histórico, usar valor do contrato
            return contrato.valor_aluguel * Decimal('0.9')  # Estimativa (90% do aluguel)

        except Exception as e:
            self.logger.error(f"Erro ao calcular valor previsto: {str(e)}")
            return Decimal('0.00')

    def atualizar_saldos_proprietario(self, repasse):
        """
        Atualiza saldo do proprietário após efetivação do repasse
        """
        try:
            with transaction.atomic():
                saldo, created = SaldoProprietario.objects.get_or_create(
                    proprietario=repasse.proprietario,
                    defaults={'saldo_atual': Decimal('0.00')}
                )

                # Registrar movimento
                MovimentoConta.objects.create(
                    proprietario=repasse.proprietario,
                    contrato=repasse.contrato,
                    tipo='repasse',
                    descricao=f"Repasse {repasse.id} - {repasse.mes_referencia}/{repasse.ano_referencia}",
                    valor=repasse.valor_liquido,
                    data_referencia=repasse.data_efetivacao,
                    repasse=repasse
                )

                # Atualizar saldo
                saldo.saldo_atual += repasse.valor_liquido
                saldo.data_atualizacao = timezone.now()
                saldo.save()

                self.logger.info(f"Saldo atualizado para proprietário {repasse.proprietario.id}")

        except Exception as e:
            self.logger.error(f"Erro ao atualizar saldo: {str(e)}")
            raise

    def gerar_relatorio_repasses(self, filtros):
        """
        Gera relatório de repasses com filtros
        """
        try:
            queryset = Repasse.objects.select_related(
                'proprietario', 'contrato', 'cobranca'
            ).prefetch_related('contrato__imovel')

            # Aplicar filtros
            if filtros.get('data_inicio'):
                queryset = queryset.filter(data_criacao__date__gte=filtros['data_inicio'])
            
            if filtros.get('data_fim'):
                queryset = queryset.filter(data_criacao__date__lte=filtros['data_fim'])
            
            if filtros.get('status'):
                queryset = queryset.filter(status=filtros['status'])
            
            if filtros.get('proprietario_id'):
                queryset = queryset.filter(proprietario_id=filtros['proprietario_id'])

            # Estatísticas
            stats = queryset.aggregate(
                total_repasses=Sum('valor'),
                total_liquido=Sum(F('valor') - F('valor_desconto') - F('valor_taxa_admin')),
                total_descontos=Sum('valor_desconto'),
                total_taxas=Sum('valor_taxa_admin'),
                quantidade=Count('id')
            )

            # Agrupamentos
            por_status = queryset.values('status').annotate(
                total=Sum(F('valor') - F('valor_desconto') - F('valor_taxa_admin')),
                quantidade=Count('id')
            )

            por_proprietario = queryset.values(
                'proprietario__nome'
            ).annotate(
                total=Sum(F('valor') - F('valor_desconto') - F('valor_taxa_admin')),
                quantidade=Count('id')
            ).order_by('-total')

            return {
                'repasses': queryset.order_by('-data_criacao'),
                'estatisticas': stats,
                'por_status': list(por_status),
                'por_proprietario': list(por_proprietario)
            }

        except Exception as e:
            self.logger.error(f"Erro ao gerar relatório: {str(e)}")
            raise

    def verificar_repasses_atrasados(self):
        """
        Verifica e retorna repasses em atraso
        """
        try:
            atrasados = Repasse.objects.filter(
                status='pendente',
                data_prevista__lt=date.today()
            ).select_related('proprietario', 'contrato').order_by('data_prevista')

            resultado = []
            for repasse in atrasados:
                resultado.append({
                    'repasse': repasse,
                    'dias_atraso': repasse.dias_atraso,
                    'proprietario': repasse.proprietario.nome,
                    'valor_liquido': repasse.valor_liquido
                })

            return resultado

        except Exception as e:
            self.logger.error(f"Erro ao verificar repasses atrasados: {str(e)}")
            return []