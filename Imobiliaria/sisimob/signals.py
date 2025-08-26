from django.dispatch import Signal

# Disparado quando um contrato é assinado/cadastrado
contrato_assinado = Signal()

# Disparado para solicitar envio de cobranças ao Asaas
enviar_cobrancas_asaas = Signal()