from django.core.management.base import BaseCommand
from sisimob.signals import enviar_cobrancas_asaas


class Command(BaseCommand):
    help = "Solicita ao módulo financeiro o envio de cobranças para o Asaas com base no mês e ano de referência"

    def add_arguments(self, parser):
        parser.add_argument("mes", type=int, help="Mês de referência (1-12)")
        parser.add_argument("ano", type=int, help="Ano de referência (ex: 2025)")

    def handle(self, *args, **options):
        mes = options["mes"]
        ano = options["ano"]
        enviar_cobrancas_asaas.send(
            sender=self.__class__, mes=mes, ano=ano, stdout=self.stdout, stderr=self.stderr
        )
        self.stdout.write("✅ Solicitação enviada ao módulo financeiro")

        