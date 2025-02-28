import requests
from datetime import datetime
from sisimob.models import IndiceInflacao
from django.apps import apps

def obter_indices_api(tipo):
    """
    Obtém os valores mensais do IPCA ou IGP-M de uma API pública.
    """
    if tipo == 'IPCA':
        url = "https://servicodados.ibge.gov.br/api/v3/agregados/1737/periodos/197912|198001|198002|198003|198004|198005|198006|198007|198008|198009|198010|198011|198012|198101|198102|198103|198104|198105|198106|198107|198108|198109|198110|198111|198112|198201|198202|198203|198204|198205|198206|198207|198208|198209|198210|198211|198212|198301|198302|198303|198304|198305|198306|198307|198308|198309|198310|198311|198312|198401|198402|198403|198404|198405|198406|198407|198408|198409|198410|198411|198412|198501|198502|198503|198504|198505|198506|198507|198508|198509|198510|198511|198512|198601|198602|198603|198604|198605|198606|198607|198608|198609|198610|198611|198612|198701|198702|198703|198704|198705|198706|198707|198708|198709|198710|198711|198712|198801|198802|198803|198804|198805|198806|198807|198808|198809|198810|198811|198812|198901|198902|198903|198904|198905|198906|198907|198908|198909|198910|198911|198912|199001|199002|199003|199004|199005|199006|199007|199008|199009|199010|199011|199012|199101|199102|199103|199104|199105|199106|199107|199108|199109|199110|199111|199112|199201|199202|199203|199204|199205|199206|199207|199208|199209|199210|199211|199212|199301|199302|199303|199304|199305|199306|199307|199308|199309|199310|199311|199312|199401|199402|199403|199404|199405|199406|199407|199408|199409|199410|199411|199412|199501|199502|199503|199504|199505|199506|199507|199508|199509|199510|199511|199512|199601|199602|199603|199604|199605|199606|199607|199608|199609|199610|199611|199612|199701|199702|199703|199704|199705|199706|199707|199708|199709|199710|199711|199712|199801|199802|199803|199804|199805|199806|199807|199808|199809|199810|199811|199812|199901|199902|199903|199904|199905|199906|199907|199908|199909|199910|199911|199912|200001|200002|200003|200004|200005|200006|200007|200008|200009|200010|200011|200012|200101|200102|200103|200104|200105|200106|200107|200108|200109|200110|200111|200112|200201|200202|200203|200204|200205|200206|200207|200208|200209|200210|200211|200212|200301|200302|200303|200304|200305|200306|200307|200308|200309|200310|200311|200312|200401|200402|200403|200404|200405|200406|200407|200408|200409|200410|200411|200412|200501|200502|200503|200504|200505|200506|200507|200508|200509|200510|200511|200512|200601|200602|200603|200604|200605|200606|200607|200608|200609|200610|200611|200612|200701|200702|200703|200704|200705|200706|200707|200708|200709|200710|200711|200712|200801|200802|200803|200804|200805|200806|200807|200808|200809|200810|200811|200812|200901|200902|200903|200904|200905|200906|200907|200908|200909|200910|200911|200912|201001|201002|201003|201004|201005|201006|201007|201008|201009|201010|201011|201012|201101|201102|201103|201104|201105|201106|201107|201108|201109|201110|201111|201112|201201|201202|201203|201204|201205|201206|201207|201208|201209|201210|201211|201212|201301|201302|201303|201304|201305|201306|201307|201308|201309|201310|201311|201312|201401|201402|201403|201404|201405|201406|201407|201408|201409|201410|201411|201412|201501|201502|201503|201504|201505|201506|201507|201508|201509|201510|201511|201512|201601|201602|201603|201604|201605|201606|201607|201608|201609|201610|201611|201612|201701|201702|201703|201704|201705|201706|201707|201708|201709|201710|201711|201712|201801|201802|201803|201804|201805|201806|201807|201808|201809|201810|201811|201812|201901|201902|201903|201904|201905|201906|201907|201908|201909|201910|201911|201912|202001|202002|202003|202004|202005|202006|202007|202008|202009|202010|202011|202012|202101|202102|202103|202104|202105|202106|202107|202108|202109|202110|202111|202112|202201|202202|202203|202204|202205|202206|202207|202208|202209|202210|202211|202212|202301|202302|202303|202304|202305|202306|202307|202308|202309|202310|202311|202312|202401|202402|202403|202404|202405|202406|202407|202408|202409|202410|202411|202412|202501/variaveis/63?localidades=N1[all]"
    elif tipo == 'IGPM':
        url = "http://ipeadata.gov.br/api/odata4/ValoresSerie(SERCODIGO='IGP12_IGPMG12')?$format=json"
    else:
        raise ValueError("Tipo de índice inválido. Use 'IPCA' ou 'IGPM'.")

    print(f"Buscando dados da API: {url}")
    response = requests.get(url)

    if response.status_code == 200:
        dados = response.json()
        indices = []

        if tipo == 'IPCA':
            # Processamento específico para IPCA
            for item in dados[0]['resultados'][0]['series'][0]['serie'].items():
                periodo = item[0]  # Exemplo: "202401"
                valor = item[1]    # Exemplo: "0.54"

                # Extrair ano e mês do período
                ano = int(periodo[:4])
                mes = int(periodo[4:])

                # Converter o valor para float
                try:
                    valor_float = float(valor)
                except ValueError:
                    print(f"Erro ao converter valor para float: {valor}")
                    continue

                indices.append({
                    "ano": ano,
                    "mes": mes,
                    "valor": valor_float
                })

        elif tipo == 'IGPM':
            # Processamento específico para IGP-M
            for item in dados['value']:  # Lista de registros
                data = item['VALDATA']  # Exemplo: "1989-07-01T00:00:00-03:00" ou "1989"
                valor = item['VALVALOR']  # Exemplo: 35.91

                try:
                    # Verificar o formato da data
                    if len(data) == 4:  # Apenas o ano
                        ano = int(data)
                        mes = 1  # Assumimos janeiro como padrão
                    else:
                        # Remover o deslocamento de fuso horário
                        data_sem_fuso = data.split('-')[0] + '-' + data.split('-')[1] + '-' + data.split('-')[2].split('T')[0]
                        data_obj = datetime.strptime(data_sem_fuso, "%Y-%m-%d")
                        ano = data_obj.year
                        mes = data_obj.month

                    # Converter o valor para float
                    valor_float = float(valor)

                    indices.append({
                        "ano": ano,
                        "mes": mes,
                        "valor": valor_float
                    })
                except Exception as e:
                    print(f"Erro ao processar registro: {item}. Detalhes: {e}")
                    continue

        return indices
    else:
        raise Exception(f"Erro ao obter os dados do {tipo}: Status Code {response.status_code}")

