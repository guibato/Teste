# financeiro/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models.cobranca import Cobranca
from .models.repasse import Repasse
from .services.repasse_service import RepasseService
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Cobranca)
def criar_repasse_automatico(sender, instance, created, **kwargs):
    """
    Cria repasse automaticamente quando cobrança é marcada como paga
    """
    # Só processar se a cobrança foi marcada como paga
    if instance.status != 'paga':
        return
    
    # Verificar se já existe repasse para esta cobrança
    if Repasse.objects.filter(cobranca=instance).exists():
        return
    
    try:
        # Buscar política ativa para o contrato/proprietário
        from .models.repasse import PoliticaRepasse
        politica = PoliticaRepasse.objects.filter(ativa=True).first()
        
        if not politica:
            logger.warning(f"Nenhuma política ativa encontrada para criar repasse da cobrança {instance.id}")
            return
        
        # Calcular valores do repasse
        service = RepasseService()
        valor_base, detalhes = service.calcular_valor_repasse(instance, politica)
        
        if valor_base <= 0:
            logger.warning(f"Valor de repasse inválido para cobrança {instance.id}: {detalhes}")
            return
        
        # Calcular data prevista baseada na política
        data_prevista = politica.calcular_proxima_data_repasse()
        if not data_prevista:
            data_prevista = instance.data_pagamento + timedelta(days=politica.dias_apos_recebimento)
        
        # Criar repasse
        repasse = Repasse.objects.create(
            proprietario=instance.contrato.proprietario,
            cobranca=instance,
            contrato=instance.contrato,
            valor=valor_base,
            valor_desconto=detalhes.get('valor_desconto', 0),
            valor_taxa_admin=detalhes.get('valor_taxa_admin', 0),
            data_prevista=data_prevista,
            mes_referencia=instance.mes_referencia,
            ano_referencia=instance.ano_referencia,
            tipo='automatico',
            status='pendente',
            descricao=f"Repasse automático referente à cobrança #{instance.id}"
        )
        
        logger.info(f"Repasse {repasse.id} criado automaticamente para cobrança {instance.id}")
        
    except Exception as e:
        logger.error(f"Erro ao criar repasse automático para cobrança {instance.id}: {str(e)}")


# Não esquecer de registrar os signals no apps.py
# financeiro/apps.py
from django.apps import AppConfig

class FinanceiroConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'financeiro'
    
    def ready(self):
        import financeiro.signals  # Importa os signals