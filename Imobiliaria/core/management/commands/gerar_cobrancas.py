from django.core.management.base import BaseCommand
from core.models import Cobranca
from core.utils.cobrancas_asaas import gerar_cobranca

class Command(BaseCommand):
    help = "Gera cobranças pendentes no Asaas a partir das Cobrancas do sistema"

    def handle(self, *args, **kwargs):
        cobrancas = Cobranca.objects.filter(
            status='pendente',
            contrato__inquilino__asaas_id__isnull=False,
            asaas_payment_id__isnull=True
        )

        for cobranca in cobrancas:
            inquilino = cobranca.contrato.inquilino
            self.stdout.write(f"🔹 Gerando cobrança para {inquilino.nome} ({cobranca.mes_referencia}/{cobranca.ano_referencia})")

            valor = float(cobranca.valor_boleto)  # já inclui despesas
            vencimento = cobranca.data_vencimento.strftime('%Y-%m-%d')

            resposta = gerar_cobranca(inquilino.asaas_id, valor, vencimento, inquilino.nome)

            if "erro" in resposta:
                self.stderr.write(f"❌ Erro: {resposta['erro']}")
                continue

            # Salva os dados do Asaas na cobrança
            cobranca.asaas_payment_id = resposta["id"]
            cobranca.asaas_boleto_url = resposta.get("bankSlipUrl")
            cobranca.asaas_pix_copia_cola = resposta.get("pix", {}).get("payload")
            cobranca.asaas_pix_url = resposta.get("pix", {}).get("qrCodeUrl")
            cobranca.asaas_codigo_barras = resposta.get("identificationField")
            cobranca.save()

            self.stdout.write(f"✅ Cobrança criada! ID: {resposta['id']}")
