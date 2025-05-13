from django.core.management.base import BaseCommand
from sisimob.models import Cliente
from sisimob.utils.cobrancas_asaas import criar_cobranca_asaas
import requests

ASAAS_API_KEY = os.getenv('ASAAS_API_KEY')
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

    if response.status_code in [200, 201]:
        return response.json()["id"]  # Retorna o ID do cliente cadastrado no Asaas
    else:
        return None  # Em caso de erro

class Command(BaseCommand):
    help = "Cadastra clientes no Asaas e cria cobranças"

    def handle(self, *args, **kwargs):
        clientes_nao_cadastrados = Cliente.objects.filter(asaas_id__isnull=True)

        if not clientes_nao_cadastrados.exists():
            self.stdout.write("Nenhum cliente novo para cadastrar.")
            return

        for cliente in clientes_nao_cadastrados:
            self.stdout.write(f"Cadastrando cliente: {cliente.nome}")
            cliente.asaas_id = cadastrar_cliente_no_asaas(cliente)
            cliente.save(update_fields=["asaas_id"])

            if cliente.asaas_id:
                # Criar uma cobrança de R$100,00 com vencimento em 10 dias
                from datetime import datetime, timedelta
                data_vencimento = (datetime.today() + timedelta(days=10)).strftime("%Y-%m-%d")

                cobranca_id = criar_cobranca_asaas(cliente, valor=100.00, vencimento=data_vencimento)

                if cobranca_id:
                    self.stdout.write(f"Cobrança criada com sucesso! ID: {cobranca_id}")
                else:
                    self.stdout.write("Erro ao criar cobrança.")