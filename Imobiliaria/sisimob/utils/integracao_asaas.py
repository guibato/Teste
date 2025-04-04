import requests

ASAAS_API_KEY = "$aact_hmlg_000MzkwODA2MWY2OGM3MWRlMDU2NWM3MzJlNzZmNGZhZGY6OjlmMjIzMzYzLTQyY2EtNGYwZS1hYmY4LWVhMGYyODU0YzQ0ZDo6JGFhY2hfMTJkOTc0YTAtZGExNC00MmExLTg1OWUtYTk3YzA3ZTYwMjgx"
ASAAS_URL = "https://sandbox.asaas.com/api/v3/customers"

def cadastrar_cliente_no_asaas(cliente):
    """ Envia os dados do Cliente para o Asaas e retorna o ID do Asaas. """
    
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

    headers = {
        "Content-Type": "application/json",
        "access_token": ASAAS_API_KEY
    }

    response = requests.post(ASAAS_URL, json=dados_cliente, headers=headers)

    try:
        resposta = response.json()  # Tenta converter a resposta para JSON
    except ValueError:
        print("Erro ao converter resposta para JSON:", response.text)
        return None  # Retorna None se a resposta não for JSON válido

    if response.status_code in [200, 201]:  # Cadastro bem-sucedido
        return resposta.get("id")  # Retorna o ID do cliente cadastrado no Asaas
    else:
        print("Erro ao cadastrar cliente:", resposta)
        return None  # Retorna None se houver erro