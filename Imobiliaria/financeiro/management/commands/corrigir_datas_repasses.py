# financeiro/management/commands/corrigir_datas_repasses.py

from django.core.management.base import BaseCommand
from django.db import transaction
from datetime import date, timedelta
from decimal import Decimal

from financeiro.models.repasse import Repasse
from sisimob.models import Contrato

try:
    from financeiro.models.cobranca import Cobranca
except ImportError:
    Cobranca = None


class Command(BaseCommand):
    help = 'Corrige as datas dos repasses existentes baseando na data de pagamento das cobranças'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Apenas simula as correções sem alterar dados',
        )
        
        parser.add_argument(
            '--repasse-id',
            type=int,
            help='ID específico do repasse para corrigir',
        )
        
        parser.add_argument(
            '--apenas-pendentes',
            action='store_true',
            help='Corrige apenas repasses pendentes',
        )
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        repasse_id = options.get('repasse_id')
        apenas_pendentes = options['apenas_pendentes']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('🧪 MODO DRY-RUN: Nenhuma alteração será feita')
            )
        
        self.stdout.write(
            self.style.SUCCESS('🔧 CORREÇÃO DE DATAS DE REPASSES')
        )
        
        # Filtrar repasses
        if repasse_id:
            repasses = Repasse.objects.filter(id=repasse_id)
        elif apenas_pendentes:
            repasses = Repasse.objects.filter(status='pendente')
        else:
            repasses = Repasse.objects.all()
        
        # Adicionar informações relacionadas
        repasses = repasses.select_related('cobranca', 'contrato').prefetch_related(
            'contrato__politica_repasse'
        )
        
        self.stdout.write(f"\n📊 Encontrados {repasses.count()} repasses para analisar")
        
        corrigidos = 0
        sem_cobranca = 0
        sem_data_pagamento = 0
        ja_corretos = 0
        erros = 0
        
        with transaction.atomic():
            for repasse in repasses:
                resultado = self._corrigir_repasse(repasse, dry_run)
                
                if resultado['acao'] == 'corrigido':
                    corrigidos += 1
                elif resultado['acao'] == 'sem_cobranca':
                    sem_cobranca += 1
                elif resultado['acao'] == 'sem_data_pagamento':
                    sem_data_pagamento += 1
                elif resultado['acao'] == 'ja_correto':
                    ja_corretos += 1
                elif resultado['acao'] == 'erro':
                    erros += 1
                
                # Mostrar detalhes dos primeiros 10
                if (corrigidos + sem_cobranca + sem_data_pagamento + ja_corretos + erros) <= 10:
                    self._mostrar_detalhe_repasse(repasse, resultado)
        
        # Resumo final
        self.stdout.write(f"\n📈 RESUMO:")
        self.stdout.write(f"   ✅ Corrigidos: {corrigidos}")
        self.stdout.write(f"   ℹ️  Já corretos: {ja_corretos}")
        self.stdout.write(f"   ⚠️  Sem cobrança: {sem_cobranca}")
        self.stdout.write(f"   ⚠️  Sem data pagamento: {sem_data_pagamento}")
        self.stdout.write(f"   ❌ Erros: {erros}")
        
        if dry_run and corrigidos > 0:
            self.stdout.write(
                self.style.SUCCESS(f"\n🚀 Para aplicar as correções, execute sem --dry-run")
            )
    
    def _corrigir_repasse(self, repasse, dry_run):
        """Corrige um repasse específico"""
        try:
            # Verificar se tem cobrança
            if not repasse.cobranca:
                return {'acao': 'sem_cobranca', 'motivo': 'Repasse não tem cobrança associada'}
            
            # Obter data de pagamento
            data_pagamento = getattr(repasse.cobranca, 'data_pagamento', None)
            if not data_pagamento:
                return {'acao': 'sem_data_pagamento', 'motivo': 'Cobrança não tem data_pagamento'}
            
            # Calcular nova data baseada na política
            nova_data = self._calcular_nova_data_repasse(repasse, data_pagamento)
            
            # Verificar se precisa corrigir
            if repasse.data_prevista == nova_data:
                return {
                    'acao': 'ja_correto',
                    'data_atual': repasse.data_prevista,
                    'data_calculada': nova_data
                }
            
            # Aplicar correção se não for dry-run
            data_anterior = repasse.data_prevista
            if not dry_run:
                repasse.data_prevista = nova_data
                repasse.save(update_fields=['data_prevista'])
            
            return {
                'acao': 'corrigido',
                'data_anterior': data_anterior,
                'data_nova': nova_data,
                'data_pagamento': data_pagamento,
                'dias_diferenca': (nova_data - data_anterior).days
            }
            
        except Exception as e:
            return {'acao': 'erro', 'motivo': str(e)}
    
    def _calcular_nova_data_repasse(self, repasse, data_pagamento):
        """Calcula a nova data de repasse baseada na política"""
        contrato = repasse.contrato
        
        # Verificar se tem política específica
        if hasattr(contrato, 'politica_repasse') and contrato.politica_repasse:
            politica = contrato.politica_repasse
            
            # Usar método da política se existir
            if hasattr(politica, 'calcular_data_repasse'):
                return politica.calcular_data_repasse(data_pagamento)
            
            # Fallback: usar configurações da política
            dias_apos = getattr(politica, 'dias_apos_recebimento', 2)
            tipo_dias = getattr(politica, 'tipo_dias', 'uteis')
            
            if tipo_dias == 'uteis':
                return self._adicionar_dias_uteis(data_pagamento, dias_apos)
            else:
                return data_pagamento + timedelta(days=dias_apos)
        
        # Padrão: 2 dias úteis
        return self._adicionar_dias_uteis(data_pagamento, 2)
    
    def _adicionar_dias_uteis(self, data_inicial, quantidade_dias):
        """Adiciona dias úteis"""
        data_atual = data_inicial
        dias_adicionados = 0
        
        while dias_adicionados < quantidade_dias:
            data_atual = data_atual + timedelta(days=1)
            if data_atual.weekday() < 5:  # Segunda a sexta
                dias_adicionados += 1
        
        return data_atual
    
    def _mostrar_detalhe_repasse(self, repasse, resultado):
        """Mostra detalhes de um repasse específico"""
        if resultado['acao'] == 'corrigido':
            self.stdout.write(
                f"   🔧 Repasse #{repasse.id}: "
                f"{resultado['data_anterior'].strftime('%d/%m/%Y')} → "
                f"{resultado['data_nova'].strftime('%d/%m/%Y')} "
                f"(cobrança paga em {resultado['data_pagamento'].strftime('%d/%m/%Y')})"
            )
        elif resultado['acao'] == 'ja_correto':
            self.stdout.write(
                f"   ✅ Repasse #{repasse.id}: "
                f"já correto ({resultado['data_atual'].strftime('%d/%m/%Y')})"
            )
        elif resultado['acao'] == 'sem_cobranca':
            self.stdout.write(
                f"   ⚠️  Repasse #{repasse.id}: sem cobrança associada"
            )
        elif resultado['acao'] == 'sem_data_pagamento':
            self.stdout.write(
                f"   ⚠️  Repasse #{repasse.id}: cobrança #{repasse.cobranca.id} sem data_pagamento"
            )
        elif resultado['acao'] == 'erro':
            self.stdout.write(
                f"   ❌ Repasse #{repasse.id}: erro - {resultado['motivo']}"
            )


