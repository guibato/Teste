import locale
from datetime import date
from django.utils import timezone
from decimal import Decimal
from dateutil.relativedelta import relativedelta
from cadastro.models import Contrato, Cliente, Cobranca

# Configura o locale para o Brasil
locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')

def gerar_mensagem_cobranca(cobranca):
    agora = timezone.localtime()
    hora = agora.hour

    contrato = cobranca.contrato
    nome = cobranca.contrato.inquilino.first().primeiro_nome if cobranca.contrato.inquilino.exists() else "Cliente"

    
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
        # Obtem valor de aluguel e total
        valor_aluguel_raw = contrato.valor_aluguel_atual()
        valor_total_raw = cobranca.valor

        valor_aluguel = valor_aluguel_raw.amount if hasattr(valor_aluguel_raw, 'amount') else valor_aluguel_raw or Decimal("0.00")
        valor_total = valor_total_raw.amount if hasattr(valor_total_raw, 'amount') else valor_total_raw or Decimal("0.00")

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
        incluir_despesa = False
        descricao = despesa.descricao or despesa.get_tipo_display()

        if despesa.is_recorrente:
            # Verifica se a despesa recorrente deve aparecer no mês de vencimento
            delta_meses = (vencimento.year - despesa.data_inicio.year) * 12 + (vencimento.month - despesa.data_inicio.month)
            if despesa.periodicidade == 'mensal' and delta_meses >= 0:
                incluir_despesa = True
            elif despesa.periodicidade == 'trimestral' and delta_meses % 3 == 0 and delta_meses >= 0:
                incluir_despesa = True
            elif despesa.periodicidade == 'semestral' and delta_meses % 6 == 0 and delta_meses >= 0:
                incluir_despesa = True
            elif despesa.periodicidade == 'anual' and delta_meses % 12 == 0 and delta_meses >= 0:
                incluir_despesa = True
        else:
            # Despesas parceladas
            inicio = despesa.data_inicio
            num_parcelas = despesa.numero_parcelas or 1
            fim = inicio + relativedelta(months=num_parcelas) - relativedelta(days=1)
            if inicio <= vencimento <= fim:
                incluir_despesa = True

        if incluir_despesa:
            try:
                valor_parcela = despesa.calcular_valor_parcela()
            except ZeroDivisionError:
                valor_parcela = Decimal("0.00")

            valor_parcela_formatado = locale.currency(valor_parcela, grouping=True, symbol=None)

            # Número da parcela apenas se não for recorrente
            if not despesa.is_recorrente:
                parcela_atual = (vencimento.year - despesa.data_inicio.year) * 12 + (vencimento.month - despesa.data_inicio.month) + 1
                descricao += f" ({parcela_atual}/{despesa.numero_parcelas})"

            despesas_texto.append(f"{descricao} : R$ {valor_parcela_formatado}")


    # Adiciona despesas à mensagem, se houver
    if despesas_texto:
        corpo += "\n".join(despesas_texto)

    # Link do boleto
    if cobranca.asaas_boleto_url:
        corpo += f"\n\nSegue o link do boleto:\n{cobranca.asaas_boleto_url}"

    return corpo