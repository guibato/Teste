import datetime
from decimal import Decimal
from django.apps import apps


class CobrancaCalculadoraService:
    """Service para cálculos de valores de cobranças"""
    
    @staticmethod
    def calcular_valor_aluguel(contrato, mes=None, ano=None):
        """
        Calcula o valor do aluguel para o período
        Considera reajustes e alterações contratuais
        """
        if not contrato:
            return Decimal('0.00')
        
        # Valor base do contrato
        valor_base = getattr(contrato, 'valor_base', Decimal('0.00'))
        valor_aluguel = getattr(contrato, 'valor_aluguel', valor_base)
        
        if not valor_aluguel:
            return Decimal('0.00')
        
        # TODO: Implementar lógica de reajustes se necessário
        # if mes and ano:
        #     valor_aluguel = calcular_reajuste(contrato, valor_aluguel, mes, ano)
        
        return Decimal(str(valor_aluguel))
    
    @staticmethod
    def buscar_despesas_periodo(contrato, mes, ano):
        """
        Busca despesas ativas para o contrato no período especificado
        """
        try:
            Despesa = apps.get_model('financeiro', 'Despesa')
            data_referencia = datetime.date(ano, mes, 1)
            
            despesas = Despesa.objects.filter(
                contrato=contrato,
                is_ativa=True,
                paga_por='inquilino'
            )
            
            # Filtrar apenas despesas ativas no período
            despesas_ativas = [
                despesa for despesa in despesas 
                if despesa.parcela_ativa_em_data(data_referencia)
            ]
            
            return despesas_ativas
            
        except LookupError:
            # Modelo Despesa não encontrado
            return []
    
    @staticmethod
    def calcular_valor_despesas(despesas):
        """
        Calcula o valor total das despesas
        """
        if not despesas:
            return Decimal('0.00')
        
        valor_total = Decimal('0.00')
        for despesa in despesas:
            if hasattr(despesa, 'calcular_valor_parcela'):
                valor_total += despesa.calcular_valor_parcela()
            else:
                # Fallback se método não existir
                valor_total += getattr(despesa, 'valor', Decimal('0.00'))
        
        return valor_total
    
    @staticmethod
    def calcular_valor_total(valor_aluguel, despesas):
        """
        Calcula valor total: aluguel + despesas
        """
        valor_aluguel = Decimal(str(valor_aluguel or 0))
        valor_despesas = CobrancaCalculadoraService.calcular_valor_despesas(despesas)
        
        return valor_aluguel + valor_despesas
    
    @staticmethod
    def calcular_taxa_administracao(contrato, valor_aluguel):
        """
        Calcula valor da taxa de administração
        """
        if not contrato or not valor_aluguel:
            return Decimal('0.00')
        
        try:
            tipo_taxa = getattr(contrato, 'tipo_taxa', None)
            
            if tipo_taxa == 'percentual':
                percentual = getattr(contrato, 'valor_taxa_administracao_percentual', Decimal('0.00'))
                if percentual:
                    return (Decimal(str(valor_aluguel)) * percentual / Decimal('100')).quantize(Decimal('0.01'))
            
            elif tipo_taxa == 'fixo':
                valor_fixo = getattr(contrato, 'valor_taxa_administracao_fixo', Decimal('0.00'))
                return Decimal(str(valor_fixo or 0))
            
        except (AttributeError, TypeError):
            pass
        
        return Decimal('0.00')
    
    @staticmethod
    def calcular_valor_repasse(cobranca):
        """
        Calcula valor do repasse para o proprietário
        """
        if not cobranca:
            return Decimal('0.00')
        
        valor_total = cobranca.valor_total
        taxa_administracao = cobranca.calcular_valor_administracao()
        
        # Buscar despesas pagas pelo proprietário
        try:
            Despesa = apps.get_model('financeiro', 'Despesa')
            data_referencia = datetime.date(cobranca.ano_referencia, cobranca.mes_referencia, 1)
            
            despesas_proprietario = Despesa.objects.filter(
                contrato=cobranca.contrato,
                is_ativa=True,
                paga_por='proprietario'
            )
            
            valor_despesas_proprietario = sum(
                d.calcular_valor_parcela()
                for d in despesas_proprietario
                if d.parcela_ativa_em_data(data_referencia)
            )
            
        except LookupError:
            valor_despesas_proprietario = Decimal('0.00')
        
        valor_repasse = valor_total - taxa_administracao - valor_despesas_proprietario
        return max(valor_repasse, Decimal('0.00'))  # Não permitir repasse negativo