# financeiro/management/commands/processar_repasses.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from financeiro.services.repasse_service import RepasseService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Processa repasses automáticos baseado nas políticas configuradas'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Executa em modo de teste sem fazer alterações',
        )
        
        parser.add_argument(
            '--force',
            action='store_true',
            help='Força o processamento mesmo se já foi executado hoje',
        )
        
        parser.add_argument(
            '--apenas-agendamentos',
            action='store_true',
            help='Processa apenas agendamentos vencidos',
        )
        
        parser.add_argument(
            '--apenas-diretos',
            action='store_true',
            help='Cria apenas repasses diretos',
        )
        
        parser.add_argument(
            '--relatorio',
            action='store_true',
            help='Gera apenas relatório do status da automação',
        )
    
    def handle(self, *args, **options):
        inicio = timezone.now()
        
        self.stdout.write(
            self.style.SUCCESS(f'Iniciando processamento de repasses em {inicio}')
        )
        
        try:
            service = RepasseService()
            
            if options['relatorio']:
                self._gerar_relatorio(service)
                return
            
            if options['dry_run']:
                self.stdout.write(
                    self.style.WARNING('MODO DRY-RUN: Nenhuma alteração será feita')
                )
                return
            
            # Executar processamento
            if options['apenas_agendamentos']:
                resultado = self._processar_apenas_agendamentos(service)
            elif options['apenas_diretos']:
                resultado = self._processar_apenas_diretos(service)
            else:
                resultado = service.processar_repasses_automaticos()
            
            # Exibir resultados
            self._exibir_resultados(resultado)
            
            # Verificar repasses atrasados
            self._verificar_atrasados(service)
            
            fim = timezone.now()
            duracao = (fim - inicio).total_seconds()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Processamento concluído em {duracao:.2f} segundos'
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Erro durante o processamento: {str(e)}')
            )
            logger.error(f"Erro no comando processar_repasses: {str(e)}")
            raise
    
    def _processar_apenas_agendamentos(self, service):
        """Processa apenas agendamentos vencidos"""
        self.stdout.write('Processando apenas agendamentos vencidos...')
        service._processar_agendamentos_vencidos()
        return service.resultados
    
    def _processar_apenas_diretos(self, service):
        """Cria apenas repasses diretos"""
        self.stdout.write('Criando apenas repasses diretos...')
        service._criar_repasses_diretos()
        return service.resultados
    
    def _gerar_relatorio(self, service):
        """Gera relatório do status da automação"""
        relatorio = service.gerar_relatorio_automatizacao()
        
        self.stdout.write(
            self.style.HTTP_INFO('\n=== RELATÓRIO DE AUTOMAÇÃO DE REPASSES ===')
        )
        
        # Contratos
        self.stdout.write(f"\n📋 CONTRATOS:")
        self.stdout.write(f"   Total de contratos ativos: {relatorio['contratos']['total']}")
        self.stdout.write(f"   Com política configurada: {relatorio['contratos']['com_politica']}")
        self.stdout.write(f"   Sem política configurada: {relatorio['contratos']['sem_politica']}")
        self.stdout.write(f"   Cobertura: {relatorio['contratos']['percentual_cobertura']:.1f}%")
        
        # Agendamentos
        self.stdout.write(f"\n📅 AGENDAMENTOS:")
        self.stdout.write(f"   Pendentes: {relatorio['agendamentos']['pendentes']}")
        
        # Repasses
        self.stdout.write(f"\n💰 REPASSES:")
        self.stdout.write(f"   Pendentes: {relatorio['repasses']['pendentes']}")
        self.stdout.write(f"   Atrasados: {relatorio['repasses']['atrasados']}")
        
        if relatorio['repasses']['atrasados'] > 0:
            self.stdout.write(
                self.style.WARNING(f"   ⚠️  Atenção: {relatorio['repasses']['atrasados']} repasses atrasados!")
            )
        
        self.stdout.write(f"\n📊 Data do relatório: {relatorio['data_relatorio']}")
    
    def _exibir_resultados(self, resultado):
        """Exibe os resultados do processamento"""
        self.stdout.write(
            self.style.HTTP_INFO('\n=== RESULTADOS DO PROCESSAMENTO ===')
        )
        
        self.stdout.write(f"✅ Repasses criados: {resultado['criados']}")
        self.stdout.write(f"⚡ Agendamentos processados: {resultado['processados']}")
        self.stdout.write(f"📅 Novos agendamentos: {resultado['agendados']}")
        self.stdout.write(f"❌ Erros: {resultado['erros']}")
        
        if resultado['detalhes']:
            self.stdout.write(f"\n📝 DETALHES:")
            for detalhe in resultado['detalhes'][:10]:  # Mostrar apenas os primeiros 10
                if 'Erro' in detalhe:
                    self.stdout.write(f"   ❌ {detalhe}")
                else:
                    self.stdout.write(f"   ✅ {detalhe}")
            
            if len(resultado['detalhes']) > 10:
                self.stdout.write(f"   ... e mais {len(resultado['detalhes']) - 10} itens")
    
    def _verificar_atrasados(self, service):
        """Verifica e alerta sobre repasses atrasados"""
        atrasados = service.verificar_repasses_atrasados()
        
        if atrasados['count'] > 0:
            self.stdout.write(
                self.style.WARNING(f"\n⚠️  ATENÇÃO: {atrasados['count']} repasses atrasados encontrados!")
            )
            
            # Mostrar os 5 mais atrasados
            for repasse in atrasados['repasses'][:5]:
                self.stdout.write(
                    f"   🔴 Repasse #{repasse['id']} - {repasse['proprietario__nome']} - "
                    f"R$ {repasse['valor_liquido']:.2f} - {repasse['dias_atraso']} dias"
                )
            
            if atrasados['count'] > 5:
                self.stdout.write(f"   ... e mais {atrasados['count'] - 5} repasses atrasados")


