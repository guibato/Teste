import requests
import os
from django.core.management.base import BaseCommand
from django.utils.timezone import make_aware
from datetime import datetime
from financeiro.models import Cobranca
from dotenv import load_dotenv


class Command(BaseCommand):
    help = 'Sincroniza o status de pagamento das cobranças com o Asaas'

    def handle(self, *args, **kwargs):
        self.stdout.write("Iniciando sincronização com Asaas...")

        # Carrega variáveis do .env
        load_dotenv()
        ASAAS_API_KEY = os.getenv('ASAAS_API_KEY')
        ASAAS_PAYMENTS_URL = os.getenv('ASAAS_PAYMENTS_URL')

        if not ASAAS_API_KEY or not ASAAS_PAYMENTS_URL:
            self.stderr.write("Chave da API ou URL do Asaas não configuradas corretamente.")
            return

        cobrancas = Cobranca.objects.exclude(asaas_id__isnull=True)

        headers = {
            'Content-Type': 'application/json',
            'access_token': ASAAS_API_KEY,
        }

        for cobranca in cobrancas:
            url = f'{ASAAS_PAYMENTS_URL}/{cobranca.asaas_id}'
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
