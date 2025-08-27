# financeiro/management/commands/testar_calculo_datas.py

from django.core.management.base import BaseCommand
from datetime import date, timedelta

class Command(BaseCommand):
    help = 'Testa o cálculo de datas de repasse'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--data-pagamento',
            type=str,
            default='2025-06-02',
            help='Data de pagamento da cobrança (YYYY-MM-DD)',
        )
        parser.add_argument(
            '--dias',
            type=int,
            default=5,
            help='Quantidade de dias para repasse',
        )
        parser.add_argument(
            '--tipo',
            choices=['uteis', 'corridos'],
            default='uteis',
            help='Tipo de dias (úteis ou corridos)',
        )
    
    def handle(self, *args, **options):
        data_pagamento_str = options['data_pagamento']
        quantidade_dias = options['dias']
        tipo_dias = options['tipo']
        
        # Converter string para date
        data_pagamento = date.fromisoformat(data_pagamento_str)
        
        self.stdout.write(
            self.style.SUCCESS(f'\n🧮 TESTE DE CÁLCULO DE DATAS DE REPASSE')
        )
        
        self.stdout.write(f"\n📅 Dados de entrada:")
        self.stdout.write(f"   Data pagamento cobrança: {data_pagamento.strftime('%d/%m/%Y (%A)')}")
        self.stdout.write(f"   Política: {quantidade_dias} dias {tipo_dias}")
        
        # Calcular data do repasse
        if tipo_dias == 'uteis':
            data_repasse = self._adicionar_dias_uteis(data_pagamento, quantidade_dias)
        else:
            data_repasse = data_pagamento + timedelta(days=quantidade_dias)
        
        # Exibir resultado
        self.stdout.write(f"\n✅ Resultado:")
        self.stdout.write(f"   Data prevista repasse: {data_repasse.strftime('%d/%m/%Y (%A)')}")
        self.stdout.write(f"   Total de dias corridos: {(data_repasse - data_pagamento).days}")
        
        # Mostrar contagem detalhada se for dias úteis
        if tipo_dias == 'uteis':
            self.stdout.write(f"\n📊 Contagem detalhada (dias úteis):")
            self._mostrar_contagem_detalhada(data_pagamento, quantidade_dias)
        
        # Testar cenários adicionais
        self.stdout.write(f"\n🎯 Outros cenários para comparação:")
        self._testar_cenarios_extras()
    
    def _adicionar_dias_uteis(self, data_inicial, quantidade_dias):
        """Adiciona quantidade específica de dias úteis"""
        data_atual = data_inicial
        dias_adicionados = 0
        
        while dias_adicionados < quantidade_dias:
            data_atual = data_atual + timedelta(days=1)
            
            # Verificar se é dia útil (segunda=0 a sexta=4)
            if data_atual.weekday() < 5:
                dias_adicionados += 1
        
        return data_atual
    
    def _mostrar_contagem_detalhada(self, data_inicial, quantidade_dias):
        """Mostra passo a passo da contagem de dias úteis"""
        data_atual = data_inicial
        dias_adicionados = 0
        
        dias_semana = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
        
        while dias_adicionados < quantidade_dias:
            data_atual = data_atual + timedelta(days=1)
            dia_nome = dias_semana[data_atual.weekday()]
            
            if data_atual.weekday() < 5:  # Dia útil
                dias_adicionados += 1
                self.stdout.write(
                    f"   ✅ Dia útil {dias_adicionados}: {data_atual.strftime('%d/%m')} ({dia_nome})"
                )
            else:  # Final de semana
                self.stdout.write(
                    f"   ⏭️  Pulando: {data_atual.strftime('%d/%m')} ({dia_nome}) - Final de semana"
                )
    
    def _testar_cenarios_extras(self):
        """Testa cenários comuns para validação"""
        cenarios = [
            # (data_pagamento, dias, tipo, descrição)
            (date(2025, 6, 2), 5, 'uteis', 'Segunda → 5 dias úteis'),
            (date(2025, 6, 6), 3, 'uteis', 'Sexta → 3 dias úteis'),
            (date(2025, 6, 7), 1, 'uteis', 'Sábado → 1 dia útil'),
            (date(2025, 6, 8), 2, 'uteis', 'Domingo → 2 dias úteis'),
            (date(2025, 6, 2), 5, 'corridos', 'Segunda → 5 dias corridos'),
            (date(2025, 6, 6), 3, 'corridos', 'Sexta → 3 dias corridos'),
        ]
        
        for data_pag, dias, tipo, descricao in cenarios:
            if tipo == 'uteis':
                data_resultado = self._adicionar_dias_uteis(data_pag, dias)
            else:
                data_resultado = data_pag + timedelta(days=dias)
            
            self.stdout.write(
                f"   {descricao}: "
                f"{data_pag.strftime('%d/%m')} → "
                f"{data_resultado.strftime('%d/%m (%A)')}"
            )


# ==================== COMANDO PARA TESTAR POLÍTICAS REAIS ====================

# financeiro/management/commands/simular_repasses_periodo.py

from django.core.management.base import BaseCommand
from financeiro.models.repasse import PoliticaRepasseContrato
Contrato = apps.get_model("sisimob", "Contrato")
from datetime import date, timedelta
import calendar