# ==================== SCRIPT ALTERNATIVO VIA SHELL ====================

def corrigir_repasses_via_shell():
    """
    Função para ser executada no shell do Django
    
    Uso:
    python manage.py shell
    >>> exec(open('corrigir_repasses.py').read())
    """
    
    from financeiro.models.repasse import Repasse
    from datetime import timedelta
    
    def adicionar_dias_uteis(data_inicial, quantidade_dias):
        data_atual = data_inicial
        dias_adicionados = 0
        
        while dias_adicionados < quantidade_dias:
            data_atual = data_atual + timedelta(days=1)
            if data_atual.weekday() < 5:
                dias_adicionados += 1
        
        return data_atual
    
    print("🔧 Corrigindo repasses...")
    
    repasses = Repasse.objects.filter(
        status='pendente',
        cobranca__isnull=False
    ).select_related('cobranca', 'contrato')
    
    corrigidos = 0
    
    for repasse in repasses:
        try:
            # Obter data de pagamento
            data_pagamento = getattr(repasse.cobranca, 'data_pagamento', None)
            if not data_pagamento:
                continue
            
            # Calcular nova data (2 dias úteis padrão)
            nova_data = adicionar_dias_uteis(data_pagamento, 2)
            
            # Aplicar correção
            if repasse.data_prevista != nova_data:
                print(f"Repasse #{repasse.id}: {repasse.data_prevista} → {nova_data}")
                repasse.data_prevista = nova_data
                repasse.save()
                corrigidos += 1
                
        except Exception as e:
            print(f"Erro no repasse #{repasse.id}: {e}")
    
    print(f"✅ {corrigidos} repasses corrigidos!")


# ==================== EXEMPLO DE VERIFICAÇÃO ====================

def verificar_repasses_exemplo():
    """
    Exemplo para verificar alguns repasses específicos
    """
    
    print("📊 VERIFICAÇÃO DE REPASSES")
    print("=" * 50)
    
    from financeiro.models.repasse import Repasse
    
    repasses = Repasse.objects.filter(
        status='pendente'
    ).select_related('cobranca', 'contrato')[:10]
    
    for repasse in repasses:
        print(f"\n🔍 Repasse #{repasse.id}:")
        print(f"   Data prevista atual: {repasse.data_prevista}")
        
        if repasse.cobranca:
            data_pagamento = getattr(repasse.cobranca, 'data_pagamento', None)
            if data_pagamento:
                print(f"   Data pagamento cobrança: {data_pagamento}")
                
                # Calcular como deveria ser (2 dias úteis)
                data_correta = adicionar_dias_uteis(data_pagamento, 2)
                print(f"   Data que deveria ser: {data_correta}")
                
                if repasse.data_prevista == data_correta:
                    print("   ✅ Correto!")
                else:
                    print("   ❌ Precisa correção!")
            else:
                print("   ⚠️  Cobrança sem data_pagamento")
        else:
            print("   ⚠️  Sem cobrança associada")

if __name__ == "__main__":
    # Para executar diretamente
    verificar_repasses_exemplo()