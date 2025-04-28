# utils.py
from sisimob.rent_calculations import calcular_aluguel_projetado
from decimal import Decimal
from datetime import date
from dateutil.relativedelta import relativedelta


def calcular_fator_acumulado_com_historico(contrato):
    from sisimob.models import IndiceInflacao
    historico = []
    data_inicio = contrato.data_inicio.replace(day=1)
    hoje = date.today().replace(day=1)
    fator_total = Decimal('1.00')

    while data_inicio + relativedelta(months=12) <= hoje:
        data_fim_ciclo = data_inicio + relativedelta(months=12) - relativedelta(days=1)
        indices = IndiceInflacao.objects.filter(
            tipo=contrato.fator_reajuste,
            data_referencia__gte=data_inicio,
            data_referencia__lte=data_fim_ciclo
        ).order_by('data_referencia')

        fator_ciclo = Decimal('1.00')
        for indice in indices:
            percentual = max(Decimal(str(indice.valor)), Decimal('0.00'))
            fator_ciclo *= (1 + percentual / 100)

        if fator_ciclo > 1:
            fator_total *= fator_ciclo
            historico.append({
                'referencia': data_fim_ciclo.strftime('%m/%Y'),
                'percentual': ((fator_ciclo - 1) * 100).quantize(Decimal('0.01'))
            })

        data_inicio += relativedelta(months=12)

    return fator_total.quantize(Decimal('0.0001')), historico


def calcular_valor_reajustado(contrato):
    return calcular_aluguel_projetado(contrato)
