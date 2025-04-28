"""
Serviço de Integração com Asaas

Este módulo fornece uma classe de serviço para encapsular todas as interações com a API do Asaas,
eliminando duplicação de código e centralizando a lógica de integração.
"""
import requests
import json
import traceback
from django.conf import settings

class AsaasService:
    """
    Classe de serviço para interação com a API Asaas.
    Centraliza todas as operações relacionadas ao Asaas em um único lugar.
    """

    def __init__(self):
        """Inicializa o serviço com as configurações do Django."""
        self.api_key = settings.ASAAS_API_KEY
        self.base_url = settings.ASAAS_API_URL
        self.sandbox = settings.ASAAS_SANDBOX

        if not self.api_key:
            print("❌ ERRO: ASAAS_API_KEY não configurada nas settings do Django.")
        if not self.base_url:
            print("❌ ERRO: ASAAS_API_URL não configurada nas settings do Django.")

    def cadastrar_cliente(self, cliente):
        """
        Cadastra um cliente no Asaas.

        Args:
            cliente: Objeto Cliente do Django com os dados do cliente

        Returns:
            str: ID do cliente no Asaas em caso de sucesso, None em caso de falha
        """
        endpoint = f"{self.base_url}/customers"

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

        try:
            response = self._fazer_requisicao("POST", endpoint, dados_cliente)

            if response and "id" in response:
                print("✅ Cliente criado com sucesso!")
                return response["id"]
            else:
                print("❌ Resposta não contém ID do cliente")
                return None

        except Exception as e:
            print(f"❌ Erro ao cadastrar cliente: {str(e)}")
            return None
        finally:
            print("=========== FIM DA INTEGRAÇÃO COM ASAAS - CADASTRAR CLIENTE ===========\n")

    def gerar_cobranca(self, asaas_id, valor, vencimento, nome, descricao=None):
        """
        Gera uma cobrança no Asaas.

        Args:
            asaas_id: ID do cliente no Asaas
            valor: Valor da cobrança
            vencimento: Data de vencimento (formato YYYY-MM-DD)
            nome: Nome do cliente
            descricao: Descrição da cobrança (opcional)

        Returns:
            dict: Dados da cobrança em caso de sucesso, dict com erro em caso de falha
        """
        endpoint = f"{self.base_url}/payments"

        print("\n=========== INÍCIO DA INTEGRAÇÃO COM ASAAS - GERAR COBRANÇA ===========")
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

            response = self._fazer_requisicao("POST", endpoint, dados_cobranca)

            if response and "id" in response:
                print("✅ Cobrança criada com sucesso!")
                return response
            else:
                print("❌ Resposta não contém ID da cobrança")
                return {"erro": response or "Resposta vazia do Asaas"}

        except Exception as e:
            print(f"❌ Erro ao gerar cobrança: {str(e)}")
            return {"erro": f"Erro ao gerar cobrança: {str(e)}"}
        finally:
            print("=========== FIM DA INTEGRAÇÃO COM ASAAS - GERAR COBRANÇA ===========\n")

    def _fazer_requisicao(self, metodo, endpoint, dados=None):
        """
        Método auxiliar para fazer requisições à API do Asaas.

        Args:
            metodo: Método HTTP (GET, POST, etc)
            endpoint: URL completa do endpoint
            dados: Dados a serem enviados (para POST, PUT)

        Returns:
            dict: Resposta da API em formato JSON, None em caso de erro
        """
        headers = {
            "Content-Type": "application/json",
            "access_token": self.api_key
        }

        print(f"🔑 Token API sendo usado: {self.api_key[:10]}...{self.api_key[-5:]}")
        print(f"🌐 URL: {endpoint}")

        try:
            print(f"⏳ Enviando requisição {metodo} para o Asaas...")

            if metodo == "GET":
                response = requests.get(endpoint, headers=headers, timeout=30)
            elif metodo == "POST":
                response = requests.post(endpoint, json=dados, headers=headers, timeout=30)
            elif metodo == "PUT":
                response = requests.put(endpoint, json=dados, headers=headers, timeout=30)
            elif metodo == "DELETE":
                response = requests.delete(endpoint, headers=headers, timeout=30)
            else:
                print(f"❌ Método HTTP não suportado: {metodo}")
                return None

            print(f"📊 Status code: {response.status_code}")

            try:
                resposta_json = response.json()
                print(f"🔍 Resposta do Asaas:")
                print(json.dumps(resposta_json, indent=2))

                # Check for errors in the response
                if response.status_code >= 400:
                    print(f"❌ Erro na API Asaas: {resposta_json.get('errors', 'Erro desconhecido')}")
                    return None

                return resposta_json

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
