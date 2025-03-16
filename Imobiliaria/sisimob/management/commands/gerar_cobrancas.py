# manage.py
from django.core.management.base import BaseCommand
from sisimob.models import Contrato, Cobranca
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

class Command(BaseCommand):
    help = 'Gera cobranças para contratos ativos'

    def handle(self, *args, **kwargs):
        hoje = datetime.now().date()
        contratos_ativos = Contrato.objects.filter(
            ativo=True,
            data_inicio__lte=hoje,
            data_fim__gte=hoje
        )

        for contrato in contratos_ativos:
            # Define o mês e ano da próxima cobrança (ex.: mês vigente)
            mes_referencia = hoje.month
            ano_referencia = hoje.year
            data_vencimento = datetime(ano_referencia, mes_referencia, contrato.dia_pagamento).date()

            # Verifica se a cobrança já existe
            if not Cobranca.objects.filter(
                contrato=contrato,
                mes_referencia=mes_referencia,
                ano_referencia=ano_referencia
            ).exists():
                valor_total = (
                    float(contrato.valor_aluguel or 0) +
                    float(contrato.valor_condominio or 0) +
                    float(contrato.valor_iptu or 0) +
                    float(contrato.valor_outros or 0)
                )

                valor_total = round(valor_total, 2)  # Arredonda para duas casas decimais

                # Cria a cobrança com o valor total
                Cobranca.objects.create(
                    contrato=contrato,
                    mes_referencia=mes_referencia,
                    ano_referencia=ano_referencia,
                    data_vencimento=data_vencimento,
                    valor=valor_total  # Valor já calculado
                )
                self.stdout.write(f'Cobrança gerada para {contrato.imovel} - {mes_referencia}/{ano_referencia}')