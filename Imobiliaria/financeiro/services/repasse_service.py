# financeiro/services/repasse_service.py - VERSÃO CORRIGIDA
from django.db import transaction
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal
import logging

from ..models.repasse import Repasse, PoliticaRepasseContrato, PoliticaRepasseGlobal, AgendamentoRepasse
from sisimob.models import Contrato, Cliente

try:
    from ..models.cobranca import Cobranca
except ImportError:
    Cobranca = None

logger = logging.getLogger(__name__)


class RepasseService:
    """
    Serviço principal para automação de repasses
    """
    
    def __init__(self):
        self.hoje = date.today()
        self.resultados = {
            'criados': 0,
            'processados': 0,
            'agendados': 0,
            'erros': 0,
            'detalhes': []
        }
    
    def processar_repasses_automaticos(self):
        """
        Método principal que processa todos os repasses automáticos
        """
        logger.info("Iniciando processamento automático de repasses")
        
        try:
            # 1. Processar agendamentos vencidos
            self._processar_agendamentos_vencidos()
            
            # 2. Criar repasses diretos baseados em cobranças pagas (ALTERADO)
            self._processar_cobrancas_pagas_recentes()
            
            logger.info(f"Processamento concluído: {self.resultados}")
            return self.resultados
            
        except Exception as e:
            logger.error(f"Erro no processamento automático: {str(e)}")
            self.resultados['erros'] += 1
            self.resultados['detalhes'].append(f"Erro geral: {str(e)}")
            return self.resultados
    
    def _processar_agendamentos_vencidos(self):
        """
        Processa agendamentos que já venceram
        """
        agendamentos_vencidos = AgendamentoRepasse.objects.filter(
            status='agendado',
            data_agendada__lte=self.hoje
        ).select_related('proprietario', 'contrato')
        
        logger.info(f"Encontrados {agendamentos_vencidos.count()} agendamentos vencidos")
        
        for agendamento in agendamentos_vencidos:
            try:
                repasse = agendamento.processar()
                if repasse:
                    self.resultados['processados'] += 1
                    self.resultados['detalhes'].append(
                        f"Agendamento {agendamento.id} processado → Repasse {repasse.id}"
                    )
                else:
                    self.resultados['erros'] += 1
                    self.resultados['detalhes'].append(
                        f"Erro ao processar agendamento {agendamento.id}"
                    )
            except Exception as e:
                self.resultados['erros'] += 1
                logger.error(f"Erro ao processar agendamento {agendamento.id}: {str(e)}")
                self.resultados['detalhes'].append(
                    f"Erro agendamento {agendamento.id}: {str(e)}"
                )

    # ==================== MÉTODO PRINCIPAL ALTERADO ====================
    
    def _processar_cobrancas_pagas_recentes(self):
        """
        NOVO: Processa cobranças pagas recentemente e cria repasses baseados na data de pagamento
        """
        if not Cobranca:
            return
        
        # Buscar cobranças pagas nos últimos 30 dias sem repasse
        data_limite = self.hoje - timedelta(days=30)
        
        cobrancas_sem_repasse = Cobranca.objects.filter(
            status='paga',
            data_pagamento__gte=data_limite,
            repasses_cobranca__isnull=True
        ).select_related('contrato').prefetch_related('contrato__proprietario')
        
        logger.info(f"Encontradas {cobrancas_sem_repasse.count()} cobranças pagas sem repasse")
        
        for cobranca in cobrancas_sem_repasse:
            self._criar_repasse_baseado_em_pagamento(cobranca)
    
    def _criar_repasse_baseado_em_pagamento(self, cobranca):
        """
        NOVO: Cria repasse baseado na DATA DE PAGAMENTO da cobrança
        """
        try:
            contrato = cobranca.contrato
            
            # Verificar se já existe repasse para esta cobrança
            if Repasse.objects.filter(cobranca=cobranca).exists():
                return
            
            # ✅ MUDANÇA PRINCIPAL: Usar data de pagamento como referência
            data_pagamento = getattr(cobranca, 'data_pagamento', self.hoje)
            
            # Calcular data do repasse baseada na política e DATA DE PAGAMENTO
            if hasattr(contrato, 'politica_repasse') and contrato.politica_repasse:
                politica = contrato.politica_repasse
                
                # ✅ USAR O NOVO MÉTODO que considera data de pagamento
                if hasattr(politica, 'calcular_data_repasse'):
                    data_repasse = politica.calcular_data_repasse(data_pagamento)
                else:
                    # Fallback se o método novo não existir ainda
                    data_repasse = self._calcular_data_repasse_fallback(data_pagamento, politica)
                
                taxa_admin = politica.get_taxa_admin()
            else:
                # Usar política padrão se não houver política específica
                data_repasse = self._adicionar_dias_uteis(data_pagamento, 2)  # 2 dias úteis padrão
                taxa_admin = Decimal('8.00')  # 8% padrão
            
            # Calcular valores
            valor_base = getattr(cobranca, 'valor_pago', getattr(cobranca, 'valor', Decimal('0')))
            valor_taxa_admin = valor_base * (taxa_admin / 100)
            
            # Verificar valor mínimo se houver política
            valor_liquido = valor_base - valor_taxa_admin
            valor_minimo = Decimal('0')
            
            if hasattr(contrato, 'politica_repasse') and contrato.politica_repasse:
                valor_minimo = getattr(contrato.politica_repasse, 'valor_minimo_repasse', Decimal('0'))
                
                if valor_liquido < valor_minimo:
                    logger.info(f"Valor líquido {valor_liquido} abaixo do mínimo {valor_minimo} para cobrança {cobranca.id}")
                    return
            
            # Criar repasse para cada proprietário
            proprietarios = contrato.proprietario.all()
            for proprietario in proprietarios:
                # Calcular valor proporcional se há múltiplos proprietários
                valor_proporcional = valor_base / len(proprietarios) if len(proprietarios) > 1 else valor_base
                taxa_proporcional = valor_taxa_admin / len(proprietarios) if len(proprietarios) > 1 else valor_taxa_admin
                
                repasse = Repasse.objects.create(
                    proprietario=proprietario,
                    cobranca=cobranca,
                    contrato=contrato,
                    valor=valor_proporcional,
                    valor_taxa_admin=taxa_proporcional,
                    data_prevista=data_repasse,  # ← Data calculada baseada no PAGAMENTO
                    mes_referencia=getattr(cobranca, 'mes_referencia', data_pagamento.month),
                    ano_referencia=getattr(cobranca, 'ano_referencia', data_pagamento.year),
                    status='pendente',
                    tipo='automatico',
                    descricao=f"Repasse automático - cobrança paga em {data_pagamento.strftime('%d/%m/%Y')}"
                )
                
                self.resultados['criados'] += 1
                self.resultados['detalhes'].append(
                    f"Repasse {repasse.id} criado para {proprietario.nome} - Cobrança paga em {data_pagamento.strftime('%d/%m/%Y')}, repasse previsto para {data_repasse.strftime('%d/%m/%Y')}"
                )
                
        except Exception as e:
            self.resultados['erros'] += 1
            logger.error(f"Erro ao criar repasse para cobrança {cobranca.id}: {str(e)}")
            self.resultados['detalhes'].append(f"Erro cobrança {cobranca.id}: {str(e)}")
    
    # ==================== MÉTODOS AUXILIARES NOVOS ====================
    
    def _calcular_data_repasse_fallback(self, data_pagamento, politica):
        """
        Fallback para calcular data de repasse se o método novo não existir na política
        """
        dias_apos = getattr(politica, 'dias_apos_recebimento', 2)
        tipo_dias = getattr(politica, 'tipo_dias', 'uteis')
        
        if tipo_dias == 'uteis':
            return self._adicionar_dias_uteis(data_pagamento, dias_apos)
        else:
            return data_pagamento + timedelta(days=dias_apos)
    
    def _adicionar_dias_uteis(self, data_inicial, quantidade_dias):
        """
        Adiciona quantidade específica de dias ÚTEIS (segunda a sexta)
        """
        data_atual = data_inicial
        dias_adicionados = 0
        
        while dias_adicionados < quantidade_dias:
            data_atual = data_atual + timedelta(days=1)
            
            # Verificar se é dia útil (segunda=0 a sexta=4)
            if data_atual.weekday() < 5:  # 0-4 = segunda a sexta
                dias_adicionados += 1
        
        return data_atual
    
    # ==================== MÉTODOS EXISTENTES (mantidos) ====================
    
    def _criar_novos_agendamentos(self):
        """
        REMOVIDO: Não usamos mais agendamentos, criamos repasses diretos
        Mantido para compatibilidade, mas pode ser removido
        """
        pass
    
    def _processar_contrato_para_agendamento(self, contrato):
        """
        REMOVIDO: Lógica antiga de agendamentos
        Mantido para compatibilidade, mas pode ser removido
        """
        pass
    
    def _criar_repasses_diretos(self):
        """
        REMOVIDO: Substituído por _processar_cobrancas_pagas_recentes
        Mantido para compatibilidade, mas pode ser removido
        """
        pass
    
    def _criar_repasse_direto(self, cobranca):
        """
        REMOVIDO: Substituído por _criar_repasse_baseado_em_pagamento
        Mantido para compatibilidade, mas pode ser removido
        """
        pass
    
    def _buscar_cobranca_paga(self, contrato, mes, ano):
        """
        Busca cobrança paga para um contrato em um período específico
        """
        if not Cobranca:
            return None
        
        return Cobranca.objects.filter(
            contrato=contrato,
            mes_referencia=mes,
            ano_referencia=ano,
            status='paga'
        ).first()
    
    def _calcular_valor_repasse(self, cobranca, politica):
        """
        Calcula o valor do repasse baseado na cobrança e política
        """
        valor_base = getattr(cobranca, 'valor_pago', getattr(cobranca, 'valor', Decimal('0')))
        taxa_admin = politica.get_taxa_admin()
        valor_taxa = valor_base * (taxa_admin / 100)
        
        return valor_base - valor_taxa
    
    def processar_repasse_individual(self, repasse_id):
        """
        Processa um repasse individual específico
        """
        try:
            repasse = Repasse.objects.get(id=repasse_id)
            
            if repasse.status != 'pendente':
                return {'success': False, 'error': 'Repasse não está pendente'}
            
            # Efetivar repasse
            success = repasse.efetivar_repasse()
            
            if success:
                return {
                    'success': True,
                    'message': f'Repasse {repasse_id} efetuado com sucesso'
                }
            else:
                return {
                    'success': False,
                    'error': 'Não foi possível efetivar o repasse'
                }
                
        except Repasse.DoesNotExist:
            return {'success': False, 'error': 'Repasse não encontrado'}
        except Exception as e:
            logger.error(f"Erro ao processar repasse {repasse_id}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def verificar_repasses_atrasados(self):
        """
        Verifica e retorna repasses atrasados
        """
        repasses_atrasados = Repasse.objects.filter(
            status='pendente',
            data_prevista__lt=self.hoje
        ).select_related('proprietario', 'contrato')
        
        return {
            'count': repasses_atrasados.count(),
            'repasses': list(repasses_atrasados.values(
                'id', 'proprietario__nome', 'contrato__id', 
                'valor_liquido', 'data_prevista', 'dias_atraso'
            ))
        }
    
    def gerar_relatorio_automatizacao(self):
        """
        Gera relatório do status da automação
        """
        # Estatísticas gerais
        total_contratos = Contrato.objects.filter(ativo=True).count()
        contratos_com_politica = Contrato.objects.filter(
            ativo=True,
            politica_repasse__isnull=False
        ).count()
        
        # Agendamentos
        agendamentos_pendentes = AgendamentoRepasse.objects.filter(
            status='agendado'
        ).count()
        
        # Repasses
        repasses_pendentes = Repasse.objects.filter(
            status='pendente'
        ).count()
        
        repasses_atrasados = Repasse.objects.filter(
            status='pendente',
            data_prevista__lt=self.hoje
        ).count()
        
        return {
            'contratos': {
                'total': total_contratos,
                'com_politica': contratos_com_politica,
                'sem_politica': total_contratos - contratos_com_politica,
                'percentual_cobertura': (contratos_com_politica / total_contratos * 100) if total_contratos > 0 else 0
            },
            'agendamentos': {
                'pendentes': agendamentos_pendentes
            },
            'repasses': {
                'pendentes': repasses_pendentes,
                'atrasados': repasses_atrasados
            },
            'data_relatorio': self.hoje.strftime('%d/%m/%Y')
        }

    # ==================== MÉTODO PARA TESTAR A LÓGICA ====================
    
    def simular_repasse_para_cobranca(self, cobranca_id):
        """
        NOVO: Simula como seria o repasse para uma cobrança específica
        Útil para testar a lógica antes de criar o repasse real
        """
        try:
            if not Cobranca:
                return {'erro': 'Modelo Cobranca não disponível'}
            
            cobranca = Cobranca.objects.get(id=cobranca_id)
            contrato = cobranca.contrato
            data_pagamento = getattr(cobranca, 'data_pagamento', self.hoje)
            
            # Simular cálculo da data
            if hasattr(contrato, 'politica_repasse') and contrato.politica_repasse:
                politica = contrato.politica_repasse
                
                if hasattr(politica, 'calcular_data_repasse'):
                    data_repasse = politica.calcular_data_repasse(data_pagamento)
                else:
                    data_repasse = self._calcular_data_repasse_fallback(data_pagamento, politica)
                
                taxa_admin = politica.get_taxa_admin()
                dias_politica = getattr(politica, 'dias_apos_recebimento', 2)
                tipo_dias = getattr(politica, 'tipo_dias', 'uteis')
            else:
                data_repasse = self._adicionar_dias_uteis(data_pagamento, 2)
                taxa_admin = Decimal('8.00')
                dias_politica = 2
                tipo_dias = 'uteis'
            
            # Calcular valores
            valor_base = getattr(cobranca, 'valor_pago', getattr(cobranca, 'valor', Decimal('0')))
            valor_taxa_admin = valor_base * (taxa_admin / 100)
            valor_liquido = valor_base - valor_taxa_admin
            
            # Calcular dias entre pagamento e repasse
            dias_para_repasse = (data_repasse - data_pagamento).days
            
            return {
                'cobranca_id': cobranca_id,
                'contrato_id': contrato.id,
                'data_pagamento': data_pagamento.strftime('%d/%m/%Y'),
                'data_repasse_prevista': data_repasse.strftime('%d/%m/%Y'),
                'dias_para_repasse': dias_para_repasse,
                'politica': {
                    'dias_apos_recebimento': dias_politica,
                    'tipo_dias': tipo_dias,
                    'taxa_admin': float(taxa_admin)
                },
                'valores': {
                    'bruto': float(valor_base),
                    'taxa_admin': float(valor_taxa_admin),
                    'liquido': float(valor_liquido)
                },
                'viable': True
            }
            
        except Exception as e:
            return {
                'erro': str(e),
                'viable': False
            }