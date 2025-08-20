# financeiro/services/cobranca_estatistica_service.py
from django.db.models import Sum, Count, Q, Avg
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta
import calendar


class CobrancaEstatisticaService:
    """
    Service para cálculos estatísticos de cobranças
    Atualizado para usar o campo 'valor' único
    """
    
    @classmethod
    def calcular_estatisticas(cls, filtros=None):
        """
        Calcula estatísticas gerais das cobranças
        
        Args:
            filtros: QuerySet filtrado, dicionário de filtros ou None para todas as cobranças
            
        Returns:
            dict: Estatísticas calculadas
        """
        from ..models.cobranca import Cobranca
        
        # Determinar o queryset baseado no tipo de filtros
        if filtros is None:
            queryset = Cobranca.objects.all()
        elif hasattr(filtros, 'count'):  # É um QuerySet
            queryset = filtros
        elif isinstance(filtros, dict):  # É um dicionário de filtros
            queryset = Cobranca.objects.all()
            # Aplicar filtros do dicionário
            for key, value in filtros.items():
                if value is not None and value != '':
                    if key == 'status' and value != 'todos':
                        queryset = queryset.filter(status=value)
                    elif key == 'mes_referencia':
                        queryset = queryset.filter(mes_referencia=value)
                    elif key == 'ano_referencia':
                        queryset = queryset.filter(ano_referencia=value)
                    # Adicionar outros filtros conforme necessário
        else:
            # Fallback para todas as cobranças
            queryset = Cobranca.objects.all()
        
        # Estatísticas básicas
        total_cobrancas = queryset.count()
        
        # Somatórias por status
        pendentes = queryset.filter(status__in=['pendente', 'rascunho']).aggregate(
            count=Count('id'),
            valor=Sum('valor')  # CORRIGIDO: 'valor' em vez de 'valor_total'
        )
        
        pagas = queryset.filter(status='paga').aggregate(
            count=Count('id'),
            valor=Sum('valor')  # CORRIGIDO
        )
        
        atrasadas = queryset.filter(status='atrasada').aggregate(
            count=Count('id'),
            valor=Sum('valor')  # CORRIGIDO
        )
        
        canceladas = queryset.filter(status='cancelada').aggregate(
            count=Count('id'),
            valor=Sum('valor')  # CORRIGIDO
        )
        
        # Valor médio das cobranças
        valor_medio = queryset.aggregate(
            media=Avg('valor')  # CORRIGIDO
        )['media'] or Decimal('0.00')
        
        # Total geral
        valor_total_geral = queryset.aggregate(
            total=Sum('valor')  # CORRIGIDO
        )['total'] or Decimal('0.00')
        
        # Cobranças vencidas (atrasadas)
        hoje = timezone.now().date()
        vencidas = queryset.filter(
            data_vencimento__lt=hoje,
            status__in=['pendente', 'atrasada']
        ).aggregate(
            count=Count('id'),
            valor=Sum('valor')  # CORRIGIDO
        )
        
        # Cobranças do mês atual
        mes_atual = timezone.now().month
        ano_atual = timezone.now().year
        
        mes_atual_stats = queryset.filter(
            mes_referencia=mes_atual,
            ano_referencia=ano_atual
        ).aggregate(
            count=Count('id'),
            valor=Sum('valor')  # CORRIGIDO
        )
        
        return {
            'total_cobrancas': total_cobrancas,
            'valor_total_geral': valor_total_geral,
            'valor_medio': valor_medio,
            
            # Por status
            'pendentes': {
                'count': pendentes['count'] or 0,
                'valor': pendentes['valor'] or Decimal('0.00')
            },
            'pagas': {
                'count': pagas['count'] or 0,
                'valor': pagas['valor'] or Decimal('0.00')
            },
            'atrasadas': {
                'count': atrasadas['count'] or 0,
                'valor': atrasadas['valor'] or Decimal('0.00')
            },
            'canceladas': {
                'count': canceladas['count'] or 0,
                'valor': canceladas['valor'] or Decimal('0.00')
            },
            'vencidas': {
                'count': vencidas['count'] or 0,
                'valor': vencidas['valor'] or Decimal('0.00')
            },
            
            # Período atual
            'mes_atual': {
                'count': mes_atual_stats['count'] or 0,
                'valor': mes_atual_stats['valor'] or Decimal('0.00'),
                'mes': mes_atual,
                'ano': ano_atual
            }
        }
    
    @classmethod
    def calcular_estatisticas_periodo(cls, mes, ano, contratos=None):
        """
        Calcula estatísticas para um período específico
        
        Args:
            mes: Mês de referência
            ano: Ano de referência
            contratos: Lista de contratos ou None para todos
            
        Returns:
            dict: Estatísticas do período
        """
        from ..models.cobranca import Cobranca
        
        queryset = Cobranca.objects.filter(
            mes_referencia=mes,
            ano_referencia=ano
        )
        
        if contratos:
            queryset = queryset.filter(contrato__in=contratos)
        
        # Estatísticas básicas
        stats = queryset.aggregate(
            total_cobrancas=Count('id'),
            valor_total=Sum('valor'),  # CORRIGIDO
            valor_medio=Avg('valor')   # CORRIGIDO
        )
        
        # Por status
        por_status = {}
        for status_key, status_name in Cobranca.STATUS_CHOICES:
            status_stats = queryset.filter(status=status_key).aggregate(
                count=Count('id'),
                valor=Sum('valor')  # CORRIGIDO
            )
            por_status[status_key] = {
                'nome': status_name,
                'count': status_stats['count'] or 0,
                'valor': status_stats['valor'] or Decimal('0.00')
            }
        
        return {
            'periodo': {
                'mes': mes,
                'ano': ano,
                'nome_mes': calendar.month_name[mes]
            },
            'total_cobrancas': stats['total_cobrancas'] or 0,
            'valor_total': stats['valor_total'] or Decimal('0.00'),
            'valor_medio': stats['valor_medio'] or Decimal('0.00'),
            'por_status': por_status
        }
    
    @classmethod
    def calcular_evolucao_mensal(cls, meses=6):
        """
        Calcula evolução das cobranças nos últimos meses
        
        Args:
            meses: Número de meses para analisar
            
        Returns:
            list: Lista com dados de cada mês
        """
        from ..models.cobranca import Cobranca
        
        hoje = date.today()
        evolucao = []
        
        for i in range(meses):
            # Calcular mês/ano
            mes_calc = hoje.month - i
            ano_calc = hoje.year
            
            while mes_calc <= 0:
                mes_calc += 12
                ano_calc -= 1
            
            # Estatísticas do mês
            queryset = Cobranca.objects.filter(
                mes_referencia=mes_calc,
                ano_referencia=ano_calc
            )
            
            stats = queryset.aggregate(
                total=Count('id'),
                valor=Sum('valor'),  # CORRIGIDO
                pendentes=Count('id', filter=Q(status='pendente')),
                pagas=Count('id', filter=Q(status='paga')),
                atrasadas=Count('id', filter=Q(status='atrasada'))
            )
            
            evolucao.append({
                'mes': mes_calc,
                'ano': ano_calc,
                'nome_mes': calendar.month_name[mes_calc],
                'total_cobrancas': stats['total'] or 0,
                'valor_total': stats['valor'] or Decimal('0.00'),
                'pendentes': stats['pendentes'] or 0,
                'pagas': stats['pagas'] or 0,
                'atrasadas': stats['atrasadas'] or 0
            })
        
        return list(reversed(evolucao))  # Ordem cronológica
    
    @classmethod
    def calcular_taxa_inadimplencia(cls, periodo_dias=30):
        """
        Calcula taxa de inadimplência
        
        Args:
            periodo_dias: Período em dias para considerar
            
        Returns:
            dict: Dados da inadimplência
        """
        from ..models.cobranca import Cobranca
        
        data_limite = timezone.now().date() - timedelta(days=periodo_dias)
        
        # Cobranças vencidas no período
        vencidas = Cobranca.objects.filter(
            data_vencimento__gte=data_limite,
            data_vencimento__lt=timezone.now().date(),
            status__in=['pendente', 'atrasada']
        )
        
        # Total de cobranças no período
        total_periodo = Cobranca.objects.filter(
            data_vencimento__gte=data_limite,
            data_vencimento__lt=timezone.now().date()
        )
        
        total_vencidas = vencidas.count()
        total_geral = total_periodo.count()
        
        # Valores
        valor_vencido = vencidas.aggregate(
            total=Sum('valor')  # CORRIGIDO
        )['total'] or Decimal('0.00')
        
        valor_total_periodo = total_periodo.aggregate(
            total=Sum('valor')  # CORRIGIDO
        )['total'] or Decimal('0.00')
        
        # Calcular taxas
        taxa_quantidade = (total_vencidas / total_geral * 100) if total_geral > 0 else 0
        taxa_valor = (valor_vencido / valor_total_periodo * 100) if valor_total_periodo > 0 else 0
        
        return {
            'periodo_dias': periodo_dias,
            'total_vencidas': total_vencidas,
            'total_periodo': total_geral,
            'valor_vencido': valor_vencido,
            'valor_total_periodo': valor_total_periodo,
            'taxa_quantidade': round(taxa_quantidade, 2),
            'taxa_valor': round(float(taxa_valor), 2)
        }
    
    @classmethod
    def obter_top_contratos_valor(cls, limite=10):
        """
        Obtém contratos com maior valor em cobranças
        
        Args:
            limite: Número de contratos a retornar
            
        Returns:
            list: Lista dos top contratos
        """
        from ..models.cobranca import Cobranca
        
        resultado = Cobranca.objects.values(
            'contrato__id',
            'contrato__numero',  # Ajuste conforme o campo correto
        ).annotate(
            total_cobrancas=Count('id'),
            valor_total=Sum('valor'),  # CORRIGIDO
            valor_medio=Avg('valor')   # CORRIGIDO
        ).order_by('-valor_total')[:limite]
        
        return list(resultado)
    
    @classmethod
    def calcular_previsao_recebimento(cls, meses_futuros=3):
        """
        Calcula previsão de recebimentos baseada nas cobranças pendentes
        
        Args:
            meses_futuros: Número de meses futuros para analisar
            
        Returns:
            dict: Previsões por mês
        """
        from ..models.cobranca import Cobranca
        
        hoje = date.today()
        previsoes = {}
        
        for i in range(meses_futuros):
            # Calcular mês/ano futuro
            mes_calc = hoje.month + i
            ano_calc = hoje.year
            
            while mes_calc > 12:
                mes_calc -= 12
                ano_calc += 1
            
            # Cobranças pendentes com vencimento neste mês
            pendentes = Cobranca.objects.filter(
                status__in=['pendente', 'rascunho'],
                data_vencimento__month=mes_calc,
                data_vencimento__year=ano_calc
            ).aggregate(
                count=Count('id'),
                valor=Sum('valor')  # CORRIGIDO
            )
            
            previsoes[f"{ano_calc}-{mes_calc:02d}"] = {
                'mes': mes_calc,
                'ano': ano_calc,
                'nome_mes': calendar.month_name[mes_calc],
                'cobrancas_pendentes': pendentes['count'] or 0,
                'valor_previsto': pendentes['valor'] or Decimal('0.00')
            }
        
        return previsoes
    
    @classmethod
    def calcular_resumo_dashboard(cls):
        """
        Calcula resumo executivo para dashboard
        
        Returns:
            dict: Resumo com principais métricas
        """
        hoje = timezone.now().date()
        mes_atual = hoje.month
        ano_atual = hoje.year
        
        # Estatísticas gerais
        stats_gerais = cls.calcular_estatisticas()
        
        # Estatísticas do mês atual
        stats_mes = cls.calcular_estatisticas_periodo(mes_atual, ano_atual)
        
        # Taxa de inadimplência
        inadimplencia = cls.calcular_taxa_inadimplencia()
        
        # Cobranças vencendo nos próximos 7 dias
        data_limite = hoje + timedelta(days=7)
        vencendo_7_dias = Cobranca.objects.filter(
            data_vencimento__gte=hoje,
            data_vencimento__lte=data_limite,
            status__in=['pendente', 'rascunho']
        ).aggregate(
            count=Count('id'),
            valor=Sum('valor')  # CORRIGIDO
        )
        
        return {
            'geral': stats_gerais,
            'mes_atual': stats_mes,
            'inadimplencia': inadimplencia,
            'vencendo_7_dias': {
                'count': vencendo_7_dias['count'] or 0,
                'valor': vencendo_7_dias['valor'] or Decimal('0.00')
            },
            'data_atualizacao': hoje
        }