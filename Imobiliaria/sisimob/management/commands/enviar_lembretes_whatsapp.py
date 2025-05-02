# sisimob/management/commands/enviar_lembretes_cobranca.py
from datetime import date
from django.core.management.base import BaseCommand
from sisimob.models import Cobranca
from sisimob.services.notificacao import gerar_mensagem_cobranca
from sisimob.services.whatsapp import enviar_mensagem
from sisimob.utils.data import dia_util_anterior  # Importando o utilitário

class Command(BaseCommand):
    help = 'Envia lembretes de cobrança via WhatsApp considerando dias úteis'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Apenas exibe as mensagens que seriam enviadas, sem enviar de fato.'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("🟢 Iniciando envio de lembretes considerando dias úteis"))
        dry_run = options['dry_run']
        hoje = date.today()

        cobrancas = Cobranca.objects.filter(status='pendente')

        mensagens_enviadas = 0

        for cobranca in cobrancas:
            vencimento = cobranca.data_vencimento

            # Calcula as 3 datas de envio baseadas em dias úteis
            envio_10_dias = dia_util_anterior(vencimento, 10)
            envio_3_dias = dia_util_anterior(vencimento, 3)
            envio_no_dia = dia_util_anterior(vencimento, 0)  # Ajustado para o último dia útil anterior

            if hoje in [envio_10_dias, envio_3_dias, envio_no_dia]:
                contrato = cobranca.contrato
                inquilino = contrato.inquilino if contrato else None

                if not inquilino or not inquilino.celular:
                    self.stdout.write(f"⚠️ Cobrança {cobranca.id} sem inquilino ou telefone.")
                    continue

                mensagem = gerar_mensagem_cobranca(cobranca)
                numero = inquilino.celular
                nome = inquilino.nome
                mensagens_enviadas += 1

                if dry_run:
                    self.stdout.write(self.style.WARNING(
                        f"\n--- MODO TESTE ---\n"
                        f"Inquilino: {nome}\n"
                        f"Telefone: {numero}\n"
                        f"Mensagem:\n{mensagem}\n"
                        f"------------------"
                    ))
                else:
                    resposta = enviar_mensagem(numero, mensagem)
                    self.stdout.write(self.style.SUCCESS(
                        f"📤 Enviado para {numero}: {resposta.get('message', resposta)}"
                    ))

        if mensagens_enviadas == 0:
            self.stdout.write(self.style.WARNING("⚠️ Nenhuma cobrança com envio programado para hoje."))
