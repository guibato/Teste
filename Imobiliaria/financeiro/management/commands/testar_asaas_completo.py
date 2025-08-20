from django.core.management.base import BaseCommand
from financeiro.models.cobranca import Cobranca
from financeiro.services.asaas_service import AsaasService
from financeiro.utils.asaas_utils import atualizar_integracao_asaas_completa, gerar_mensagem_cobranca_com_asaas

class Command(BaseCommand):
    help = 'Testa integração completa com Asaas (código de barras e PIX)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--cobranca-id',
            type=int,
            help='ID específico da cobrança para testar'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Apenas mostra o que seria feito, sem salvar'
        )

    def handle(self, *args, **options):
        self.stdout.write("🧪 TESTE ASAAS COMPLETO")
        self.stdout.write("=" * 50)
        
        # Buscar cobrança
        if options['cobranca_id']:
            try:
                cobranca = Cobranca.objects.get(pk=options['cobranca_id'])
            except Cobranca.DoesNotExist:
                self.stdout.write(f"❌ Cobrança {options['cobranca_id']} não encontrada")
                return
        else:
            cobranca = Cobranca.objects.filter(
                asaas_integracao__asaas_id__isnull=False
            ).first()
            
            if not cobranca:
                self.stdout.write("❌ Nenhuma cobrança com integração Asaas encontrada")
                return
        
        self.stdout.write(f"📋 Cobrança: {cobranca}")
        self.stdout.write(f"🆔 Asaas ID: {cobranca.asaas_integracao.asaas_id}")
        
        try:
            # Testar conexão
            asaas_service = AsaasService()
            conexao = asaas_service.testar_conexao()
            
            if not conexao['sucesso']:
                self.stdout.write(f"❌ Erro na conexão: {conexao['erro']}")
                return
            
            self.stdout.write(f"✅ Conexão OK - {conexao['mensagem']}")
            
            # Testar atualização completa
            if not options['dry_run']:
                resultado = atualizar_integracao_asaas_completa(cobranca)
                
                if resultado['success']:
                    self.stdout.write("✅ Integração atualizada com sucesso!")
                    self.stdout.write(f"   Dados: {resultado['dados_atualizados']}")
                    if resultado['erros']:
                        self.stdout.write(f"   Avisos: {resultado['erros']}")
                else:
                    self.stdout.write(f"❌ Falha na atualização: {resultado['erros']}")
            else:
                self.stdout.write("🧪 DRY RUN - Não salvando alterações")
            
            # Testar mensagem
            self.stdout.write("\n📝 MENSAGEM GERADA:")
            self.stdout.write("-" * 40)
            mensagem = gerar_mensagem_cobranca_com_asaas(cobranca)
            self.stdout.write(mensagem)
            self.stdout.write("-" * 40)
            
        except Exception as e:
            self.stdout.write(f"💥 Erro no teste: {str(e)}")