# financeiro/management/commands/testar_politicas.py
from django.core.management.base import BaseCommand
from financeiro.models.repasse import PoliticaRepasseContrato
from core.models import Contrato


class Command(BaseCommand):
    help = 'Testa as políticas de repasse configuradas'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--contrato-id',
            type=int,
            help='ID do contrato específico para testar',
        )
    
    def handle(self, *args, **options):
        if options['contrato_id']:
            self._testar_contrato_especifico(options['contrato_id'])
        else:
            self._testar_todas_politicas()
    
    def _testar_contrato_especifico(self, contrato_id):
        """Testa política de um contrato específico"""
        try:
            contrato = Contrato.objects.get(id=contrato_id)
            
            if hasattr(contrato, 'politica_repasse') and contrato.politica_repasse:
                politica = contrato.politica_repasse
                simulacao = politica.simular_proximo_repasse()
                
                self.stdout.write(f"\n🏠 CONTRATO #{contrato.id}")
                self.stdout.write(f"   Proprietário(s): {', '.join([p.nome for p in contrato.proprietario.all()])}")
                self.stdout.write(f"   Endereço: {contrato.imovel}")
                
                self.stdout.write(f"\n📋 POLÍTICA:")
                self.stdout.write(f"   Periodicidade: {politica.get_periodicidade_display()}")
                self.stdout.write(f"   Tipo de dias: {politica.get_tipo_dias_display()}")
                self.stdout.write(f"   Ativa: {'Sim' if politica.ativa else 'Não'}")
                
                self.stdout.write(f"\n💰 SIMULAÇÃO:")
                if simulacao['viavel']:
                    self.stdout.write(f"   ✅ Próximo repasse: {simulacao['data_prevista']}")
                    self.stdout.write(f"   Valor bruto: R$ {simulacao['valor_bruto']:.2f}")
                    self.stdout.write(f"   Taxa admin: R$ {simulacao['valor_taxa_admin']:.2f}")
                    self.stdout.write(f"   Valor líquido: R$ {simulacao['valor_liquido']:.2f}")
                else:
                    self.stdout.write(f"   ❌ Não viável: {simulacao['motivo']}")
            else:
                self.stdout.write(
                    self.style.WARNING(f"Contrato #{contrato_id} não possui política configurada")
                )
                
        except Contrato.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"Contrato #{contrato_id} não encontrado")
            )
    
    def _testar_todas_politicas(self):
        """Testa todas as políticas configuradas"""
        politicas = PoliticaRepasseContrato.objects.select_related('contrato').prefetch_related(
            'contrato__proprietario'
        )
        
        self.stdout.write(f"📊 Testando {politicas.count()} políticas configuradas...\n")
        
        ativas = 0
        inativas = 0
        viaveis = 0
        nao_viaveis = 0
        
        for politica in politicas:
            if politica.ativa:
                ativas += 1
                simulacao = politica.simular_proximo_repasse()
                
                if simulacao['viavel']:
                    viaveis += 1
                    status = "✅"
                else:
                    nao_viaveis += 1
                    status = "❌"
                
                self.stdout.write(
                    f"{status} Contrato #{politica.contrato.id} - "
                    f"{politica.get_periodicidade_display()} - "
                    f"R$ {simulacao.get('valor_liquido', 0):.2f}"
                )
            else:
                inativas += 1
        
        # Resumo
        self.stdout.write(f"\n📈 RESUMO:")
        self.stdout.write(f"   Políticas ativas: {ativas}")
        self.stdout.write(f"   Políticas inativas: {inativas}")
        self.stdout.write(f"   Repasses viáveis: {viaveis}")
        self.stdout.write(f"   Repasses não viáveis: {nao_viaveis}")
        
        if nao_viaveis > 0:
            self.stdout.write(
                self.style.WARNING(f"\n⚠️  {nao_viaveis} contratos com problemas na política!")
            )