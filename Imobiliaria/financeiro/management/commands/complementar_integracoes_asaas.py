# financeiro/management/commands/complementar_integracoes_asaas.py
from django.core.management.base import BaseCommand
from django.db import models

from financeiro.models.cobranca import AsaasIntegracao
from financeiro.utils.asaas_utils import atualizar_integracao_asaas_completa


class Command(BaseCommand):
    """Complementa integrações Asaas com dados faltantes"""

    help = "Busca integrações Asaas com dados faltantes e tenta completá-las"

    def handle(self, *args, **options):
        integracoes = AsaasIntegracao.objects.filter(
            models.Q(codigo_barras__isnull=True) | models.Q(codigo_barras="")
        ).select_related("cobranca")

        total = integracoes.count()
        atualizadas = 0
        falhas = 0

        if total == 0:
            self.stdout.write("Nenhuma integração pendente encontrada")
            return

        self.stdout.write(f"Processando {total} integrações pendentes...")

        for integracao in integracoes:
            cobranca = integracao.cobranca
            try:
                resultado = atualizar_integracao_asaas_completa(cobranca)
                if resultado and resultado.get("success"):
                    integracao.refresh_from_db()
                    atualizadas += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Cobrança {cobranca.pk} atualizada com sucesso"
                        )
                    )
                else:
                    falhas += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"Falha ao atualizar cobrança {cobranca.pk}: {resultado.get('erros') if resultado else 'sem retorno'}"
                        )
                    )
            except Exception as e:
                falhas += 1
                self.stdout.write(
                    self.style.ERROR(
                        f"Erro ao atualizar cobrança {cobranca.pk}: {e}"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Cobranças atualizadas: {atualizadas}/{total}"
            )
        )
        self.stdout.write(
            self.style.WARNING(
                f"Falhas: {falhas}/{total}"
            )
        )