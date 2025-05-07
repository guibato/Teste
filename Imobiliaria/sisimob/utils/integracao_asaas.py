import requests
import json
import traceback

ASAAS_API_KEY = "$aact_prod_000MzkwODA2MWY2OGM3MWRlMDU2NWM3MzJlNzZmNGZhZGY6OjZiZGJhZGY3LTE4M2ItNGRmOC1iYmVkLWE3ZWUyMmQ1OGE4MDo6JGFhY2hfYTYxYTIxMGYtNDdmMy00MWQwLWEzNzgtNmIzYjcxMzk5ZmM3"
ASAAS_URL = "https://www.asaas.com/api/v3/customers"

def cadastrar_cliente_no_asaas(cliente):
    """ Envia os dados do Cliente para o Asaas e retorna o ID do Asaas. """
    
    print("\n=========== INÍCIO DA INTEGRAÇÃO COM ASAAS - CADASTRAR CLIENTE ===========")
    print(f"Parâmetros recebidos:")
    print(f"- Nome: {cliente.nome}")
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
        "name": cliente.nome,
        "cpfCnpj": cliente.CPF,
        "email": cliente.email if cliente.email else "",
        "phone": cliente.celular if cliente.celular else cliente.telefone,
        "postalCode": cliente.cep,
        "address": cliente.endereco,
        "addressNumber": cliente.numero,
        "complement": cliente.complemento if cliente.complemento else "",
        "province": cliente.bairro if cliente.bairro else "",
        "city": cliente.cidade,
        "state": cliente.estado,
    }
    
    print(f"📌 Dados do cliente montados:")
    print(json.dumps(dados_cliente, indent=2))

    headers = {
        "Content-Type": "application/json",
        "access_token": ASAAS_API_KEY
    }
    
    print(f"🔑 Token API sendo usado: {ASAAS_API_KEY[:10]}...{ASAAS_API_KEY[-5:]}")
    print(f"🌐 URL: {ASAAS_URL}")
    
    try:
        print("⏳ Enviando requisição para o Asaas...")
        response = requests.post(ASAAS_URL, json=dados_cliente, headers=headers, timeout=30)
        print(f"📊 Status code: {response.status_code}")
        
        try:
            resposta_json = response.json()
            print(f"🔍 Resposta do Asaas:")
            print(json.dumps(resposta_json, indent=2))
            
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

def atualizar_cliente_no_asaas(cliente):
    if not cliente.asaas_id:
        print("⚠️ Cliente sem ID do Asaas. Não é possível atualizar.")
        return False

    url = f"https://www.asaas.com/api/v3/customers/{cliente.asaas_id}"
    headers = {
        "Content-Type": "application/json",
        "access_token": ASAAS_API_KEY
    }
    data = {
        "name": cliente.nome,
        "email": cliente.email or "",
        "phone": cliente.celular or cliente.telefone or "",
        "cpfCnpj": cliente.CPF if cliente.tipo_pessoa == 'F' else cliente.cnpj,
        "postalCode": cliente.cep,
        "address": cliente.endereco,
        "addressNumber": cliente.numero,
        "complement": cliente.complemento or "",
        "province": cliente.bairro or "",
        "city": cliente.cidade,
        "state": cliente.estado,
        "notificationDisabled": False,
    }

    print("⏳ Atualizando cliente no Asaas...")
    response = requests.put(url, json=data, headers=headers)
    print(f"📊 Status code: {response.status_code}")
    
    try:
        resposta_json = response.json()
        print(json.dumps(resposta_json, indent=2))
    except:
        print(response.text)

    if response.status_code == 200:
        print("✅ Cliente atualizado com sucesso!")
        return True
    else:
        print("❌ Falha ao atualizar cliente.")
        return False