class Command(BaseCommand):
    help = 'Simula repasses para um período específico'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--data-inicio',
            type=str,
            default='2025-06-01',
            help='Data início do período (YYYY-MM-DD)',
        )
        parser.add_argument(
            '--data-fim',
            type=str,
            default='2025-06-30',
            help='Data fim do período (YYYY-MM-DD)',
        )
        parser.add_argument(
            '--contrato-id',
            type=int,
            help='ID específico do contrato para testar',
        )
    
    def handle(self, *args, **options):
        data_inicio = date.fromisoformat(options['data_inicio'])
        data_fim = date.fromisoformat(options['data_fim'])
        contrato_id = options.get('contrato_id')
        
        self.stdout.write(
            self.style.SUCCESS(f'\n📊 SIMULAÇÃO DE REPASSES - PERÍODO')
        )
        
        self.stdout.write(f"\n📅 Período: {data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}")
        
        # Buscar contratos com política
        if contrato_id:
            contratos = Contrato.objects.filter(id=contrato_id, politica_repasse__isnull=False)
        else:
            contratos = Contrato.objects.filter(
                ativo=True,
                politica_repasse__isnull=False
            )[:10]  # Limitar a 10 para não sobrecarregar
        
        if not contratos:
            self.stdout.write(
                self.style.WARNING('Nenhum contrato com política encontrado!')
            )
            return
        
        self.stdout.write(f"\n🏠 Simulando {contratos.count()} contrato(s):")
        
        # Simular cada data do período
        data_atual = data_inicio
        simulacoes = []
        
        while data_atual <= data_fim:
            for contrato in contratos:
                politica = contrato.politica_repasse
                
                # Simular pagamento nesta data
                simulacao = self._simular_pagamento_data(contrato, politica, data_atual)
                simulacoes.append(simulacao)
            
            data_atual += timedelta(days=1)
        
        # Agrupar e exibir resultados
        self._exibir_resultados_agrupados(simulacoes)
    
    def _simular_pagamento_data(self, contrato, politica, data_pagamento):
        """Simula um pagamento em uma data específica"""
        try:
            # Usar o método corrigido se existir
            if hasattr(politica, 'calcular_data_repasse'):
                data_repasse = politica.calcular_data_repasse(data_pagamento)
            else:
                # Fallback para lógica simples
                if politica.dias_apos_recebimento:
                    if politica.tipo_dias == 'uteis':
                        data_repasse = self._adicionar_dias_uteis(data_pagamento, politica.dias_apos_recebimento)
                    else:
                        data_repasse = data_pagamento + timedelta(days=politica.dias_apos_recebimento)
                else:
                    data_repasse = data_pagamento + timedelta(days=2)  # Padrão
            
            dias_para_repasse = (data_repasse - data_pagamento).days
            
            return {
                'contrato_id': contrato.id,
                'data_pagamento': data_pagamento,
                'data_repasse': data_repasse,
                'dias_para_repasse': dias_para_repasse,
                'politica': {
                    'dias_apos': politica.dias_apos_recebimento,
                    'tipo_dias': politica.tipo_dias,
                    'periodicidade': politica.periodicidade
                },
                'sucesso': True
            }
            
        except Exception as e:
            return {
                'contrato_id': contrato.id,
                'data_pagamento': data_pagamento,
                'erro': str(e),
                'sucesso': False
            }
    
    def _adicionar_dias_uteis(self, data_inicial, quantidade_dias):
        """Adiciona dias úteis"""
        data_atual = data_inicial
        dias_adicionados = 0
        
        while dias_adicionados < quantidade_dias:
            data_atual = data_atual + timedelta(days=1)
            if data_atual.weekday() < 5:
                dias_adicionados += 1
        
        return data_atual
    
    def _exibir_resultados_agrupados(self, simulacoes):
        """Exibe resultados agrupados por contrato"""
        from collections import defaultdict
        
        por_contrato = defaultdict(list)
        
        for sim in simulacoes:
            if sim['sucesso']:
                por_contrato[sim['contrato_id']].append(sim)
        
        for contrato_id, sims in por_contrato.items():
            self.stdout.write(f"\n📋 Contrato #{contrato_id}:")
            
            # Estatísticas
            dias_repasse = [s['dias_para_repasse'] for s in sims]
            media_dias = sum(dias_repasse) / len(dias_repasse) if dias_repasse else 0
            
            self.stdout.write(f"   Total simulações: {len(sims)}")
            self.stdout.write(f"   Média dias para repasse: {media_dias:.1f}")
            self.stdout.write(f"   Variação: {min(dias_repasse)} a {max(dias_repasse)} dias")
            
            # Exemplos
            self.stdout.write(f"   Exemplos:")
            for sim in sims[:3]:  # Mostrar apenas 3 exemplos
                self.stdout.write(
                    f"     {sim['data_pagamento'].strftime('%d/%m')} → "
                    f"{sim['data_repasse'].strftime('%d/%m')} "
                    f"({sim['dias_para_repasse']} dias)"
                )
            
            if len(sims) > 3:
                self.stdout.write(f"     ... e mais {len(sims) - 3} simulações")