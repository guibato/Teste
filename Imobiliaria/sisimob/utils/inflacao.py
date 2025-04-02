import requests
import datetime
from sisimob.models import IndiceInflacao
from django.apps import apps
from datetime import datetime, timedelta

def gerar_periodos_iniciais(fim_data=datetime.now()):
    """
    Gera uma string com períodos no formato 'YYYYMM' desde 1979-12 até a data atual.
    """
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
        
        # Avança para o próximo mês
        if current_month == 12:
            current_month = 1
            current_year += 1
        else:
            current_month += 1

    return "|".join(periodos)

def obter_indices_api(tipo):
    """
    Obtém os valores mensais do IPCA ou IGP-M de uma API pública.
    """
    if tipo == 'IPCA':
        periodos_str = gerar_periodos_iniciais()
        
        # Adicionando o print para ver os períodos gerados
        print(f"Períodos gerados para {tipo}: {periodos_str}")  # 👈 Aqui!
        
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
        try:
            for item in dados[0]['resultados'][0]['series'][0]['serie'].items():
                periodo = item[0]
                valor = item[1]
                
                # Skip non-numeric values
                if valor in ['...', 'N/A', '', None]:
                    print(f"Pulando valor não numérico para o período {periodo}: {valor}")
                    continue
                    
                try:
                    ano = int(periodo[:4])
                    mes = int(periodo[4:])
                    valor_float = float(valor) if valor else 0.0
                    indices.append({
                        "ano": ano,
                        "mes": mes,
                        "valor": valor_float
                    })
                except ValueError as e:
                    print(f"Erro ao converter dados para o período {periodo}: {e}")
                    
        except (IndexError, KeyError) as e:
            print(f"Erro ao processar IPCA: formato inesperado na resposta da API. Erro: {e}")
    elif tipo == 'IGPM':
        try:
            # Check if the data has a 'value' property (new format)
            if isinstance(dados, dict) and 'value' in dados:
                items = dados['value']
            else:
                items = dados
                
            for item in items:
                if isinstance(item, dict):
                    # Try different formats the API might return
                    if 'VALDATA' in item and 'VALVALOR' in item:
                        data_str = item['VALDATA']
                        valor = item['VALVALOR']
                    elif 'data' in item and 'valor' in item:
                        data_str = item['data']
                        valor = item['valor']
                    else:
                        # Skip metadata items
                        continue
                        
                    # Skip non-numeric values
                    if valor in ['...', 'N/A', '', None]:
                        print(f"Pulando valor não numérico: {valor}")
                        continue
                        
                    try:
                        # Parse the date (adjust format if needed)
                        if 'T' in data_str:  # ISO format like "2023-01-01T00:00:00"
                            data_str = data_str.split('T')[0]
                        
                        ano, mes, _ = data_str.split('-')
                        valor_float = float(valor)
                        indices.append({
                            "ano": int(ano),
                            "mes": int(mes),
                            "valor": valor_float
                        })
                    except (ValueError, TypeError) as e:
                        print(f"Erro ao converter dados para a data {data_str}, valor {valor}: {e}")
                        
                # Skip string or other non-dict items
                elif not isinstance(item, str):
                    print(f"Item com formato inesperado: {item}")
        except Exception as e:
            print(f"Erro ao processar IGPM: {e}")
            
    return indices


def atualizar_indices_inflacao():
    """
    Atualiza os índices de inflação no banco de dados.
    """
    try:
        # Use the correct model from your schema
        IndiceInflacao = apps.get_model('sisimob', 'IndiceInflacao')
        
        for tipo_indice in ['IPCA', 'IGPM']:
            try:
                print(f"Atualizando {tipo_indice}...")
                dados = obter_indices_api(tipo_indice)
                
                print(f"Encontrados {len(dados)} registros para {tipo_indice}")
                
                for item in dados:
                    ano = item['ano']
                    mes = item['mes']
                    valor = item['valor']
                    
                    # Criar uma data correta baseada no ano e mês
                    data_referencia = datetime(ano, mes, 1).date()
                    
                    try:
                        # Use os nomes de campo corretos do seu modelo
                        indice, created = IndiceInflacao.objects.get_or_create(
                            tipo=tipo_indice,  # Mudado de 'tipo' para 'nome'
                            data_referencia=data_referencia,  # Usando um objeto date em vez de ano/mes
                            defaults={'valor': valor}
                        )
                        
                        if not created and float(indice.valor) != float(valor):
                            indice.valor = valor
                            indice.save()
                    except Exception as e:
                        print(f"Erro ao salvar índice para {tipo_indice} - {ano}/{mes}: {e}")
                
                print(f"Dados do {tipo_indice} atualizados com sucesso.")
            except Exception as e:
                print(f"Erro ao processar {tipo_indice}: {str(e)}")
    except Exception as e:
        print(f"Erro ao inicializar atualização de índices: {e}")
        
    print("Índices atualizados com sucesso!")