# financeiro/management/commands/calcular_repasses.py
from django.core.management.base import BaseCommand
from django.db.models import Q
from datetime import date, timedelta
import logging

from ...services.repasse_service import RepasseService
from ...models.cobranca import Cobranca
from ...models.repasse import Repasse, PoliticaRepasse

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Calcula e agenda repasses baseados em cobranças pagas'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dias-atras',
            type=int,
            default=7,
            help='Verificar cobranças pagas nos últimos N dias'
        )
        parser.add_argument(
            '--politica-id',
            type=int,
            help='ID da política específica para usar'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula execução sem fazer alterações'
        )

    def handle(self, *args, **options):
        dias_atras = options['dias_atras']
        politica_id = options['politica_id']
        dry_run = options['dry_run']
        
        data_limite = date.today() - timedelta(days=dias_atras)
        
        self.stdout.write(f'Calculando repasses para cobranças pagas desde {data_limite}')
        if dry_run:
            self.stdout.write(self.style.WARNING('MODO DRY-RUN - Nenhuma alteração será feita'))

        try:
            # Buscar cobranças pagas que ainda não têm repasse
            cobrancas = Cobranca.objects.filter(
                status='paga',
                data_pagamento__gte=data_limite,
                status_repasse__in=['pendente', None]
            ).select_related('contrato', 'contrato__proprietario')

            # Filtrar cobranças que já têm repasse
            cobrancas_sem_repasse = []
            for cobranca in cobrancas:
                existe_repasse = Repasse.objects.filter(
                    cobranca=cobranca,
                    status__in=['pendente', 'efetuado']
                ).exists()
                
                if not existe_repasse:
                    cobrancas_sem_repasse.append(cobranca)

            self.stdout.write(f'Encontradas {len(cobrancas_sem_repasse)} cobranças sem repasse')

            # Buscar política ativa
            if politica_id:
                try:
                    politica = PoliticaRepasse.objects.get(id=politica_id, ativa=True)
                except PoliticaRepasse.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f'Política {politica_id} não encontrada ou inativa'))
                    return
            else:
                politica = PoliticaRepasse.objects.filter(ativa=True).first()
                if not politica:
                    self.stdout.write(self.style.ERROR('Nenhuma política ativa encontrada'))
                    return

            self.stdout.write(f'Usando política: {politica.nome}')

            service = RepasseService()
            criados = 0
            erros = 0

            for cobranca in cobrancas_sem_repasse:
                try:
                    # Calcular próxima data de repasse
                    data_repasse = politica.calcular_proxima_data_repasse(cobranca.data_pagamento)
                    
                    if not data_repasse:
                        self.stdout.write(f'Erro ao calcular data para cobrança {cobranca.id}')
                        erros += 1
                        continue

                    # Calcular valor do repasse
                    valor_base, detalhes = service.calcular_valor_repasse(cobranca, politica)
                    
                    if valor_base <= 0 or 'erro' in detalhes:
                        self.stdout.write(f'Erro ao calcular valor para cobrança {cobranca.id}: {detalhes}')
                        erros += 1
                        continue

                    if not dry_run:
                        # Criar repasse
                        repasse_data = {
                            'proprietario': cobranca.contrato.proprietario,
                            'contrato': cobranca.contrato,
                            'cobranca': cobranca,
                            'valor': valor_base,
                            'valor_desconto': detalhes.get('valor_desconto', 0),
                            'valor_taxa_admin': detalhes.get('valor_taxa_admin', 0),
                            'data_prevista': data_repasse,
                            'mes_referencia': cobranca.mes_referencia,
                            'ano_referencia': cobranca.ano_referencia,
                            'descricao': f'Repasse automático ref. {cobranca.mes_referencia}/{cobranca.ano_referencia}'
                        }
                        
                        repasse = service.criar_repasse_manual(repasse_data)
                        
                        # Atualizar status da cobrança
                        cobranca.status_repasse = 'agendado'
                        cobranca.save(update_fields=['status_repasse'])
                        
                        criados += 1
                        
                        self.stdout.write(
                            f'Repasse criado: #{repasse.id} - {repasse.proprietario.nome} - '
                            f'R$ {repasse.valor_liquido} - {data_repasse}'
                        )
                    else:
                        self.stdout.write(
                            f'[SIMULAÇÃO] Criaria repasse: {cobranca.contrato.proprietario.nome} - '
                            f'R$ {detalhes["valor_liquido"]} - {data_repasse}'
                        )
                        criados += 1

                except Exception as e:
                    logger.error(f'Erro ao processar cobrança {cobranca.id}: {str(e)}')
                    erros += 1

            self.stdout.write(
                self.style.SUCCESS(
                    f'Processamento concluído:\n'
                    f'- Repasses criados: {criados}\n'
                    f'- Erros: {erros}'
                )
            )

        except Exception as e:
            logger.error(f'Erro no cálculo de repasses: {str(e)}')
            self.stdout.write(
                self.style.ERROR(f'Erro no processamento: {str(e)}')
            )
