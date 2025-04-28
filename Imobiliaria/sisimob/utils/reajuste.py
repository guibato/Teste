from decimal import Decimal
from dateutil.relativedelta import relativedelta
from datetime import date
from djmoney.money import Money
from sisimob.models import IndiceInflacao, Reajuste, Contrato

def calcular_reajuste(contrato):
    hoje = date.today()
    ultimo_reajuste = contrato.reajustes.filter(aprovado=True).order_by('-data_reajuste').first()
    data_base = ultimo_reajuste.data_reajuste if ultimo_reajuste else contrato.data_inicio

    if (hoje - data_base).days < 365:
        return None  # ainda não é hora de reajustar

    data_final = data_base + relativedelta(months=+11)

    indices = IndiceInflacao.objects.filter(
    tipo=contrato.fator_reajuste,
    data_referencia__gte=data_base.replace(day=1),  # <-- Aqui o ajuste
    data_referencia__lte=data_final.replace(day=1),
    ).order_by('data_referencia')


    fator_acumulado = Decimal('1.0')
    historico = []
    for indice in indices:
        taxa = Decimal(str(indice.valor)) / 100
        fator_acumulado *= (1 + taxa)
        historico.append({
            'referencia': indice.data_referencia.strftime('%m/%Y'),
            'percentual': indice.valor
        })

    if fator_acumulado < 1:
        fator_acumulado = Decimal('1.0')  # sem deflação

    # Tratamento correto para objetos Money
    if contrato.valor_aluguel and isinstance(contrato.valor_aluguel, Money):
        valor_base_amount = contrato.valor_aluguel.amount
        moeda = contrato.valor_aluguel.currency
    elif contrato.valor_pacote and isinstance(contrato.valor_pacote, Money):
        valor_base_amount = contrato.valor_pacote.amount
        moeda = contrato.valor_pacote.currency
    else:
        # Fallback para um valor padrão
        valor_base_amount = Decimal('0.00')
        moeda = 'BRL'

    # Garante que valor_base_amount seja Decimal
    if not isinstance(valor_base_amount, Decimal):
        try:
            valor_base_amount = Decimal(str(valor_base_amount))
        except decimal.InvalidOperation:
            valor_base_amount = Decimal('0.00')

    # Cálculo do novo valor
    novo_valor_amount = valor_base_amount * fator_acumulado
    novo_valor = Money(novo_valor_amount.quantize(Decimal('0.01')), moeda)

    return {
        'fator': fator_acumulado.quantize(Decimal('0.0001')),
        'valor': novo_valor,
        'data_base': data_base,
        'historico': historico
    }