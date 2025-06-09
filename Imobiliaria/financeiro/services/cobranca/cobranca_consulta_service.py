from django.db.models import Q, Sum, Count
from decimal import Decimal


class CobrancaConsultaService:
    """Service para consultas e filtros"""
    
    @staticmethod
    def filtrar_cobrancas(filtros):
        """
        Aplica filtros na queryset de cobranças
        """
        from financeiro.models import Cobranca
        
        queryset = Cobranca.objects.select_related('contrato').all()
        
        # Filtro por status
        status = filtros.get('status')
        if status and status != 'todos':
            queryset = queryset.filter(status=status)
        
        # Filtro por período
        mes = filtros.get('mes')
        if mes:
            try:
                queryset = queryset.filter(mes_referencia=int(mes))
            except (ValueError, TypeError):
                pass
        
        ano = filtros.get('ano')
        if ano:
            try:
                queryset = queryset.filter(ano_referencia=int(ano))
            except (ValueError, TypeError):
                pass
        
        # Filtro por contrato
        contrato_busca = filtros.get('contrato', '').strip()
        if contrato_busca:
            queryset = queryset.filter(
                Q(contrato__numero_contrato__icontains=contrato_busca) |
                Q(contrato__tipo_contrato__icontains=contrato_busca)
            )
        
        # Filtro por inquilino
        inquilino_busca = filtros.get('inquilino', '').strip()
        if inquilino_busca:
            queryset = queryset.filter(
                Q(contrato__inquilino__nome__icontains=inquilino_busca) |
                Q(contrato__inquilino__email__icontains=inquilino_busca)
            )
        
        return queryset.order_by('-ano_referencia', '-mes_referencia', '-data_vencimento')