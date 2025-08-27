# financeiro/signals.py
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from decimal import Decimal
from datetime import date, timedelta
import logging

logger = logging.getLogger(__name__)

# Import dos modelos (com fallbacks seguros)
try:
    from .models.cobranca import Cobranca
except ImportError:
    try:
        from financeiro.models.cobranca import Cobranca
    except ImportError:
        logger.warning("Modelo Cobranca não encontrado")
        Cobranca = None

try:
    from .models.repasse import Repasse, PoliticaRepasseContrato, AgendamentoRepasse
except ImportError:
    try:
        from financeiro.models.repasse import Repasse, PoliticaRepasseContrato, AgendamentoRepasse
    except ImportError:
        logger.warning("Modelos de Repasse não encontrados")
        Repasse = None
        PoliticaRepasseContrato = None
        AgendamentoRepasse = None

try:
    Contrato = apps.get_model("sisimob", "Contrato")
except ImportError:
    logger.warning("Modelo Contrato não encontrado")
    Contrato = None


# === SIGNAL PRINCIPAL ===
if Cobranca and Repasse:
    @receiver(post_save, sender=Cobranca)
    def criar_repasse_automatico_signal(sender, instance, created, **kwargs):
        """
        🤖 Signal que cria repasse automaticamente quando cobrança é paga
        """
        # Verificar se a cobrança foi marcada como paga
        if instance.status != 'paga':
            return
        
        # Verificar se já existe repasse para esta cobrança
        if Repasse.objects.filter(cobranca=instance).exists():
            logger.info(f"Cobrança {instance.id} já possui repasse - pulando")
            return
        
        try:
            logger.info(f"🚀 Processando cobrança {instance.id} para criação automática de repasse")
            
            # Criar repasse usando função segura
            repasse = _criar_repasse_seguro(instance)
            
            if repasse:
                logger.info(f"✅ Repasse {repasse.id} criado automaticamente para cobrança {instance.id}")
                print(f"✅ Repasse {repasse.id} criado automaticamente para cobrança {instance.id}")
            else:
                logger.warning(f"⚠️ Não foi possível criar repasse para cobrança {instance.id}")
                print(f"⚠️ Não foi possível criar repasse para cobrança {instance.id}")
                
        except Exception as e:
            logger.error(f"❌ Erro ao criar repasse automático para cobrança {instance.id}: {e}")
            print(f"❌ Erro ao criar repasse automático para cobrança {instance.id}: {e}")


    @receiver(pre_save, sender=Cobranca)
    def detectar_mudanca_status_cobranca(sender, instance, **kwargs):
        """
        🔍 Detecta quando status da cobrança muda para 'paga'
        """
        if not instance.pk:
            return  # Novo objeto
        
        try:
            # Buscar estado anterior
            cobranca_anterior = Cobranca.objects.get(pk=instance.pk)
            
            # Se mudou de outro status para 'paga'
            if (cobranca_anterior.status != 'paga' and 
                instance.status == 'paga'):
                
                logger.info(f"🔄 Cobrança {instance.id} mudou para 'paga' - será processada pelo signal")
                print(f"🔄 Cobrança {instance.id} mudou para 'paga'")
                
                # Garantir que tem data de pagamento
                if not instance.data_pagamento:
                    instance.data_pagamento = date.today()
                    logger.info(f"📅 Data de pagamento definida para cobrança {instance.id}: {instance.data_pagamento}")
                
        except Cobranca.DoesNotExist:
            pass  # Cobrança nova
        except Exception as e:
            logger.error(f"Erro ao detectar mudança de status da cobrança {instance.id}: {e}")


# === FUNÇÕES AUXILIARES ===

