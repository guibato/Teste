from django.core.management.base import BaseCommand
from financeiro.models import Cobranca as NovaCobranca
from core.models import Cobranca as CobrancaAntiga


class Command(BaseCommand):
    help = "Migra cobranças do app sisimob para o app financeiro"

    def handle(self, *args, **options):
        total_migradas = 0
        erros = 0

        for antiga in CobrancaAntiga.objects.all():
            try:
                nova = NovaCobranca(
                    contrato=antiga.contrato,
                    inquilino=antiga.inquilino,
                    mes_referencia=antiga.mes_referencia,
                    ano_referencia=antiga.ano_referencia,
                    data_vencimento=antiga.data_vencimento,
                    data_pagamento=antiga.data_pagamento,
                    descricao=antiga.descricao,
                    valor_total=antiga.valor,
                    status=antiga.status,
                    
                    # Campos Asaas
                    asaas_id=antiga.asaas_id,
                    boleto_url=antiga.asaas_boleto_url,
                    pix_copia_cola=antiga.asaas_pix_copia_cola,
                    pix_qrcode=antiga.asaas_pix_qr_code_base64,
                    pix_url=antiga.asaas_pix_url,
                    codigo_barras=antiga.asaas_codigo_barras,
                    fatura_url=antiga.asaas_url_fatura,
                    gateway_status=antiga.asaas_status,
                    

                    # Lembretes
                    lembrete_10_enviado=antiga.lembrete_10_enviado,
                    lembrete_3_enviado=antiga.lembrete_3_enviado,
                    lembrete_0_enviado=antiga.lembrete_0_enviado,

                    
                )

                nova.save()
                total_migradas += 1

            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Erro ao migrar cobrança ID {antiga.id}: {e}"))
                erros += 1

        self.stdout.write(self.style.SUCCESS(f"{total_migradas} cobranças migradas com sucesso."))
        if erros:
            self.stdout.write(self.style.WARNING(f"{erros} cobranças com erro."))
