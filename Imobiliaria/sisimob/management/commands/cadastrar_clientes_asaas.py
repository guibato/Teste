from django.core.management.base import BaseCommand
from sisimob.models import Cliente
from sisimob.utils.cobrancas_asaas import gerar_cobranca
import requests
from datetime import datetime, timedelta
import logging
import requests

ASAAS_API_KEY = "$aact_prod_000MzkwODA2MWY2OGM3MWRlMDU2NWM3MzJlNzZmNGZhZGY6OmM0NmU2MWJmLTllYjctNGE0OC1hMDQ2LWY1NDU3YzhlMTY5ZTo6JGFhY2hfNzQ2MDIwYjktMGJmYi00ZGUwLWJhMDgtNGU0OTk4ZDA1NjNi"
ASAAS_URL = "https://www.asaas.com/api/v3/customers"
logger = logging.getLogger(__name__)

def cadastrar_cliente_no_asaas(cliente):
    """ Envia os dados do Cliente para o Asaas e retorna o ID do Asaas. """

    if not cliente.nome_exibicao or not (cliente.cnpj or cliente.CPF):
        logger.warning(f"Dados incompletos para o cliente: {cliente.id} - {cliente}")
        return None

    cpf_cnpj = cliente.cnpj if cliente.tipo_pessoa == 'J' else cliente.CPF

    dados_cliente = {
        "name": cliente.nome_exibicao.strip(),
        "cpfCnpj": cpf_cnpj.strip(),
        "email": (cliente.email or "").strip(),
        "phone": (cliente.celular or cliente.telefone or "").strip(),
        "postalCode": (cliente.cep or "").strip(),
        "address": (cliente.endereco or "").strip(),
        "addressNumber": (cliente.numero or "").strip(),
        "complement": (cliente.complemento or "").strip(),
        "province": (cliente.bairro or "").strip(),
        "city": (cliente.cidade or "").strip(),
        "state": (cliente.estado or "").strip(),
    }

    headers = {
        "Content-Type": "application/json",
        "access_token": ASAAS_API_KEY
    }

    try:
        response = requests.post(ASAAS_URL, json=dados_cliente, headers=headers)
        response_data = response.json()
    except Exception as e:
        logger.error(f"Erro ao conectar com o Asaas: {e}")
        return None

    if response.status_code in [200, 201] and "id" in response_data:
        logger.info(f"Cliente cadastrado com sucesso no Asaas: {cliente.nome_exibicao} - ID: {response_data['id']}")
        return response_data["id"]
    else:
        logger.error(f"Erro ao cadastrar cliente no Asaas ({cliente.nome_exibicao}): {response.status_code} - {response.text}")
        return None
class Command(BaseCommand):
    help = "Cadastra clientes no Asaas e cria cobranças"

    def handle(self, *args, **kwargs):
        clientes_nao_cadastrados = Cliente.objects.filter(asaas_id__isnull=True)

        if not clientes_nao_cadastrados.exists():
            self.stdout.write("Nenhum cliente novo para cadastrar.")
            return

        for cliente in clientes_nao_cadastrados:
            self.stdout.write(f"Cadastrando cliente: {cliente.nome_exibicao}")
            asaas_id = cadastrar_cliente_no_asaas(cliente)
            if asaas_id:
                cliente.asaas_id = asaas_id
                cliente.save(update_fields=["asaas_id"])
                self.stdout.write(self.style.SUCCESS(f"✅ Cliente {cliente.nome_exibicao} cadastrado com sucesso."))
            else:
                self.stdout.write(self.style.ERROR(f"❌ Falha ao cadastrar {cliente.nome_exibicao}."))
