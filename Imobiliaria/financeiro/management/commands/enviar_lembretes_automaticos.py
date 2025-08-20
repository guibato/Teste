# financeiro/management/commands/enviar_lembretes_automaticos.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
import logging

from financeiro.models.cobranca import Cobranca
from financeiro.models.lembrete import LembreteEnviado
from financeiro.views.lembrete_views import simular_envio_lembrete, is_dry_run_mode

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Envia lembretes automáticos de cobrança (10DU, 3DU, dia vencimento)'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Executa em modo teste (não envia mensagens reais)'
        )
        parser.add_argument(
            '--force',
            action='store_true', 
            help='Força execução mesmo em final de semana'
        )
        parser.add_argument(
            '--dias-antes',
            nargs='+',
            type=int,
            default=[10, 3, 1, 0],
            help='Dias antes do vencimento para enviar (padrão: 10 3 1 0)'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Log detalhado'
        )

    def handle(self, *args, **options):
        """Executa envio automático de lembretes"""
        
        # Configurar modo dry run se solicitado
        if options['dry_run']:
            import os
            os.environ['LEMBRETE_DRY_RUN'] = 'True'
            self.stdout.write(
                self.style.WARNING('🧪 MODO DRY RUN ATIVADO - Mensagens não serão enviadas!')
            )
        
        hoje = date.today()
        verbose = options['verbose']
        
        # Verificar se é dia útil (a menos que forçado)
        if not options['force']:
            if hoje.weekday() >= 5:  # Sábado=5, Domingo=6
                self.stdout.write(
                    self.style.WARNING(
                        f'⏰ Hoje é {hoje.strftime("%A, %d/%m/%Y")} (final de semana). '
                        'Use --force para executar mesmo assim.'
                    )
                )
                return
        
        self.stdout.write(
            self.style.SUCCESS(
                f'🚀 Iniciando envio automático de lembretes - {hoje.strftime("%d/%m/%Y")}'
            )
        )
        
        dias_antes_lista = options['dias_antes']
        total_enviados = 0
        total_falhas = 0
        
        # Processar cada configuração de dias antes
        for dias_antes in dias_antes_lista:
            
            if verbose:
                self.stdout.write(f'\n📅 Processando lembretes para {dias_antes} dias antes...')
            
            # Calcular data de vencimento alvo
            data_vencimento_alvo = hoje + timedelta(days=dias_antes)
            
            # Buscar cobranças que vencem na data alvo
            cobrancas = Cobranca.objects.filter(
                status__in=['pendente', 'atrasada'],
                data_vencimento=data_vencimento_alvo
            ).select_related('inquilino', 'contrato', 'asaas_integracao')
            
            if verbose:
                self.stdout.write(
                    f'   📋 {cobrancas.count()} cobranças vencem em {data_vencimento_alvo.strftime("%d/%m/%Y")}'
                )
            
            enviados_grupo = 0
            falhas_grupo = 0
            
            for cobranca in cobrancas:
                
                # Verificar se já foi enviado lembrete para esta configuração
                ja_enviado = LembreteEnviado.objects.filter(
                    cobranca=cobranca,
                    dias_antes_vencimento=dias_antes,
                    status='enviado'
                ).exists()
                
                if ja_enviado:
                    if verbose:
                        self.stdout.write(
                            f'   ⏭️  {cobranca.inquilino.nome} - Já enviado'
                        )
                    continue
                
                # Verificar se inquilino tem telefone
                inquilino = cobranca.inquilino
                if not inquilino:
                    if verbose:
                        self.stdout.write(
                            f'   ❌ Cobrança {cobranca.pk} sem inquilino'
                        )
                    falhas_grupo += 1
                    continue
                
                telefone = self._get_telefone_inquilino(inquilino)
                if not telefone:
                    if verbose:
                        self.stdout.write(
                            f'   📵 {inquilino.nome} - Sem telefone válido'
                        )
                    falhas_grupo += 1
                    continue
                
                # Tentar enviar lembrete
                try:
                    sucesso = simular_envio_lembrete(cobranca, 'whatsapp')
                    
                    # Registrar o envio
                    observacao = f'Enviado automaticamente via comando - {dias_antes} dias antes'
                    if is_dry_run_mode():
                        observacao = '[DRY RUN] ' + observacao
                    
                    LembreteEnviado.objects.create(
                        cobranca=cobranca,
                        tipo='whatsapp',
                        dias_antes_vencimento=dias_antes,
                        status='enviado' if sucesso else 'falha',
                        observacao=observacao
                    )
                    
                    if sucesso:
                        enviados_grupo += 1
                        if verbose:
                            self.stdout.write(
                                f'   ✅ {inquilino.nome} - R$ {cobranca.valor_total}'
                            )
                    else:
                        falhas_grupo += 1
                        if verbose:
                            self.stdout.write(
                                f'   ❌ {inquilino.nome} - Falha no envio'
                            )
                            
                except Exception as e:
                    falhas_grupo += 1
                    logger.error(f'Erro no envio para {inquilino.nome}: {str(e)}')
                    if verbose:
                        self.stdout.write(
                            f'   💥 {inquilino.nome} - Erro: {str(e)[:50]}...'
                        )
            
            # Resumo do grupo
            if enviados_grupo > 0 or falhas_grupo > 0:
                self.stdout.write(
                    f'   📊 {dias_antes} dias antes: {enviados_grupo} enviados, {falhas_grupo} falhas'
                )
            
            total_enviados += enviados_grupo
            total_falhas += falhas_grupo
        
        # Resumo final
        self.stdout.write('\n' + '='*60)
        
        if total_enviados > 0 or total_falhas > 0:
            sucesso_pct = (total_enviados / (total_enviados + total_falhas) * 100) if (total_enviados + total_falhas) > 0 else 0
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ CONCLUÍDO: {total_enviados} lembretes enviados'
                )
            )
            
            if total_falhas > 0:
                self.stdout.write(
                    self.style.ERROR(
                        f'❌ FALHAS: {total_falhas} lembretes falharam'
                    )
                )
            
            self.stdout.write(
                f'📈 Taxa de sucesso: {sucesso_pct:.1f}%'
            )
            
            if is_dry_run_mode():
                self.stdout.write(
                    self.style.WARNING('🧪 Executado em modo DRY RUN - Nenhuma mensagem real foi enviada!')
                )
        else:
            self.stdout.write(
                self.style.SUCCESS('✨ Nenhum lembrete programado para hoje!')
            )
    
    def _get_telefone_inquilino(self, inquilino):
        """Busca telefone válido do inquilino"""
        campos_telefone = ['whatsapp', 'telefone', 'celular', 'telefone_celular']
        
        for campo in campos_telefone:
            if hasattr(inquilino, campo):
                telefone = getattr(inquilino, campo)
                if telefone and len(str(telefone).replace(' ', '').replace('-', '').replace('(', '').replace(')', '')) >= 10:
                    return telefone
        
        return None