def _criar_repasse_seguro(cobranca):
    """
    🛡️ Cria repasse de forma segura com todas as validações
    """
    try:
        print(f"🔄 Processando cobrança {cobranca.id}")
        
        # === VALIDAÇÕES BÁSICAS ===
        if not cobranca.data_pagamento:
            print(f"⚠️ Sem data de pagamento - definindo hoje")
            cobranca.data_pagamento = date.today()
            cobranca.save(update_fields=['data_pagamento'])
        
        contrato = cobranca.contrato
        if not contrato:
            print(f"❌ Cobrança sem contrato")
            return None
        
        print(f"✅ Contrato: {contrato.id}")
        
        # === VERIFICAR POLÍTICA DO CONTRATO ===
        politica = _obter_politica_contrato(contrato)
        
        if not politica:
            print(f"❌ Contrato sem política ativa")
            # Tentar criar agendamento
            _criar_agendamento_pendente(cobranca, "Aguardando política de repasse")
            return None
        
        print(f"✅ Política encontrada: ID {getattr(politica, 'id', 'N/A')}")
        
        # === VERIFICAR PROPRIETÁRIO ===
        proprietario = _obter_proprietario_contrato(contrato)
        
        if not proprietario:
            print(f"❌ Contrato sem proprietário")
            return None
        
        print(f"✅ Proprietário: {proprietario.nome}")
        
        # === CALCULAR VALORES ===
        valores = _calcular_valores_repasse(cobranca, politica)
        
        if not valores:
            print(f"❌ Erro ao calcular valores")
            return None
        
        print(f"💰 Valor base: R$ {valores['valor_base']:.2f}")
        print(f"🏦 Taxa admin: {valores['taxa_percentual']}% = R$ {valores['valor_taxa_admin']:.2f}")
        print(f"💵 Valor líquido: R$ {valores['valor_liquido']:.2f}")
        
        # === CALCULAR DATA PREVISTA ===
        data_prevista = _calcular_data_repasse(cobranca, politica)
        print(f"📅 Data prevista: {data_prevista}")
        
        # === CRIAR REPASSE ===
        repasse = Repasse.objects.create(
            proprietario=proprietario,
            cobranca=cobranca,
            contrato=contrato,
            
            # Valores calculados
            valor=valores['valor_base'],
            valor_desconto=Decimal('0.00'),
            valor_taxa_admin=valores['valor_taxa_admin'],
            
            # Datas e referência
            data_prevista=data_prevista,
            mes_referencia=cobranca.mes_referencia,
            ano_referencia=cobranca.ano_referencia,
            
            # Status e tipo
            status='pendente',
            tipo='automatico',
            
            # Descrição detalhada
            descricao=f"Repasse automático - {cobranca.mes_referencia:02d}/{cobranca.ano_referencia}",
            observacoes=f"Criado automaticamente via signal. Taxa: {valores['taxa_percentual']}% = R$ {valores['valor_taxa_admin']:.2f}"
        )
        
        print(f"🎉 REPASSE CRIADO: #{repasse.id}")
        print(f"   Status: {repasse.status}")
        print(f"   Valor total: R$ {repasse.valor:.2f}")
        print(f"   Taxa admin: R$ {repasse.valor_taxa_admin:.2f}")
        print(f"   Data prevista: {repasse.data_prevista}")
        
        return repasse
        
    except Exception as e:
        print(f"❌ ERRO: {e}")
        logger.error(f"Erro ao criar repasse para cobrança {cobranca.id}: {e}")
        import traceback
        traceback.print_exc()
        return None


def _obter_politica_contrato(contrato):
    """
    🏛️ Obtém política ativa do contrato
    """
    try:
        if hasattr(contrato, 'politica_repasse') and contrato.politica_repasse:
            politica = contrato.politica_repasse
            
            if politica.ativa:
                return politica
            else:
                print(f"⚠️ Política do contrato {contrato.id} existe mas está inativa")
        
        # Se não tem política específica, tentar política global
        if PoliticaRepasseContrato:
            try:
                from .models.repasse import PoliticaRepasseGlobal
                politica_global = PoliticaRepasseGlobal.objects.filter(ativa=True).first()
                
                if politica_global:
                    print(f"ℹ️ Usando política global {politica_global.id} para contrato {contrato.id}")
                    return politica_global
                    
            except Exception:
                pass
        
        return None
        
    except Exception as e:
        print(f"❌ Erro ao obter política para contrato {contrato.id}: {e}")
        return None


def _obter_proprietario_contrato(contrato):
    """
    👤 Obtém proprietário do contrato (compatível com ForeignKey e ManyToMany)
    """
    try:
        if hasattr(contrato, 'proprietario'):
            if hasattr(contrato.proprietario, 'first'):
                # ManyToMany
                return contrato.proprietario.first()
            else:
                # ForeignKey
                return contrato.proprietario
        return None
        
    except Exception as e:
        print(f"❌ Erro ao obter proprietário do contrato {contrato.id}: {e}")
        return None


def _calcular_valores_repasse(cobranca, politica):
    """
    💰 Calcula valores do repasse baseado na cobrança e política
    """
    try:
        # Valor base da cobrança
        valor_base = cobranca.valor
        
        # Obter taxa administrativa
        if hasattr(politica, 'get_taxa_admin'):
            taxa_percentual = politica.get_taxa_admin()
        elif hasattr(politica, 'taxa_admin_personalizada') and politica.taxa_admin_personalizada:
            taxa_percentual = politica.taxa_admin_personalizada
        elif hasattr(politica, 'taxa_admin_padrao'):
            taxa_percentual = politica.taxa_admin_padrao
        else:
            taxa_percentual = Decimal('8.00')  # Padrão fallback
        
        # Calcular valores
        valor_taxa_admin = valor_base * (taxa_percentual / 100)
        valor_liquido = valor_base - valor_taxa_admin
        
        # Verificar valor mínimo
        valor_minimo = getattr(politica, 'valor_minimo_repasse', Decimal('0.00')) or Decimal('0.00')
        
        if valor_liquido < valor_minimo:
            print(f"⚠️ Valor líquido R$ {valor_liquido:.2f} abaixo do mínimo R$ {valor_minimo:.2f}")
        
        return {
            'valor_base': valor_base,
            'taxa_percentual': taxa_percentual,
            'valor_taxa_admin': valor_taxa_admin,
            'valor_liquido': valor_liquido,
            'valor_minimo': valor_minimo,
            'acima_minimo': valor_liquido >= valor_minimo
        }
        
    except Exception as e:
        print(f"❌ Erro ao calcular valores para cobrança {cobranca.id}: {e}")
        return None


