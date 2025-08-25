from datetime import date
from django.core.management.base import BaseCommand
from cadastro.models import Cobranca, LembreteEnviado
from sisimob.services.notificacao import gerar_mensagem_cobranca
from sisimob.services.whatsapp import enviar_mensagem
from sisimob.utils.data import dia_util_anterior


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

        def lembrete_ja_enviado(cobranca, tipo):
            return LembreteEnviado.objects.filter(cobranca=cobranca, tipo=tipo).exists()

        for cobranca in cobrancas:
            vencimento = cobranca.data_vencimento

            envio_10_dias = dia_util_anterior(vencimento, 10)
            envio_3_dias = dia_util_anterior(vencimento, 3)
            envio_no_dia = dia_util_anterior(vencimento, 0)

            envios = [
                ('10_dias', envio_10_dias),
                ('3_dias', envio_3_dias),
                ('vencimento', envio_no_dia),
            ]

            for tipo, data_envio in envios:
                if hoje == data_envio and not lembrete_ja_enviado(cobranca, tipo):
                    contrato = cobranca.contrato
                    if not contrato:
                        self.stdout.write(f"⚠️ Cobrança {cobranca.id} sem contrato associado.")
                        continue

                    inquilinos = contrato.inquilino.all()
                    if not inquilinos:
                        self.stdout.write(f"⚠️ Contrato {contrato.id} não possui inquilinos.")
                        continue

                    for inquilino in inquilinos:
                        if not inquilino.celular:
                            self.stdout.write(f"⚠️ Inquilino {inquilino.nome} sem telefone.")
                            continue

                        mensagem = gerar_mensagem_cobranca(cobranca)
                        numero = inquilino.celular
                        nome = inquilino.nome

                        if dry_run:
                            self.stdout.write(self.style.WARNING(
                                f"\n--- MODO TESTE ({tipo}) ---\n"
                                f"Inquilino: {nome}\n"
                                f"Telefone: {numero}\n"
                                f"Mensagem:\n{mensagem}\n"
                                f"------------------"
                            ))
                        else:
                            resposta = enviar_mensagem(numero, mensagem)
                            self.stdout.write(self.style.SUCCESS(
                                f"📤 Enviado para {numero} ({tipo}): {resposta.get('message', resposta)}"
                            ))
                            LembreteEnviado.objects.create(cobranca=cobranca, tipo=tipo)

                        mensagens_enviadas += 1

        if mensagens_enviadas == 0:
            self.stdout.write(self.style.WARNING("⚠️ Nenhuma cobrança com envio programado para hoje."))
