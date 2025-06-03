# financeiro/management/commands/atualizar_indices.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from financeiro.services.indice_service import IndiceAPIService


class Command(BaseCommand):
    help = 'Atualiza índices de inflação das APIs externas'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tipo',
            type=str,
            choices=['IPCA', 'IGPM'],
            help='Tipo específico de índice para atualizar'
        )

    def handle(self, *args, **options):
        service = IndiceAPIService()
        
        self.stdout.write(
            self.style.SUCCESS(f'Iniciando atualização em {timezone.now()}')
        )

        if options['tipo']:
            # Atualizar tipo específico
            try:
                resultado = service.atualizar_indice(options['tipo'])
                self.stdout.write(
                    self.style.SUCCESS(
                        f"{options['tipo']}: {resultado['criados']} criados, "
                        f"{resultado['atualizados']} atualizados"
                    )
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Erro ao atualizar {options['tipo']}: {e}")
                )
        else:
            # Atualizar todos
            resultados = service.atualizar_todos_indices()
            
            for tipo, resultado in resultados.items():
                if resultado['sucesso']:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"{tipo}: {resultado['criados']} criados, "
                            f"{resultado['atualizados']} atualizados"
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(f"Erro {tipo}: {resultado['erro']}")
                    )

        self.stdout.write(
            self.style.SUCCESS('Atualização concluída!')
        )