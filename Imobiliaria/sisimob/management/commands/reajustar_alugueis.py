from django.core.management.base import BaseCommand
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from sisimob.models import Contrato, IndiceInflacao

class Command(BaseCommand):
    help = 'Aplica reajuste de aluguel aos contratos ativos, se aplicável.'

    def handle(self, *args, **kwargs):
        hoje = timezone.now().date()
        contratos = Contrato.objects.filter(ativo=True)

        for contrato in contratos:
            historico = contrato.historico_aluguel
            ultima_data_reajuste = max([
                timezone.datetime.strptime(k, "%Y-%m-%d").date()
                for k in historico.keys()
            ])
            nova_data_reajuste = ultima_data_reajuste + relativedelta(months=12)

            # Buscar 12 índices após o último reajuste
            indices = IndiceInflacao.objects.filter(
                tipo=contrato.fator_reajuste,
                data_referencia__gt=ultima_data_reajuste
            ).order_by('data_referencia')[:12]

            print(f"[DEBUG] Contrato {contrato.id}")
            print(f" - Último reajuste: {ultima_data_reajuste}")
            print(f" - Próximo reajuste esperado: {nova_data_reajuste}")
            print(f" - Índices encontrados: {indices.count()}")

            if indices.count() == 12:
                fator_reajuste = Decimal('1.00')
                for indice in indices:
                    fator_reajuste *= (1 + indice.valor / 100)

                valor_anterior = Decimal(historico[str(ultima_data_reajuste)])
                novo_valor = (valor_anterior * fator_reajuste).quantize(Decimal('0.01'))

                contrato.historico_aluguel[str(nova_data_reajuste)] = float(novo_valor)
                contrato.valor_aluguel = novo_valor
                contrato.save()

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Contrato {contrato.id}: Reajustado de R$ {valor_anterior} para R$ {novo_valor} usando índices até {indices.last().data_referencia}"
                    )
                )
            else:
                self.stdout.write(f"Contrato {contrato.id}: Ainda não há 12 índices disponíveis (encontrou {indices.count()}).")