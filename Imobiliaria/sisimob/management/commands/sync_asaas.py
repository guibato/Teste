import requests
from django.core.management.base import BaseCommand
from django.utils.timezone import make_aware
from datetime import datetime
from decimal import Decimal
from sisimob.models import Cobranca  # ajuste conforme o nome do seu app

ASAAS_API_KEY = "$aact_prod_000MzkwODA2MWY2OGM3MWRlMDU2NWM3MzJlNzZmNGZhZGY6OjZiZGJhZGY3LTE4M2ItNGRmOC1iYmVkLWE3ZWUyMmQ1OGE4MDo6JGFhY2hfYTYxYTIxMGYtNDdmMy00MWQwLWEzNzgtNmIzYjcxMzk5ZmM3"
ASAAS_BASE_URL = 'https://www.asaas.com/api/v3'  # ou sandbox: https://sandbox.asaas.com/api/v3

class Command(BaseCommand):
    help = 'Sincroniza o status de pagamento das cobranças com o Asaas'

    def handle(self, *args, **kwargs):
        self.stdout.write("Iniciando sincronização com Asaas...")

        cobrancas = Cobranca.objects.exclude(asaas_id__isnull=True)

        headers = {
            'Content-Type': 'application/json',
            'access_token': ASAAS_API_KEY,
        }

        for cobranca in cobrancas:
            url = f'{ASAAS_BASE_URL}/payments/{cobranca.asaas_id}'
            response = requests.get(url, headers=headers)

            if response.status_code != 200:
                self.stderr.write(f'Erro ao consultar cobrança {cobranca.id}: {response.status_code}')
                continue

            dados = response.json()
            status_asaas = dados.get('status')
            data_pagamento = dados.get('paymentDate')

            if cobranca.asaas_status != status_asaas:
                cobranca.asaas_status = status_asaas

                if status_asaas == 'RECEIVED':
                    cobranca.status = 'paga'
                    if data_pagamento:
                        cobranca.data_pagamento = make_aware(datetime.strptime(data_pagamento, '%Y-%m-%d'))
                elif status_asaas == 'PENDING':
                    cobranca.status = 'pendente'
                    cobranca.data_pagamento = None
                elif status_asaas == 'OVERDUE':
                    cobranca.status = 'atrasada'
                elif status_asaas == 'CANCELED':
                    cobranca.status = 'cancelada'

                cobranca.save()
                self.stdout.write(f"Cobrança {cobranca.id} atualizada para {cobranca.status.upper()}")

        self.stdout.write("Sincronização concluída.")

