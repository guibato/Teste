import json
from datetime import datetime, date
import logging
logger = logging.getLogger(__name__)

def obter_valor_historico(historico_json, data_cobranca):

    logger.debug("Entrando em obter_valor_historico")
    logger.debug(f"Histórico recebido: {historico_json}")
    logger.debug(f"Data de cobrança: {data_cobranca}")
    """
    Retorna o valor vigente com base no histórico JSON e na data de cobrança.
    """

    # Garantir que data_cobranca seja do tipo date
    if isinstance(data_cobranca, datetime):
        data_cobranca = data_cobranca.date()

    # Carregar JSON se for string
    try:
        historico = json.loads(historico_json) if isinstance(historico_json, str) else historico_json
    except (json.JSONDecodeError, TypeError):
        return 0  # Valor padrão em caso de erro

    datas_valores = []

    for data_str, valor in historico.items():
        try:
            data_reajuste = datetime.strptime(data_str.strip(), "%Y-%m-%d").date()
            datas_valores.append((data_reajuste, float(valor)))
        except (ValueError, TypeError):
            continue  # Ignorar entradas inválidas

    # Ordenar por data
    datas_valores.sort(key=lambda x: x[0])

    if not datas_valores:
        return 0  # Sem histórico válido

    valor_vigente = datas_valores[0][1]  # Inicializa com o primeiro valor

    for data_reajuste, valor in datas_valores:
        if data_reajuste <= data_cobranca:
            valor_vigente = valor
        else:
            break  # As próximas datas são posteriores à data de cobrança

    return valor_vigente