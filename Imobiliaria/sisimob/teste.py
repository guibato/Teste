import json
from datetime import date, datetime

def obter_valor_historico(historico_json, data_cobranca):
    if isinstance(data_cobranca, str):
        data_cobranca = date.fromisoformat(data_cobranca)
    elif isinstance(data_cobranca, datetime):
        data_cobranca = data_cobranca.date()

    try:
        historico = json.loads(historico_json) if isinstance(historico_json, str) else historico_json
    except (json.JSONDecodeError, TypeError):
        return 0

    datas_valores = []
    for data_str, valor in historico.items():
        try:
            data_reajuste = date.fromisoformat(data_str.strip())
            datas_valores.append((data_reajuste, float(valor)))
        except (ValueError, TypeError):
            continue

    datas_valores.sort(key=lambda x: x[0])

    if not datas_valores:
        return 0

    valor_vigente = datas_valores[0][1]

    for data_reajuste, valor in datas_valores:
        if data_reajuste <= data_cobranca:
            valor_vigente = valor
        else:
            break

    return valor_vigente


# Teste com seus dados reais
historico = '{"2024-04-09": 1710.03, "2025-04-30": 1856.85}'
data_cobranca = date(2025, 1, 9)  # 09/01/2025

valor = obter_valor_historico(historico, data_cobranca)
print(f"Valor correto esperado: R$ {valor:.2f}")