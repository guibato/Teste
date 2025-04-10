import requests
import json
import traceback

ASAAS_API_KEY = "$aact_hmlg_000MzkwODA2MWY2OGM3MWRlMDU2NWM3MzJlNzZmNGZhZGY6OjlmMjIzMzYzLTQyY2EtNGYwZS1hYmY4LWVhMGYyODU0YzQ0ZDo6JGFhY2hfMTJkOTc0YTAtZGExNC00MmExLTg1OWUtYTk3YzA3ZTYwMjgx"
ASAAS_URL = "https://sandbox.asaas.com/api/v3/payments"

def gerar_cobranca(asaas_id, valor, vencimento, nome, descricao=None):
    """Cria uma cobrança no Asaas para um cliente existente com logs detalhados."""
    
    print("\n=========== INÍCIO DA INTEGRAÇÃO COM ASAAS ===========")
    print(f"Parâmetros recebidos:")
    print(f"- asaas_id: {asaas_id}")
    print(f"- valor: {valor}")
    print(f"- vencimento: {vencimento}")
    print(f"- nome: {nome}")
    print(f"- descricao: {descricao}")
    
    # Verificação de parâmetros
    if not asaas_id:
        print("❌ ERRO: asaas_id está vazio!")
        return {"erro": "ID do cliente Asaas não fornecido"}
    
    try:
        dados_cobranca = {
            "customer": asaas_id,
            "billingType": "BOLETO",
            "value": float(valor),
            "dueDate": vencimento,
            "description": descricao if descricao else f"Aluguel {vencimento[5:7]}/{vencimento[0:4]}",
            "name": nome,
            "interest": { "value": 1 },
            "fine": {
                "value": 10,
                "type": "PERCENTAGE"
            }
        }
        
        print(f"📌 Dados da cobrança montados:")
        print(json.dumps(dados_cobranca, indent=2))

        headers = {
            "Content-Type": "application/json",
            "access_token": ASAAS_API_KEY
        }
        
        print(f"🔑 Token API sendo usado: {ASAAS_API_KEY[:10]}...{ASAAS_API_KEY[-5:]}")
        print(f"🌐 URL: {ASAAS_URL}")
        
        # Tenta fazer a requisição com timeout
        try:
            print("⏳ Enviando requisição para o Asaas...")
            response = requests.post(ASAAS_URL, json=dados_cobranca, headers=headers, timeout=30)
            print(f"📊 Status code: {response.status_code}")
            
            try:
                resposta_json = response.json()
                print(f"🔍 Resposta do Asaas:")
                print(json.dumps(resposta_json, indent=2))
                
                # Verifica se a resposta contém um id de cobrança
                if "id" in resposta_json:
                    print("✅ Cobrança criada com sucesso!")
                    return resposta_json
                else:
                    print("❌ Resposta não contém ID da cobrança")
                    return {"erro": resposta_json}
                
            except json.JSONDecodeError:
                print("❌ Erro ao decodificar JSON da resposta")
                print(f"Conteúdo da resposta: {response.text}")
                return {"erro": "Resposta inválida do Asaas"}
            
        except requests.exceptions.Timeout:
            print("❌ Timeout na requisição")
            return {"erro": "Timeout na comunicação com o Asaas"}
        except requests.exceptions.ConnectionError:
            print("❌ Erro de conexão")
            return {"erro": "Erro de conexão com o Asaas"}
        except Exception as e:
            print(f"❌ Erro na requisição: {str(e)}")
            traceback.print_exc()
            return {"erro": f"Erro na comunicação com o Asaas: {str(e)}"}
            
    except Exception as e:
        print(f"❌ Erro ao preparar dados: {str(e)}")
        traceback.print_exc()
        return {"erro": f"Erro ao preparar dados para o Asaas: {str(e)}"}
    finally:
        print("=========== FIM DA INTEGRAÇÃO COM ASAAS ===========\n")