from datetime import date, timedelta
from django.core.management.base import BaseCommand
from sisimob.models import Cobranca
from sisimob.services.notificacao import gerar_mensagem_cobranca
from sisimob.services.whatsapp import enviar_mensagem

class Command(BaseCommand):
    help = 'Envia lembretes de cobrança via WhatsApp'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Apenas exibe as mensagens que seriam enviadas, sem enviar de fato.'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("🟢 Comando iniciado"))
        dry_run = options['dry_run']
        hoje = date.today()
        dias_alerta = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30]

        cobrancas_encontradas = 0

        for dias in dias_alerta:
            data_alvo = hoje + timedelta(days=dias)
            cobrancas = Cobranca.objects.filter(data_vencimento=data_alvo, status='pendente')

            for cobranca in cobrancas:
                contrato = cobranca.contrato
                inquilino = contrato.inquilino if contrato else None

                if not inquilino or not inquilino.celular:
                    self.stdout.write(f"⚠️ Cobrança {cobranca.id} sem inquilino ou telefone.")
                    continue

                telefone = inquilino.celular
                nome = inquilino.nome


                numero = telefone
                mensagem = gerar_mensagem_cobranca(cobranca)
                cobrancas_encontradas += 1

                if dry_run:
                    self.stdout.write(self.style.WARNING(
                        f"\n--- MODO TESTE (sem envio) ---\n"
                        f"Inquilino: {nome}\n"
                        f"Telefone: {numero}\n"
                        f"Mensagem:\n{mensagem}\n"
                        f"------------------------------"
                    ))
                else:
                    resposta = enviar_mensagem(numero, mensagem)
                    self.stdout.write(self.style.SUCCESS(
                        f"📤 Enviado para {numero}: {resposta.get('message', resposta)}"
                    ))

        if cobrancas_encontradas == 0:
            self.stdout.write(self.style.WARNING("⚠️ Nenhuma cobrança pendente encontrada para os próximos 0, 3 ou 10 dias."))
