import requests
import json
import traceback

ASAAS_API_KEY = "$aact_prod_000MzkwODA2MWY2OGM3MWRlMDU2NWM3MzJlNzZmNGZhZGY6OmM0NmU2MWJmLTllYjctNGE0OC1hMDQ2LWY1NDU3YzhlMTY5ZTo6JGFhY2hfNzQ2MDIwYjktMGJmYi00ZGUwLWJhMDgtNGU0OTk4ZDA1NjNi"
ASAAS_URL = "https://www.asaas.com/api/v3/customers"

def cadastrar_cliente_no_asaas(cliente):
    """ Envia os dados do Cliente para o Asaas e retorna o ID do Asaas. """
    
    print("\n=========== INÍCIO DA INTEGRAÇÃO COM ASAAS - CADASTRAR CLIENTE ===========")
    print(f"Parâmetros recebidos:")
    print(f"- Nome: {cliente.nome_exibicao}")
    print(f"- CPF: {cliente.CPF}")
    print(f"- Email: {cliente.email}")
    print(f"- Celular: {cliente.celular}")
    print(f"- Telefone: {cliente.telefone}")
    print(f"- CEP: {cliente.cep}")
    print(f"- Endereço: {cliente.endereco}")
    print(f"- Número: {cliente.numero}")
    print(f"- Complemento: {cliente.complemento}")
    print(f"- Bairro: {cliente.bairro}")
    print(f"- Cidade: {cliente.cidade}")
    print(f"- Estado: {cliente.estado}")
    
    dados_cliente = {
        "name": cliente.nome_exibicao,
        "cpfCnpj": cliente.CPF,
        "email": cliente.email if cliente.email else "",
        "phone": cliente.celular if cliente.celular else cliente.telefone,
        "postalCode": cliente.cep,
        "address": cliente.endereco,
        "addressNumber": cliente.numero,
        "complement": cliente.complemento if cliente.complemento else "",
        "province": cliente.bairro if cliente.bairro else "",
        # "city": cliente.cidade, # Asaas API might infer city from postalCode
        # "state": cliente.estado, # Asaas API might infer state from postalCode
        # Ensure required fields match Asaas documentation
    }
    
    print(f"📌 Dados do cliente montados:")
    print(json.dumps(dados_cliente, indent=2))

    headers = {
        "Content-Type": "application/json",
        "access_token": asaas_api_key
    }
    
    print(f"🔑 Token API sendo usado: {asaas_api_key[:10]}...{asaas_api_key[-5:]}")
    print(f"🌐 URL: {asaas_url}")
    
    try:
        print("⏳ Enviando requisição para o Asaas...")
        response = requests.post(asaas_url, json=dados_cliente, headers=headers, timeout=30)
        print(f"📊 Status code: {response.status_code}")
        
        try:
            resposta_json = response.json()
            print(f"🔍 Resposta do Asaas:")
            print(json.dumps(resposta_json, indent=2))
            
            # Check for errors in the response
            if response.status_code >= 400:
                print(f"❌ Erro na API Asaas: {resposta_json.get('errors', 'Erro desconhecido')}")
                return None

            # Verifica se a resposta contém um id de cliente
            if "id" in resposta_json:
                print("✅ Cliente criado com sucesso!")
                return resposta_json["id"]
            else:
                print("❌ Resposta não contém ID do cliente")
                return None
            
        except json.JSONDecodeError:
            print("❌ Erro ao decodificar JSON da resposta")
            print(f"Conteúdo da resposta: {response.text}")
            return None
        
    except requests.exceptions.Timeout:
        print("❌ Timeout na requisição")
        return None
    except requests.exceptions.ConnectionError:
        print("❌ Erro de conexão")
        return None
    except Exception as e:
        print(f"❌ Erro na requisição: {str(e)}")
        traceback.print_exc()
        return None
    finally:
        print("=========== FIM DA INTEGRAÇÃO COM ASAAS - CADASTRAR CLIENTE ===========\n")
