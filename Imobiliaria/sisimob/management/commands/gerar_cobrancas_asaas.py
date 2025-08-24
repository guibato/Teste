from django.core.management.base import BaseCommand
from financeiro.models.cobranca import Cobranca, AsaasIntegracao
from sisimob.utils.cobrancas_asaas import gerar_cobranca
from django.utils import timezone
 
class Command(BaseCommand):
    help = "Envia cobranças criadas para o Asaas com base no mês e ano de referência"
 
    def add_arguments(self, parser):
        parser.add_argument("mes", type=int, help="Mês de referência (1-12)")
        parser.add_argument("ano", type=int, help="Ano de referência (ex: 2025)")
 
    def handle(self, *args, **options):
        mes = options["mes"]
        ano = options["ano"]
 
        self.stdout.write(f"🔎 Buscando cobranças de {mes}/{ano}...")
 

        cobrancas = Cobranca.objects.filter(
            mes_referencia=mes,
            ano_referencia=ano,
            asaas_integracao__isnull=True,
        ).select_related("contrato")
 
        if not cobrancas.exists():
            self.stdout.write("⚠️ Nenhuma cobrança pendente de envio encontrada.")
            return
 
        for cobranca in cobrancas:
            inquilinos = cobranca.contrato.inquilino.all()
            if not inquilinos:
                self.stderr.write(f"🚫 Nenhum inquilino associado ao contrato {cobranca.contrato.id}")
                continue
 
            for inquilino in inquilinos:
                if not inquilino.asaas_id:
                    self.stderr.write(
                        f"🚫 Inquilino {inquilino.nome} sem asaas_id para o contrato {cobranca.contrato.id}"
                    )
                    continue

                self.stdout.write(
                    f"🔹 Enviando cobrança de R$ {cobranca.valor} para {inquilino.nome} - Vencimento: {cobranca.data_vencimento}"
                )

                resposta = gerar_cobranca(
                    asaas_id=inquilino.asaas_id,
                    valor=cobranca.valor,
                    vencimento=cobranca.data_vencimento.strftime("%Y-%m-%d"),
                    nome=inquilino.nome,
                )

                if "erro" in resposta:
                    self.stderr.write(f"❌ Erro ao gerar cobrança: {resposta['erro']}")
                    continue

                cobranca.asaas_payment_id = resposta["id"]
                cobranca.asaas_boleto_url = resposta.get("bankSlipUrl")
                cobranca.asaas_pix_copia_cola = resposta.get("pix", {}).get("payload")
                cobranca.asaas_pix_url = resposta.get("pix", {}).get("qrCodeUrl")
                cobranca.asaas_codigo_barras = resposta.get("identificationField")
                cobranca.save()

                self.stdout.write(f"✅ Cobrança enviada com sucesso! ID Asaas: {resposta['id']}")
                break
 
