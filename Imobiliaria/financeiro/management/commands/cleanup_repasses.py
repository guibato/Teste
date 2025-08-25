# financeiro/management/commands/cleanup_repasses.py
from django.core.management.base import BaseCommand
from django.db import transaction
from datetime import date, timedelta
import logging

from ...models.repasse import Repasse, AgendamentoRepasse

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    
    help = 'Limpa dados antigos e inconsistentes de repasses'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dias-antigos',
            type=int,
            default=365,
            help='Remover agendamentos cancelados com mais de N dias'
        )
        parser.add_argument(
            '--corrigir-inconsistencias',
            action='store_true',
            help='Corrigir repasses com dados inconsistentes'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula execução sem fazer alterações'
        )

    def handle(self, *args, **options):
        dias_antigos = options['dias_antigos']
        corrigir_inconsistencias = options['corrigir_inconsistencias']
        dry_run = options['dry_run']
        
        self.stdout.write('Iniciando limpeza de dados de repasses...')
        if dry_run:
            self.stdout.write(self.style.WARNING('MODO DRY-RUN - Nenhuma alteração será feita'))

        try:
            with transaction.atomic():
                # 1. Limpar agendamentos antigos cancelados
                data_limite = date.today() - timedelta(days=dias_antigos)
                
                agendamentos_antigos = AgendamentoRepasse.objects.filter(
                    status__in=['cancelado', 'falha'],
                    data_criacao__date__lt=data_limite
                )
                
                count_agendamentos = agendamentos_antigos.count()
                
                if not dry_run and count_agendamentos > 0:
                    agendamentos_antigos.delete()
                
                self.stdout.write(
                    f'{"[SIMULAÇÃO] " if dry_run else ""}Removidos {count_agendamentos} '
                    f'agendamentos antigos (>{dias_antigos} dias)'
                )

                # 2. Corrigir inconsistências se solicitado
                if corrigir_inconsistencias:
                    self._corrigir_inconsistencias(dry_run)

                if dry_run:
                    # Rollback da transação no dry-run
                    transaction.set_rollback(True)

        except Exception as e:
            logger.error(f'Erro na limpeza: {str(e)}')
            self.stdout.write(
                self.style.ERROR(f'Erro na limpeza: {str(e)}')
            )

    def _corrigir_inconsistencias(self, dry_run):
        """Corrige dados inconsistentes"""
        
        # Repasses com valor líquido negativo
        repasses_negativos = Repasse.objects.filter(
            valor__lt=0
        ).exclude(status='cancelado')
        
        count_negativos = repasses_negativos.count()
        
        if not dry_run and count_negativos > 0:
            for repasse in repasses_negativos:
                repasse.cancelar_repasse('Valor líquido negativo - correção automática')
        
        self.stdout.write(
            f'{"[SIMULAÇÃO] " if dry_run else ""}Corrigidos {count_negativos} '
            f'repasses com valores negativos'
        )
        
        # Repasses efetuados sem data de efetivação
        repasses_sem_data = Repasse.objects.filter(
            status='efetuado',
            data_efetivacao__isnull=True
        )
        
        count_sem_data = repasses_sem_data.count()
        
        if not dry_run and count_sem_data > 0:
            for repasse in repasses_sem_data:
                repasse.data_efetivacao = repasse.data_criacao.date()
                repasse.save(update_fields=['data_efetivacao'])
        
        self.stdout.write(
            f'{"[SIMULAÇÃO] " if dry_run else ""}Corrigidos {count_sem_data} '
            f'repasses efetuados sem data de efetivação'
        )
        
        # Agendamentos órfãos (sem contrato ativo)
        from cadastro.models import Contrato
        
        agendamentos_orfaos = AgendamentoRepasse.objects.filter(
            status='agendado'
        ).exclude(
            contrato__in=Contrato.objects.filter(status='ativo')
        )
        
        count_orfaos = agendamentos_orfaos.count()
        
        if not dry_run and count_orfaos > 0:
            for agendamento in agendamentos_orfaos:
                agendamento.cancelar('Contrato inativo - limpeza automática')
        
        self.stdout.write(
            f'{"[SIMULAÇÃO] " if dry_run else ""}Cancelados {count_orfaos} '
            f'agendamentos órfãos'
        )