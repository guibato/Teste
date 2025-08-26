"""Serviços de integração com o Asaas"""

from financeiro.models.cobranca import Cobranca
from financeiro.utils.cobrancas_asaas import gerar_cobranca


def enviar_cobrancas(mes: int, ano: int, stdout=None, stderr=None) -> None:
    """Envia cobranças do período para o Asaas.

    Args:
        mes: Mês de referência.
        ano: Ano de referência.
        stdout: Stream opcional para mensagens de sucesso.
        stderr: Stream opcional para mensagens de erro.
    """
    cobrancas = Cobranca.objects.filter(
        mes_referencia=mes,
        ano_referencia=ano,
        asaas_integracao__isnull=True,
    ).select_related("contrato")

    if not cobrancas.exists():
        if stdout:
            stdout.write("⚠️ Nenhuma cobrança pendente de envio encontrada.")
        return

    for cobranca in cobrancas:
        inquilinos = cobranca.contrato.inquilino.all()
        if not inquilinos:
            if stderr:
                stderr.write(
                    f"🚫 Nenhum inquilino associado ao contrato {cobranca.contrato.id}"
                )
            continue

        for inquilino in inquilinos:
            if not inquilino.asaas_id:
                if stderr:
                    stderr.write(
                        f"🚫 Inquilino {inquilino.nome} sem asaas_id para o contrato {cobranca.contrato.id}"
                    )
                continue

            if stdout:
                stdout.write(
                    f"🔹 Enviando cobrança de R$ {cobranca.valor} para {inquilino.nome} - Vencimento: {cobranca.data_vencimento}"
                )

            resposta = gerar_cobranca(
                asaas_id=inquilino.asaas_id,
                valor=cobranca.valor,
                vencimento=cobranca.data_vencimento.strftime("%Y-%m-%d"),
                nome=inquilino.nome,
            )

            if "erro" in resposta:
                if stderr:
                    stderr.write(f"❌ Erro ao gerar cobrança: {resposta['erro']}")
                continue

            cobranca.asaas_payment_id = resposta["id"]
            cobranca.asaas_boleto_url = resposta.get("bankSlipUrl")
            cobranca.asaas_pix_copia_cola = resposta.get("pix", {}).get("payload")
            cobranca.asaas_pix_url = resposta.get("pix", {}).get("qrCodeUrl")
            cobranca.asaas_codigo_barras = resposta.get("identificationField")
            cobranca.save()

            if stdout:
                stdout.write(
                    f"✅ Cobrança enviada com sucesso! ID Asaas: {resposta['id']}"
                )
            break