def _calcular_data_repasse(cobranca, politica):
    """
    📅 Calcula data prevista do repasse
    """
    try:
        data_pagamento = cobranca.data_pagamento or date.today()
        
        # Tentar usar método da política específica
        if hasattr(politica, 'calcular_data_repasse'):
            return politica.calcular_data_repasse(data_pagamento)
        
        # Fallback: usar dias após recebimento
        dias_apos = getattr(politica, 'dias_apos_recebimento', 5) or 5
        tipo_dias = getattr(politica, 'tipo_dias', 'uteis')
        
        if tipo_dias == 'uteis':
            return _adicionar_dias_uteis(data_pagamento, dias_apos)
        else:
            return data_pagamento + timedelta(days=dias_apos)
            
    except Exception as e:
        print(f"⚠️ Erro ao calcular data de repasse: {e}")
        # Fallback final
        return (cobranca.data_pagamento or date.today()) + timedelta(days=5)


def _adicionar_dias_uteis(data_inicial, quantidade_dias):
    """
    📅 Adiciona dias úteis a uma data
    """
    data_atual = data_inicial
    dias_adicionados = 0
    
    while dias_adicionados < quantidade_dias:
        data_atual = data_atual + timedelta(days=1)
        
        # Segunda=0 a Sexta=4 são dias úteis
        if data_atual.weekday() < 5:
            dias_adicionados += 1
    
    return data_atual


def _criar_agendamento_pendente(cobranca, motivo):
    """
    📋 Cria agendamento para processar depois quando política for configurada
    """
    try:
        if not AgendamentoRepasse:
            print("ℹ️ AgendamentoRepasse não disponível")
            return None
            
        agendamento = AgendamentoRepasse.objects.create(
            contrato=cobranca.contrato,
            proprietario=_obter_proprietario_contrato(cobranca.contrato),
            data_agendada=date.today() + timedelta(days=1),
            valor_previsto=cobranca.valor,
            mes_referencia=cobranca.mes_referencia,
            ano_referencia=cobranca.ano_referencia,
            status='agendado',
            detalhes_processamento=f"Cobrança {cobranca.id} paga em {cobranca.data_pagamento}. {motivo}"
        )
        
        print(f"📋 Agendamento {agendamento.id} criado para cobrança {cobranca.id}")
        return agendamento
        
    except Exception as e:
        print(f"❌ Erro ao criar agendamento para cobrança {cobranca.id}: {e}")
        return None


# === FUNÇÕES PARA TESTE E PROCESSAMENTO MANUAL ===

def teste_cobranca_especifica(cobranca_id):
    """
    🧪 Testa criação de repasse para cobrança específica
    """
    if not Cobranca or not Repasse:
        print("❌ Modelos não disponíveis")
        return None
        
    try:
        cobranca = Cobranca.objects.get(id=cobranca_id)
        
        print(f"🧪 TESTE: Cobrança {cobranca_id}")
        print(f"   Status: {cobranca.status}")
        print(f"   Valor: R$ {cobranca.valor:.2f}")
        print(f"   Data pagamento: {cobranca.data_pagamento}")
        print(f"   Contrato: {cobranca.contrato.id}")
        
        # Verificar proprietário
        proprietario = _obter_proprietario_contrato(cobranca.contrato)
        if proprietario:
            print(f"   Proprietário: {proprietario.nome}")
        
        # Verificar política
        if hasattr(cobranca.contrato, 'politica_repasse') and cobranca.contrato.politica_repasse:
            politica = cobranca.contrato.politica_repasse
            print(f"   Política: #{politica.id} (ativa: {politica.ativa})")
        else:
            print(f"   ❌ SEM POLÍTICA!")
        
        # Verificar repasse existente
        repasse_existente = Repasse.objects.filter(cobranca=cobranca).first()
        
        if repasse_existente:
            print(f"   ✅ JÁ TEM REPASSE: #{repasse_existente.id}")
            print(f"      Valor: R$ {repasse_existente.valor:.2f}")
            print(f"      Status: {repasse_existente.status}")
            return repasse_existente
        else:
            print(f"   ❌ SEM REPASSE - criando agora...")
            
            # Criar repasse
            if cobranca.status == 'paga':
                repasse_novo = _criar_repasse_seguro(cobranca)
                
                if repasse_novo:
                    print(f"\n🎉 SUCESSO! Repasse criado para cobrança {cobranca_id}!")
                    return repasse_novo
                else:
                    print(f"\n❌ FALHA ao criar repasse para cobrança {cobranca_id}")
                    return None
            else:
                print(f"   ⚠️ Cobrança não está paga - status: {cobranca.status}")
                return None

    except Cobranca.DoesNotExist:
        print(f"❌ Cobrança {cobranca_id} não encontrada!")
        return None
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return None