def atualizar_indices_inflacao():

    IndiceInflacao = apps.get_model('sisimob', 'IndiceInflacao')
    """
    Atualiza o banco de dados com os valores mensais do IPCA e IGP-M.
    """
    for tipo in ['IPCA', 'IGPM']:
        try:
            print(f"Buscando dados do {tipo}...")
            dados = obter_indices_api(tipo)

            for item in dados:
                ano = item['ano']
                mes = item['mes']
                valor = item['valor']

                print(f"Processando {tipo} - Ano: {ano}, Mês: {mes}, Valor: {valor}%")

                # Verifica se o registro já existe
                indice, created = IndiceInflacao.objects.get_or_create(
                    tipo=tipo,
                    ano=ano,
                    mes=mes,
                    defaults={'valor': valor}
                )

                # Se o registro já existir, atualiza o valor
                if not created and indice.valor != valor:
                    print(f"Atualizando valor de {tipo} - Ano: {ano}, Mês: {mes}")
                    indice.valor = valor
                    indice.save()

            print(f"Dados do {tipo} atualizados com sucesso.")
        except Exception as e:
            print(f"Erro ao atualizar os dados do {tipo}: {e}")

import requests
from datetime import datetime

def obter_indices_api(tipo):
    # Implementação da função (já fornecida anteriormente)
    pass