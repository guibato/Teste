import requests
import json
import traceback
import os

ASAAS_API_KEY = os.getenv('ASAAS_API_KEY')
ASAAS_PAYMENTS_URL = os.getenv("ASAAS_PAYMENTS_URL")

def gerar_cobranca(asaas_id, valor, vencimento, nome, descricao=None):
    """Cria uma cobrança no Asaas para um cliente existente com logs detalhados e retorno completo."""

    print("\n=========== INÍCIO DA INTEGRAÇÃO COM ASAAS ===========")
    print(f"Parâmetros recebidos:")
    print(f"- asaas_id: {asaas_id}")
    print(f"- valor: {valor}")
    print(f"- vencimento: {vencimento}")
    print(f"- nome: {nome}")
    print(f"- descricao: {descricao}")

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
            "interest": {"value": 1},
            "fine": {
                "value": 10,
                "type": "PERCENTAGE"
            },
            "paymentMethod": "BOLETO_PIX"
        }

        print(f"📌 Dados da cobrança montados:")
        print(json.dumps(dados_cobranca, indent=2))

        headers = {
            "Content-Type": "application/json",
            "access_token": ASAAS_API_KEY
        }

        print(f"🔑 Token API sendo usado: {ASAAS_API_KEY[:10]}...{ASAAS_API_KEY[-5:]}")
        print(f"🌐 URL: {ASAAS_PAYMENTS_URL}")

        try:
            print("⏳ Enviando requisição para o Asaas...")
            response = requests.post(ASAAS_PAYMENTS_URL, json=dados_cobranca, headers=headers, timeout=30)
            print(f"📊 Status code: {response.status_code}")

            try:
                resposta_json = response.json()
                print(f"🔍 Resposta do Asaas:")
                print(json.dumps(resposta_json, indent=2))

                if "id" in resposta_json:
                    print("✅ Cobrança criada com sucesso!")

                    retorno = {
                        "id": resposta_json.get("id"),
                        "bankSlipUrl": resposta_json.get("bankSlipUrl"),
                        "invoiceUrl": resposta_json.get("invoiceUrl"),
                        "identificationField": resposta_json.get("identificationField"),
                        "status": resposta_json.get("status"),
                        "pix": {
                            "payload": resposta_json.get("pix", {}).get("payload"),
                            "qrCodeUrl": resposta_json.get("pix", {}).get("qrCodeUrl"),
                            "qrCode": resposta_json.get("pix", {}).get("qrCode"),
                        }
                    }

                    return retorno
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