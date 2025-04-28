import requests
import json
import traceback

ASAAS_API_KEY = "$aact_prod_000MzkwODA2MWY2OGM3MWRlMDU2NWM3MzJlNzZmNGZhZGY6OmM0NmU2MWJmLTllYjctNGE0OC1hMDQ2LWY1NDU3YzhlMTY5ZTo6JGFhY2hfNzQ2MDIwYjktMGJmYi00ZGUwLWJhMDgtNGU0OTk4ZDA1NjNi"
ASAAS_URL = "https://www.asaas.com/api/v3/payments"

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
            "access_token": asaas_api_key
        }
        
        print(f"🔑 Token API sendo usado: {asaas_api_key[:10]}...{asaas_api_key[-5:]}")
        print(f"🌐 URL: {asaas_url}")
        
        # Tenta fazer a requisição com timeout
        try:
            print("⏳ Enviando requisição para o Asaas...")
            response = requests.post(asaas_url, json=dados_cobranca, headers=headers, timeout=30)
            print(f"📊 Status code: {response.status_code}")
            
            try:
                resposta_json = response.json()
                print(f"🔍 Resposta do Asaas:")
                print(json.dumps(resposta_json, indent=2))
                
                # Check for errors in the response
                if response.status_code >= 400:
                    print(f"❌ Erro na API Asaas: {resposta_json.get('errors', 'Erro desconhecido')}")
                    return {"erro": resposta_json}

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
