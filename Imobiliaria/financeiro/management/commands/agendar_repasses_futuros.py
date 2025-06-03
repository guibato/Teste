# financeiro/management/commands/agendar_repasses_futuros.py
from django.core.management.base import BaseCommand
from datetime import date, timedelta
import logging

from ...services.repasse_service import RepasseService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Agenda repasses futuros baseados nas políticas ativas'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dias-futuro',
            type=int,
            default=30,
            help='Quantos dias no futuro agendar (padrão: 30)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula execução sem fazer alterações'
        )

    def handle(self, *args, **options):
        dias_futuro = options['dias_futuro']
        dry_run = options['dry_run']
        
        self.stdout.write(f'Agendando repasses para os próximos {dias_futuro} dias')
        if dry_run:
            self.stdout.write(self.style.WARNING('MODO DRY-RUN - Nenhuma alteração será feita'))

        try:
            service = RepasseService()
            
            if not dry_run:
                resultado = service.agendar_repasses_futuros(dias_futuro)
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Agendamento concluído:\n'
                        f'- Agendamentos criados: {resultado["agendados"]}\n'
                        f'- Erros: {resultado["erros"]}'
                    )
                )

                if resultado['agendados'] > 0:
                    self.stdout.write('Detalhes dos agendamentos:')
                    for detalhe in resultado['detalhes']:
                        self.stdout.write(
                            f'  - Agendamento #{detalhe["agendamento_id"]}: '
                            f'Contrato {detalhe["contrato_id"]} - '
                            f'R$ {detalhe["valor_previsto"]} em {detalhe["data_agendada"]}'
                        )
            else:
                # Simular agendamento
                from ...models.repasse import PoliticaRepasse
                from sisimob.models import Contrato
                
                politicas_ativas = PoliticaRepasse.objects.filter(ativa=True)
                data_limite = date.today() + timedelta(days=dias_futuro)
                
                total_simulado = 0
                
                for politica in politicas_ativas:
                    contratos = Contrato.objects.filter(
                        status='ativo',
                        data_fim__gte=date.today()
                    ).select_related('proprietario')
                    
                    for contrato in contratos:
                        proxima_data = politica.calcular_proxima_data_repasse()
                        
                        if proxima_data and proxima_data <= data_limite:
                            self.stdout.write(
                                f'[SIMULAÇÃO] Agendaria: {contrato.proprietario.nome} - '
                                f'{proxima_data} - Política: {politica.nome}'
                            )
                            total_simulado += 1
                
                self.stdout.write(f'Total de agendamentos simulados: {total_simulado}')

        except Exception as e:
            logger.error(f'Erro no agendamento: {str(e)}')
            self.stdout.write(
                self.style.ERROR(f'Erro no processamento: {str(e)}')
            )