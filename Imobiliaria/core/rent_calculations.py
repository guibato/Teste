from decimal import Decimal
from dateutil.relativedelta import relativedelta
from core.models import IndiceInflacao
from core.models import Contrato

from datetime import date

def calcular_aluguel_projetado(contrato):
    print("Contrato ID:", contrato.id)
    print("Valor Base (Aluguel/Pacote):", contrato.valor_aluguel, contrato.valor_pacote)
    print("Fator Reajuste:", contrato.fator_reajuste)
    print("Data Inicial:", contrato.data_inicio)
    print("Tipo de Pagamento:", contrato.tipo_pagamento)  # Adicionado para depuração
    
    hoje = date.today()
    max_data_final = contrato.data_inicio + relativedelta(months=+12)
    data_final = min(max_data_final, hoje)
    print("Data Final:", data_final)
    
    # Liste os índices encontrados para depuração
    indices = IndiceInflacao.objects.filter(
        tipo=contrato.fator_reajuste,
        data_referencia__gte=contrato.data_inicio.replace(day=1),
        data_referencia__lte=data_final.replace(day=1),
    ).order_by('data_referencia')
    print("Índices Encontrados:", indices.count())
    
    # Mostrar cada índice para depuração
    for indice in indices:
        print(f"Índice: {indice.tipo}, Data: {indice.data_referencia}, Valor: {indice.valor}")
    
    fator_acumulado = Decimal('1.0')
    for indice in indices:
        taxa = Decimal(str(indice.valor)) / 100
        fator_acumulado *= (1 + taxa)
        print(f"Aplicando índice {indice.valor}%, fator acumulado: {fator_acumulado}")
    
    print("Fator Acumulado Final:", fator_acumulado)
    
    # Corrigir a verificação para minúsculo conforme definido no modelo
    if contrato.tipo_pagamento == 'despesas_separadas':
        valor_base = contrato.valor_aluguel or Decimal('0.00')
    else:
        valor_base = contrato.valor_pacote or Decimal('0.00')
    print("Valor Base:", valor_base)
    
    aluguel_projetado = valor_base * fator_acumulado
    print("Aluguel Projetado:", aluguel_projetado)
    return aluguel_projetado.quantize(Decimal('0.01'))