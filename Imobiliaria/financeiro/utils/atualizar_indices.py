import requests
from datetime import datetime
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from financeiro.models import IndiceInflacao  # ✅ Import direto agora que está no app correto


def gerar_periodos_iniciais(fim_data=datetime.now()):
    start_year = 1979
    start_month = 12
    end_year = fim_data.year
    end_month = fim_data.month

    periodos = []
    current_year = start_year
    current_month = start_month

    while (current_year < end_year) or (current_year == end_year and current_month <= end_month):
        periodo = f"{current_year:04d}{current_month:02d}"
        periodos.append(periodo)
        if current_month == 12:
            current_month = 1
            current_year += 1
        else:
            current_month += 1

    return "|".join(periodos)


def obter_indices_api(tipo):
    if tipo == 'IPCA':
        periodos_str = gerar_periodos_iniciais()
        url = f"https://servicodados.ibge.gov.br/api/v3/agregados/1737/periodos/{periodos_str}/variaveis/63?localidades=N1[all]"
    elif tipo == 'IGPM':
        url = "http://ipeadata.gov.br/api/odata4/ValoresSerie(SERCODIGO='IGP12_IGPMG12')?$format=json"
    else:
        raise ValueError("Tipo de índice inválido. Use 'IPCA' ou 'IGPM'.")

    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Erro ao buscar {tipo}: Status {response.status_code}")
    return processar_dados(tipo, response.json())


def processar_dados(tipo, dados):
    indices = []
    if tipo == 'IPCA':
        for periodo, valor in dados[0]['resultados'][0]['series'][0]['serie'].items():
            if valor in ['...', 'N/A', '', None]:
                continue
            try:
                ano = int(periodo[:4])
                mes = int(periodo[4:])
                valor_float = float(valor)
                indices.append({
                    "ano": ano,
                    "mes": mes,
                    "valor": valor_float
                })
            except ValueError:
                continue
    elif tipo == 'IGPM':
        items = dados['value'] if 'value' in dados else dados
        for item in items:
            try:
                data_str = item.get('VALDATA') or item.get('data')
                valor = item.get('VALVALOR') or item.get('valor')
                if not data_str or valor in ['...', 'N/A', '', None]:
                    continue
                data = datetime.fromisoformat(data_str.split('T')[0])
                indices.append({
                    "ano": data.year,
                    "mes": data.month,
                    "valor": float(valor)
                })
            except Exception:
                continue
    return indices


def atualizar_indices_inflacao():
    for tipo_indice in ['IPCA', 'IGPM']:
        try:
            print(f"Atualizando {tipo_indice}...")
            dados = obter_indices_api(tipo_indice)
            for item in dados:
                data_ref = datetime(item['ano'], item['mes'], 1).date()
                valor = Decimal(str(item['valor']))
                indice, created = IndiceInflacao.objects.get_or_create(
                    tipo=tipo_indice,
                    data_referencia=data_ref,
                    defaults={'valor': valor}
                )
                if not created and float(indice.valor) != float(valor):
                    indice.valor = valor
                    indice.save()
            print(f"{tipo_indice} atualizado com sucesso.")
        except Exception as e:
            print(f"Erro ao atualizar {tipo_indice}: {e}")

    print("Indices de inflação atualizados com sucesso.")