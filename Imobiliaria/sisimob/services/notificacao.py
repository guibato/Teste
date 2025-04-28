import locale
from datetime import date
from django.utils import timezone
from decimal import Decimal
from dateutil.relativedelta import relativedelta

# Configura o locale para o Brasil
locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')

def gerar_mensagem_cobranca(cobranca):
    agora = timezone.localtime()
    hora = agora.hour

    contrato = cobranca.contrato
    inquilino = contrato.inquilino
    nome = inquilino.primeiro_nome if inquilino and inquilino.primeiro_nome else "Cliente"

    # Saudação
    if hora < 12:
        saudacao = "Bom dia"
    elif hora < 18:
        saudacao = "Boa tarde"
    else:
        saudacao = "Boa noite"

    # Verbo flexionado
    hoje = date.today()
    vencimento = cobranca.data_vencimento
    if vencimento > hoje:
        verbo = "vencerá"
    elif vencimento == hoje:
        verbo = "vence"
    else:
        verbo = "venceu"

    # Valores monetários
    try:
        # Acessa o atributo .amount se o valor for do tipo Money
        valor_aluguel = contrato.valor_aluguel.amount if hasattr(contrato.valor_aluguel, 'amount') else contrato.valor_aluguel or Decimal("0.00")
        valor_total = cobranca.valor.amount if hasattr(cobranca.valor, 'amount') else cobranca.valor or Decimal("0.00")
        outros = valor_total - valor_aluguel

        # Formata os valores monetários com locale
        valor_aluguel_formatado = locale.currency(valor_aluguel, grouping=True, symbol=None)
        valor_total_formatado = locale.currency(valor_total, grouping=True, symbol=None)

    except Exception as e:
        raise ValueError(f"Erro ao processar valores monetários: {str(e)}")

    # Mensagem principal
    corpo = f"""{saudacao} {nome}, tudo bem?

O aluguel {verbo} em {vencimento.strftime('%d/%m/%y')}, no valor de R$ {valor_total_formatado}.

Aluguel : R$ {valor_aluguel_formatado}
"""

    # Despesas individuais
    despesas_texto = []
    for despesa in contrato.despesas.all():
        inicio = despesa.data_inicio
        num_parcelas = despesa.numero_parcelas or 1
        fim = inicio + relativedelta(months=num_parcelas) - relativedelta(days=1)

        if inicio <= vencimento <= fim:
            try:
                valor_parcela = (despesa.valor_total.amount if hasattr(despesa.valor_total, 'amount') else despesa.valor_total or Decimal("0.00")) / num_parcelas
            except ZeroDivisionError:
                valor_parcela = Decimal("0.00")

            # Formata o valor da parcela com locale
            valor_parcela_formatado = locale.currency(valor_parcela, grouping=True, symbol=None)

            # Calcula qual a parcela atual (considerando mês e ano)
            parcela_atual = (vencimento.year - inicio.year) * 12 + (vencimento.month - inicio.month) + 1

            # Formata com número da parcela
            descricao = f"{despesa.descricao} ({parcela_atual}/{num_parcelas})"
            despesas_texto.append(f"{descricao} : R$ {valor_parcela_formatado}")

    # Adiciona despesas à mensagem, se houver
    if despesas_texto:
        corpo += "\n" + "\n".join(despesas_texto)

    # Link do boleto
    if cobranca.asaas_boleto_url:
        corpo += f"\n\nSegue o link do boleto:\n{cobranca.asaas_boleto_url}"

    return corpo