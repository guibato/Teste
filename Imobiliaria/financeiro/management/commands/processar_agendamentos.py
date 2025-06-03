# financeiro/management/commands/processar_agendamentos.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
import logging

from ...services.repasse_service import RepasseService
from ...models.repasse import AgendamentoRepasse

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Processa agendamentos de repasses pendentes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--data',
            type=str,
            help='Data para processamento (YYYY-MM-DD). Padrão: hoje'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula execução sem fazer alterações'
        )

    def handle(self, *args, **options):
        data_processamento = date.today()
        
        if options['data']:
            try:
                data_processamento = date.fromisoformat(options['data'])
            except ValueError:
                self.stdout.write(
                    self.style.ERROR(f'Data inválida: {options["data"]}')
                )
                return

        dry_run = options['dry_run']
        
        self.stdout.write(f'Processando agendamentos para {data_processamento}')
        if dry_run:
            self.stdout.write(self.style.WARNING('MODO DRY-RUN - Nenhuma alteração será feita'))

        try:
            service = RepasseService()
            
            # Buscar agendamentos para processar
            agendamentos = AgendamentoRepasse.objects.filter(
                status='agendado',
                data_agendada__lte=data_processamento
            ).select_related('proprietario', 'contrato', 'politica')

            self.stdout.write(f'Encontrados {agendamentos.count()} agendamentos para processar')

            if not dry_run:
                resultado = service.processar_repasses_automaticos(data_processamento)
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Processamento concluído:\n'
                        f'- Processados: {resultado["processados"]}\n'
                        f'- Criados: {resultado["criados"]}\n'
                        f'- Erros: {resultado["erros"]}'
                    )
                )

                if resultado['erros'] > 0:
                    self.stdout.write(self.style.WARNING('Detalhes dos erros:'))
                    for detalhe in resultado['detalhes']:
                        if detalhe['status'] == 'erro':
                            self.stdout.write(f'  - Agendamento {detalhe["agendamento_id"]}: {detalhe["erro"]}')
            else:
                # Simular processamento
                for agendamento in agendamentos:
                    self.stdout.write(
                        f'[SIMULAÇÃO] Processaria agendamento {agendamento.id} - '
                        f'{agendamento.proprietario.nome} - R$ {agendamento.valor_previsto}'
                    )

        except Exception as e:
            logger.error(f'Erro no processamento de agendamentos: {str(e)}')
            self.stdout.write(
                self.style.ERROR(f'Erro no processamento: {str(e)}')
            )