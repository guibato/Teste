# financeiro/services/repasse/repasse_service.py - CORREÇÕES

from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone
from django.db import transaction
import logging

logger = logging.getLogger(__name__)

class RepasseService:
    """
    Service para cálculo e criação de repasses com correção de dias úteis
    """
    
    # CONFIGURAÇÕES PADRÃO
    DIAS_UTEIS_PADRAO = 5  # 🔧 CORRIGIDO: Era 2, agora 5 dias úteis
    TAXA_ADMIN_PADRAO = Decimal('8.00')
    
    def __init__(self):
        """Inicializar o serviço com resultados zerados"""
        self.resultados = {
            'criados': 0,
            'processados': 0,
            'agendados': 0,
            'erros': 0,
            'detalhes': []
        }
    
    # ... (métodos anteriores mantidos) ...
    
    @staticmethod
    def _calcular_data_repasse(cobranca):
        """📅 Calcula data prevista do repasse - USANDO MODELO REAL"""
        try:
            logger.info(f"📅 Calculando data de repasse para cobrança {cobranca.id} - Contrato {cobranca.contrato.id}")
            
            data_pagamento = cobranca.data_pagamento or date.today()
            
            # 1. PRIORIDADE: Buscar política específica do contrato
            politica = getattr(cobranca.contrato, 'politica_repasse', None)
            
            if politica and politica.ativa:
                logger.info(f"📋 Política ATIVA encontrada para contrato {cobranca.contrato.id}")
                
                # Usar o método específico da política que já existe no modelo
                if hasattr(politica, 'calcular_data_repasse') and callable(politica.calcular_data_repasse):
                    try:
                        data_customizada = politica.calcular_data_repasse(data_pagamento)
                        logger.info(f"✅ Data calculada pela política: {data_customizada}")
                        return data_customizada
                    except Exception as e:
                        logger.warning(f"⚠️ Erro no método da política: {e}")
                
                # Fallback: usar dias_apos_recebimento da política
                if politica.dias_apos_recebimento:
                    dias_uteis = politica.dias_apos_recebimento
                    logger.info(f"✅ Usando dias_apos_recebimento da política: {dias_uteis} dias")
                    
                    if politica.tipo_dias == 'uteis':
                        data_repasse = RepasseService._adicionar_dias_uteis(data_pagamento, dias_uteis)
                        logger.info(f"📅 Calculado como dias ÚTEIS: {data_repasse}")
                    else:
                        data_repasse = data_pagamento + timedelta(days=dias_uteis)
                        logger.info(f"📅 Calculado como dias CORRIDOS: {data_repasse}")
                    
                    return data_repasse
                else:
                    logger.info(f"📋 Política sem dias_apos_recebimento, usando padrão")
            elif politica and not politica.ativa:
                logger.warning(f"📋 Política encontrada mas INATIVA para contrato {cobranca.contrato.id}")
            else:
                logger.info(f"📋 Nenhuma política encontrada para contrato {cobranca.contrato.id}")
            
            # 2. FALLBACK: Usar padrão do sistema (5 dias úteis)
            dias_uteis = RepasseService.DIAS_UTEIS_PADRAO
            data_repasse = RepasseService._adicionar_dias_uteis(data_pagamento, dias_uteis)
            
            logger.info(f"🔄 FALLBACK: {data_pagamento} + {dias_uteis} dias úteis = {data_repasse}")
            
            return data_repasse
            
        except Exception as e:
            logger.error(f"❌ Erro ao calcular data de repasse: {e}")
            # Fallback absoluto
            data_pagamento = cobranca.data_pagamento or date.today()
            data_fallback = RepasseService._adicionar_dias_uteis(data_pagamento, RepasseService.DIAS_UTEIS_PADRAO)
            logger.warning(f"🆘 Fallback absoluto: {data_fallback}")
            return data_fallback
    
    @staticmethod
    def _obter_dias_uteis_configuracao():
        """⚙️ Obtém configuração de dias úteis do sistema"""
        try:
            # Tentar buscar em configurações do sistema
            from django.conf import settings
            
            # 1. Verificar settings customizado
            if hasattr(settings, 'REPASSE_DIAS_UTEIS'):
                dias = int(settings.REPASSE_DIAS_UTEIS)
                logger.info(f"⚙️ Configuração via settings: {dias} dias")
                return dias
            
            # 2. Verificar tabela de configurações (se existir)
            try:
                from configuracao.models import ConfiguracaoSistema  # Ajuste conforme sua estrutura
                config = ConfiguracaoSistema.objects.filter(
                    chave='repasse_dias_uteis'
                ).first()
                
                if config and config.valor:
                    dias = int(config.valor)
                    logger.info(f"⚙️ Configuração via banco: {dias} dias")
                    return dias
            except ImportError:
                logger.debug("📝 Modelo ConfiguracaoSistema não encontrado")
            
            # 3. Fallback para padrão
            logger.info(f"⚙️ Usando padrão do sistema: {RepasseService.DIAS_UTEIS_PADRAO} dias")
            return RepasseService.DIAS_UTEIS_PADRAO
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao obter configuração: {e}, usando padrão")
            return RepasseService.DIAS_UTEIS_PADRAO
    
    @staticmethod
    def _adicionar_dias_uteis(data_inicial, quantidade_dias):
        """📅 Adiciona dias úteis a uma data - VERSÃO MELHORADA"""
        if quantidade_dias <= 0:
            return data_inicial
        
        data_atual = data_inicial
        dias_adicionados = 0
        
        logger.debug(f"📅 Adicionando {quantidade_dias} dias úteis a partir de {data_inicial}")
        
        # Lista de feriados nacionais (você pode expandir ou buscar de uma tabela)
        feriados = RepasseService._obter_feriados_nacionais(data_inicial.year)
        
        while dias_adicionados < quantidade_dias:
            data_atual = data_atual + timedelta(days=1)
            
            # Verificar se é dia útil (Segunda=0 a Sexta=4)
            if data_atual.weekday() < 5:
                # Verificar se não é feriado
                if data_atual not in feriados:
                    dias_adicionados += 1
                    logger.debug(f"📅 Dia útil {dias_adicionados}/{quantidade_dias}: {data_atual}")
                else:
                    logger.debug(f"📅 Pulando feriado: {data_atual}")
            else:
                logger.debug(f"📅 Pulando fim de semana: {data_atual}")
        
        logger.info(f"📅 Resultado final: {data_inicial} + {quantidade_dias} dias úteis = {data_atual}")
        return data_atual
    
    @staticmethod
    def _obter_feriados_nacionais(ano):
        """🎉 Obtém lista de feriados nacionais para um ano"""
        try:
            # Feriados fixos
            feriados = {
                date(ano, 1, 1),   # Ano Novo
                date(ano, 4, 21),  # Tiradentes
                date(ano, 5, 1),   # Dia do Trabalhador
                date(ano, 9, 7),   # Independência
                date(ano, 10, 12), # Nossa Senhora Aparecida
                date(ano, 11, 2),  # Finados
                date(ano, 11, 15), # Proclamação da República
                date(ano, 12, 25), # Natal
            }
            
            # Tentar calcular feriados móveis (Páscoa, etc.)
            try:
                feriados.update(RepasseService._calcular_feriados_moveis(ano))
            except:
                logger.warning(f"⚠️ Erro ao calcular feriados móveis para {ano}")
            
            # Tentar buscar feriados municipais/estaduais do banco
            try:
                from configuracao.models import Feriado  # Ajuste conforme sua estrutura
                feriados_extras = Feriado.objects.filter(
                    ano=ano,
                    ativo=True
                ).values_list('data', flat=True)
                
                feriados.update(feriados_extras)
            except ImportError:
                logger.debug("📝 Modelo Feriado não encontrado")
            
            logger.debug(f"🎉 {len(feriados)} feriados carregados para {ano}")
            return feriados
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao carregar feriados: {e}")
            return set()
    
    @staticmethod
    def _calcular_feriados_moveis(ano):
        """🥚 Calcula feriados móveis baseados na Páscoa"""
        try:
            # Algoritmo para calcular a Páscoa
            def calcular_pascoa(ano):
                # Algoritmo de Gauss para cálculo da Páscoa
                a = ano % 19
                b = ano // 100
                c = ano % 100
                d = b // 4
                e = b % 4
                f = (b + 8) // 25
                g = (b - f + 1) // 3
                h = (19 * a + b - d - g + 15) % 30
                i = c // 4
                k = c % 4
                l = (32 + 2 * e + 2 * i - h - k) % 7
                m = (a + 11 * h + 22 * l) // 451
                n = (h + l - 7 * m + 114) // 31
                p = (h + l - 7 * m + 114) % 31
                return date(ano, n, p + 1)
            
            pascoa = calcular_pascoa(ano)
            
            return {
                pascoa - timedelta(days=47),  # Carnaval (47 dias antes)
                pascoa - timedelta(days=46),  # Carnaval (46 dias antes)
                pascoa - timedelta(days=2),   # Sexta-feira Santa
                pascoa,                       # Páscoa
                pascoa + timedelta(days=60),  # Corpus Christi
            }
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao calcular feriados móveis: {e}")
            return set()
    
    @staticmethod
    def calcular_data_repasse_manual(data_pagamento, dias_uteis=None):
        """🛠️ Método público para calcular data de repasse manualmente"""
        if dias_uteis is None:
            dias_uteis = RepasseService.DIAS_UTEIS_PADRAO
        
        logger.info(f"🛠️ Cálculo manual: {data_pagamento} + {dias_uteis} dias úteis")
        return RepasseService._adicionar_dias_uteis(data_pagamento, dias_uteis)
    
    @staticmethod
    def debug_politica_contrato(contrato_id):
        """🔍 Debug da política de repasse de um contrato específico - MODELO REAL"""
        try:
            Contrato = apps.get_model("sisimob", "Contrato")
            
            contrato = Contrato.objects.get(id=contrato_id)
            
            print(f"🔍 DEBUG - POLÍTICA DO CONTRATO #{contrato_id}")
            print("=" * 60)
            print(f"📋 Contrato: {contrato}")
            
            # Verificar se tem política
            politica = getattr(contrato, 'politica_repasse', None)
            
            if politica:
                print(f"✅ Política encontrada: {politica}")
                print(f"   - ID: {getattr(politica, 'id', 'N/A')}")
                print(f"   - Ativa: {getattr(politica, 'ativa', 'N/A')}")
                print(f"   - Periodicidade: {getattr(politica, 'periodicidade', 'N/A')}")
                print(f"   - Tipo dias: {getattr(politica, 'tipo_dias', 'N/A')}")
                
                # Campos específicos do modelo
                print("\n📅 Configurações de prazo (do modelo real):")
                print(f"   - dias_apos_recebimento: {getattr(politica, 'dias_apos_recebimento', 'N/A')}")
                print(f"   - dia_mes: {getattr(politica, 'dia_mes', 'N/A')}")
                print(f"   - dia_semana: {getattr(politica, 'dia_semana', 'N/A')}")
                print(f"   - considerar_feriados: {getattr(politica, 'considerar_feriados', 'N/A')}")
                print(f"   - antecipar_fds_feriados: {getattr(politica, 'antecipar_fds_feriados', 'N/A')}")
                
                # Configurações financeiras
                print("\n💰 Configurações financeiras:")
                print(f"   - taxa_admin_personalizada: {getattr(politica, 'taxa_admin_personalizada', 'N/A')}")
                print(f"   - valor_minimo_repasse: {getattr(politica, 'valor_minimo_repasse', 'N/A')}")
                print(f"   - percentual_adiantamento: {getattr(politica, 'percentual_adiantamento', 'N/A')}")
                
                # Testar método calcular_data_repasse se existir
                if hasattr(politica, 'calcular_data_repasse'):
                    print("\n🧪 TESTE DO MÉTODO calcular_data_repasse:")
                    try:
                        from datetime import date
                        data_teste = date.today()
                        resultado = politica.calcular_data_repasse(data_teste)
                        print(f"   Data teste: {data_teste}")
                        print(f"   Resultado: {resultado}")
                        print(f"   Diferença: {(resultado - data_teste).days} dias")
                    except Exception as e:
                        print(f"   ❌ Erro ao testar método: {e}")
                else:
                    print("\n❌ Método calcular_data_repasse não encontrado")
                
                # Simular repasse se método existir
                if hasattr(politica, 'simular_repasse_com_data_pagamento'):
                    print("\n🎯 SIMULAÇÃO DE REPASSE:")
                    try:
                        from datetime import date
                        from decimal import Decimal
                        simulacao = politica.simular_repasse_com_data_pagamento(
                            data_pagamento=date.today(),
                            valor_cobranca=Decimal('1000.00')
                        )
                        for key, value in simulacao.items():
                            print(f"   {key}: {value}")
                    except Exception as e:
                        print(f"   ❌ Erro na simulação: {e}")
                        
            else:
                print("❌ Nenhuma política encontrada para este contrato")
                print(f"🔄 Será usado o padrão: {RepasseService.DIAS_UTEIS_PADRAO} dias úteis")
            
            return politica
            
        except Exception as e:
            print(f"❌ Erro ao buscar política: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    @staticmethod
    def debug_calculo_dias():
        """🐛 Método para debug do cálculo de dias úteis"""
        print("🐛 DEBUG - CÁLCULO DE DIAS ÚTEIS")
        print("=" * 50)
        
        hoje = date.today()
        
        for dias in [1, 2, 3, 5, 10]:
            resultado = RepasseService._adicionar_dias_uteis(hoje, dias)
            weekday_nome = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo'][hoje.weekday()]
            resultado_weekday = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo'][resultado.weekday()]
            print(f"📅 {hoje} ({weekday_nome}) + {dias} dias úteis = {resultado} ({resultado_weekday})")
        
        # Testar com feriados
        feriados = RepasseService._obter_feriados_nacionais(hoje.year)
        print(f"\n🎉 Feriados {hoje.year}: {len(feriados)} encontrados")
        
        # Mostrar próximos feriados
        proximos_feriados = [f for f in sorted(feriados) if f >= hoje][:5]
        if proximos_feriados:
            print("📅 Próximos feriados:")
            for feriado in proximos_feriados:
                weekday = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo'][feriado.weekday()]
                print(f"   - {feriado} ({weekday})")
        
        print(f"\n⚙️ Configuração padrão: {RepasseService.DIAS_UTEIS_PADRAO} dias úteis")


# === FUNÇÃO DE TESTE ===

# === FUNÇÕES DE TESTE ATUALIZADAS ===

def testar_calculo_dias():
    """🧪 Testa o cálculo de dias úteis"""
    print("🧪 TESTANDO CÁLCULO DE DIAS ÚTEIS")
    print("=" * 50)
    
    # Debug do sistema
    RepasseService.debug_calculo_dias()
    
    # Testar casos específicos
    from datetime import datetime
    
    casos_teste = [
        datetime(2025, 7, 1).date(),   # Terça-feira
        datetime(2025, 7, 4).date(),   # Sexta-feira
        datetime(2025, 7, 5).date(),   # Sábado
        datetime(2025, 12, 23).date(), # Véspera do Natal
    ]
    
    print("\n📊 CASOS DE TESTE:")
    for data_teste in casos_teste:
        resultado = RepasseService.calcular_data_repasse_manual(data_teste, 5)
        weekday_nome = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo'][data_teste.weekday()]
        resultado_weekday = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo'][resultado.weekday()]
        
        print(f"   {data_teste} ({weekday_nome}) + 5 dias úteis = {resultado} ({resultado_weekday})")


def testar_politica_contrato(contrato_id):
    """🧪 Testa política específica de um contrato"""
    print(f"🧪 TESTANDO POLÍTICA DO CONTRATO #{contrato_id}")
    print("=" * 60)
    
    try:
        # Debug da política
        politica = RepasseService.debug_politica_contrato(contrato_id)
        
        if politica:
            # Simular cálculo de data
            from datetime import date
            data_teste = date.today()
            
            print(f"\n📅 SIMULAÇÃO DE CÁLCULO:")
            print(f"Data base: {data_teste}")
            
            # Criar objeto mock de cobrança para teste
            class MockCobranca:
                def __init__(self, contrato, data_pagamento):
                    self.contrato = contrato
                    self.data_pagamento = data_pagamento
                    self.id = 'TESTE'
            
            Contrato = apps.get_model("sisimob", "Contrato")
            contrato = Contrato.objects.get(id=contrato_id)
            cobranca_mock = MockCobranca(contrato, data_teste)
            
            # Calcular data usando o service
            data_repasse = RepasseService._calcular_data_repasse(cobranca_mock)
            
            print(f"Data calculada: {data_repasse}")
            
            dias_diferenca = (data_repasse - data_teste).days
            print(f"Diferença: {dias_diferenca} dias corridos")
            
        return politica
        
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        return None


def listar_contratos_com_politica():
    """📋 Lista contratos que têm política de repasse - MODELO REAL"""
    try:
        Contrato = apps.get_model("sisimob", "Contrato")
        
        print("📋 CONTRATOS COM POLÍTICA DE REPASSE")
        print("=" * 60)
        
        # Contratos com política
        contratos = Contrato.objects.filter(
            politica_repasse__isnull=False
        ).select_related('politica_repasse')
        
        if contratos.exists():
            print("✅ CONTRATOS COM POLÍTICA:")
            for contrato in contratos:
                politica = contrato.politica_repasse
                
                # Obter dados específicos do modelo
                ativa = getattr(politica, 'ativa', 'N/A')
                dias_apos = getattr(politica, 'dias_apos_recebimento', 'N/A')
                tipo_dias = getattr(politica, 'tipo_dias', 'N/A')
                periodicidade = getattr(politica, 'periodicidade', 'N/A')
                
                status = "🟢 ATIVA" if ativa else "🔴 INATIVA"
                
                print(f"   Contrato #{contrato.id}: {dias_apos} dias {tipo_dias} ({periodicidade}) - {status}")
                
                # Mostrar dados adicionais se existirem
                if hasattr(politica, 'taxa_admin_personalizada') and politica.taxa_admin_personalizada:
                    print(f"      Taxa personalizada: {politica.taxa_admin_personalizada}%")
                
                if hasattr(politica, 'valor_minimo_repasse') and politica.valor_minimo_repasse:
                    print(f"      Valor mínimo: R$ {politica.valor_minimo_repasse}")
        else:
            print("❌ Nenhum contrato com política encontrado")
        
        # Contratos sem política
        contratos_ativos = Contrato.objects.filter(ativo=True)
        sem_politica = contratos_ativos.filter(politica_repasse__isnull=True).count()
        
        print(f"\n📊 ESTATÍSTICAS:")
        print(f"   - Com política: {contratos.count()}")
        print(f"   - Sem política (ativos): {sem_politica}")
        print(f"   - Total ativos: {contratos_ativos.count()}")
        print(f"   - Padrão usado: {RepasseService.DIAS_UTEIS_PADRAO} dias úteis")
        
        # Políticas inativas
        inativas = contratos.filter(politica_repasse__ativa=False).count()
        if inativas > 0:
            print(f"   - ⚠️ Políticas inativas: {inativas}")
        
    except Exception as e:
        print(f"❌ Erro ao listar contratos: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("🚀 EXECUTANDO TESTES DO REPASSE SERVICE")
    print("=" * 60)
    
    # Teste básico de dias úteis
    testar_calculo_dias()
    
    print("\n" + "=" * 60)
    
    # Listar contratos com política
    listar_contratos_com_politica()
    
    # Exemplo de como testar um contrato específico:
    # testar_politica_contrato(1)  # Substitua 1 pelo ID do contrato