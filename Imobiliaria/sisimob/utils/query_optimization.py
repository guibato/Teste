from django.db import models
from django.db.models import Prefetch, Count, Sum, F, Q
from django.core.paginator import Paginator

def otimizar_consultas_exemplo():
    """
    Exemplos de otimização de consultas usando select_related e prefetch_related.

    Este é um arquivo de referência para demonstrar como otimizar consultas
    ao banco de dados no projeto de administração imobiliária.
    """

    # Exemplo 1: Carregando contratos com proprietários e inquilinos em uma única consulta
    # Antes (gera N+1 consultas):
    contratos = Contrato.objects.all()
    for contrato in contratos:
        proprietario = contrato.proprietario  # Consulta adicional
        inquilino = contrato.inquilino  # Consulta adicional

    # Depois (uma única consulta):
    contratos = Contrato.objects.select_related('proprietario', 'inquilino', 'imovel').all()
    for contrato in contratos:
        proprietario = contrato.proprietario  # Já carregado
        inquilino = contrato.inquilino  # Já carregado

    # Exemplo 2: Carregando contratos com suas cobranças em uma única consulta
    # Antes (gera N+1 consultas):
    contratos = Contrato.objects.all()
    for contrato in contratos:
        cobrancas = contrato.cobrancas.all()  # Consulta adicional

    # Depois (duas consultas no total):
    contratos = Contrato.objects.prefetch_related('cobrancas').all()
    for contrato in contratos:
        cobrancas = contrato.cobrancas.all()  # Já carregado

    # Exemplo 3: Filtragem eficiente
    # Antes:
    contratos = Contrato.objects.all()
    contratos_ativos = [c for c in contratos if c.ativo]

    # Depois:
    contratos_ativos = Contrato.objects.filter(ativo=True)

    # Exemplo 4: Agregações no banco de dados
    # Antes:
    contratos = Contrato.objects.all()
    total = 0
    for contrato in contratos:
        total += contrato.valor_aluguel

    # Depois:
    total = Contrato.objects.aggregate(total=Sum('valor_aluguel'))['total'] or 0

    # Exemplo 5: Paginação para grandes conjuntos de dados
    contratos = Contrato.objects.all()
    paginator = Paginator(contratos, 20)  # 20 itens por página
    page = paginator.page(1)

    # Exemplo 6: Consultas complexas com anotações
    contratos_com_estatisticas = Contrato.objects.annotate(
        num_cobrancas=Count('cobrancas'),
        total_recebido=Sum('cobrancas__valor', filter=Q(cobrancas__status='paga'))
    )

    # Exemplo 7: Usando valores calculados
    contratos_com_lucro = Contrato.objects.annotate(
        lucro=F('valor_aluguel') - F('valor_taxa_administracao_fixo')
    ).filter(lucro__gt=0)

    # Exemplo 8: Prefetch com filtros específicos
    contratos = Contrato.objects.prefetch_related(
        Prefetch('cobrancas', queryset=Cobranca.objects.filter(status='paga'))
    )

    return "Exemplos de otimização de consultas"