def processar_cobrancas_pagas_sem_repasse():
    """
    🔄 Processa todas as cobranças pagas que não têm repasse
    """
    if not Cobranca or not Repasse:
        print("❌ Modelos não disponíveis")
        return {'error': 'Modelos não disponíveis'}
    
    print("🔄 Processando cobranças pagas sem repasse...")
    
    # Buscar cobranças pagas sem repasse
    cobrancas_sem_repasse = Cobranca.objects.filter(
        status='paga'
    ).exclude(
        id__in=Repasse.objects.values_list('cobranca_id', flat=True)
    )
    
    total_cobrancas = cobrancas_sem_repasse.count()
    criados = 0
    erros = 0
    agendados = 0
    
    print(f"📊 Encontradas {total_cobrancas} cobranças pagas sem repasse")
    
    for cobranca in cobrancas_sem_repasse:
        try:
            print(f"\n🔄 Processando cobrança {cobranca.id}...")
            
            # Verificar se tem política ativa
            politica = _obter_politica_contrato(cobranca.contrato)
            
            if politica:
                repasse = _criar_repasse_seguro(cobranca)
                
                if repasse:
                    criados += 1
                    print(f"   ✅ Repasse {repasse.id} criado")
                else:
                    erros += 1
                    print(f"   ❌ Erro ao criar repasse")
            else:
                # Criar agendamento
                agendamento = _criar_agendamento_pendente(cobranca, "Política não configurada")
                if agendamento:
                    agendados += 1
                    print(f"   📋 Agendamento criado")
                else:
                    erros += 1
                    print(f"   ❌ Erro ao criar agendamento")
                    
        except Exception as e:
            erros += 1
            print(f"   ❌ Erro: {e}")
    
    print(f"\n📊 RESULTADO:")
    print(f"   ✅ Repasses criados: {criados}")
    print(f"   📋 Agendamentos criados: {agendados}")
    print(f"   ❌ Erros: {erros}")
    
    return {
        'total_processadas': total_cobrancas,
        'repasses_criados': criados,
        'agendamentos_criados': agendados,
        'erros': erros
    }


def verificar_configuracao():
    """
    🔍 Verifica se a configuração está correta
    """
    print("🔍 VERIFICANDO CONFIGURAÇÃO...")
    print("="*50)
    
    # Verificar modelos
    print(f"Cobranca disponível: {Cobranca is not None}")
    print(f"Repasse disponível: {Repasse is not None}")
    print(f"PoliticaRepasseContrato disponível: {PoliticaRepasseContrato is not None}")
    
    if Cobranca and Repasse:
        # Estatísticas
        total_cobrancas_pagas = Cobranca.objects.filter(status='paga').count()
        total_repasses = Repasse.objects.count()
        
        print(f"\n📊 ESTATÍSTICAS:")
        print(f"   Cobranças pagas: {total_cobrancas_pagas}")
        print(f"   Total repasses: {total_repasses}")
        
        if PoliticaRepasseContrato:
            politicas_ativas = PoliticaRepasseContrato.objects.filter(ativa=True).count()
            print(f"   Políticas ativas: {politicas_ativas}")
        
        # Cobranças sem repasse
        cobrancas_sem_repasse = Cobranca.objects.filter(
            status='paga'
        ).exclude(
            id__in=Repasse.objects.values_list('cobranca_id', flat=True)
        ).count()
        
        print(f"   Cobranças sem repasse: {cobrancas_sem_repasse}")
        
        if cobrancas_sem_repasse > 0:
            print(f"\n💡 Para processar as cobranças sem repasse, execute:")
            print(f"   from financeiro.signals import processar_cobrancas_pagas_sem_repasse")
            print(f"   resultado = processar_cobrancas_pagas_sem_repasse()")
    
    print(f"\n✅ Verificação concluída!")


# Executar verificação ao importar (apenas uma vez)
if __name__ != '__main__':
    try:
        # Fazer verificação silenciosa
        pass
    except:
        pass