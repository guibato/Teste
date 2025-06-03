# financeiro/management/commands/verificar_repasses_atrasados.py
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from datetime import date
import logging

from ...services.repasse_service import RepasseService
from ...models.repasse import Repasse

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Verifica repasses em atraso e envia notificações'

    def add_arguments(self, parser):
        parser.add_argument(
            '--enviar-email',
            action='store_true',
            help='Enviar email de notificação sobre atrasos'
        )
        parser.add_argument(
            '--dias-limite',
            type=int,
            default=5,
            help='Alertar sobre repasses com mais de N dias de atraso'
        )

    def handle(self, *args, **options):
        enviar_email = options['enviar_email']
        dias_limite = options['dias_limite']
        
        self.stdout.write('Verificando repasses em atraso...')

        try:
            service = RepasseService()
            atrasados = service.verificar_repasses_atrasados()
            
            if not atrasados:
                self.stdout.write(self.style.SUCCESS('Nenhum repasse em atraso encontrado'))
                return

            # Filtrar por dias de atraso
            atrasados_criticos = [r for r in atrasados if r['dias_atraso'] >= dias_limite]
            
            self.stdout.write(f'Encontrados {len(atrasados)} repasses em atraso')
            self.stdout.write(f'{len(atrasados_criticos)} com mais de {dias_limite} dias de atraso')

            # Exibir detalhes
            for item in atrasados:
                repasse = item['repasse']
                status_emoji = '🔴' if item['dias_atraso'] >= dias_limite else '🟡'
                
                self.stdout.write(
                    f'{status_emoji} Repasse #{repasse.id} - {item["proprietario"]} - '
                    f'R$ {item["valor_liquido"]} - {item["dias_atraso"]} dias de atraso'
                )

            # Enviar email se solicitado
            if enviar_email and atrasados_criticos:
                self._enviar_notificacao_atraso(atrasados_criticos)

        except Exception as e:
            logger.error(f'Erro na verificação de atrasos: {str(e)}')
            self.stdout.write(
                self.style.ERROR(f'Erro na verificação: {str(e)}')
            )

    def _enviar_notificacao_atraso(self, atrasados_criticos):
        """Envia email de notificação sobre repasses em atraso"""
        try:
            total_valor = sum(item['valor_liquido'] for item in atrasados_criticos)
            
            subject = f'ALERTA: {len(atrasados_criticos)} repasses em atraso crítico'
            
            message = f"""
Repasses em Atraso Crítico - {date.today().strftime('%d/%m/%Y')}

Total de repasses: {len(atrasados_criticos)}
Valor total: R$ {total_valor:,.2f}

Detalhes:
"""
            
            for item in atrasados_criticos:
                repasse = item['repasse']
                message += f"""
- Repasse #{repasse.id}
  Proprietário: {item['proprietario']}
  Valor: R$ {item['valor_liquido']:,.2f}
  Dias de atraso: {item['dias_atraso']}
  Data prevista: {repasse.data_prevista.strftime('%d/%m/%Y')}
"""

            message += f"""

Acesse o sistema para processar os repasses pendentes.
"""

            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.ADMIN_EMAIL],
                fail_silently=False,
            )
            
            self.stdout.write(self.style.SUCCESS('Email de notificação enviado'))
            
        except Exception as e:
            logger.error(f'Erro ao enviar email: {str(e)}')
            self.stdout.write(
                self.style.ERROR(f'Erro ao enviar email: {str(e)}')
            )