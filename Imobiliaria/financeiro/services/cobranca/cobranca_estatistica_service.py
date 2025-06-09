from financeiro.services.cobranca.cobranca_consulta_service import CobrancaConsultaService
from django.db.models import Sum, Count, Q  # ← Adicionar Sum aqui
from decimal import Decimal


class CobrancaEstatisticaService:
    """Service para cálculo de estatísticas"""
    
    @staticmethod
    def calcular_estatisticas(filtros=None):
        """
        Calcula estatísticas gerais das cobranças
        """
        from financeiro.models import Cobranca
        
        queryset = Cobranca.objects.all()
        
        # Aplicar filtros se fornecidos
        if filtros:
            queryset = CobrancaConsultaService.filtrar_cobrancas(filtros)
        
        # Contar por status
        stats = {
            'total_cobrancas': queryset.count(),
            'cobrancas_pendentes': queryset.filter(status='pendente').count(),
            'cobrancas_pagas': queryset.filter(status='paga').count(),
            'cobrancas_atrasadas': queryset.filter(status='atrasada').count(),
        }
        
        # Somar valores por status
        valores = queryset.aggregate(
            total_pendente=Sum('valor_total', filter=Q(status='pendente')),
            total_pago=Sum('valor_total', filter=Q(status='paga')),
            total_atrasado=Sum('valor_total', filter=Q(status='atrasada'))
        )
        
        stats.update({
            'valor_total_pendente': valores['total_pendente'] or Decimal('0.00'),
            'valor_total_pago': valores['total_pago'] or Decimal('0.00'),
            'valor_total_atrasado': valores['total_atrasado'] or Decimal('0.00'),
        })
        
        return stats