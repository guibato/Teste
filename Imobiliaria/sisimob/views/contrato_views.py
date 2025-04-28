from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.generic import ListView
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Sum, Prefetch
from django.utils import timezone
from decimal import Decimal
from datetime import date
from ..forms import ContratoForm, DespesaForm
from ..models import Contrato, Cobranca, Despesa
from ..rent_calculations import calcular_aluguel_projetado # Assuming this function exists
from ..utils.pdf_utils import format_currency # Assuming this utility exists
from django.http import HttpResponse
# Import necessary PDF generation utilities (replace with actual imports)
# from ..utils.pdf_generator import gerar_pdf_contrato, gerar_pdf_extrato_rendimento

class ListarContratosView(ListView):
    """
    View para listar todos os contratos com paginação.
    Otimizada com select_related para reduzir consultas.
    """
    model = Contrato
    template_name = 'contratos/listar_contratos.html' # Specify template name
    context_object_name = 'contratos' # Specify context object name
    paginate_by = 10
    # Optimize query by fetching related objects in the same query
    queryset = Contrato.objects.select_related('proprietario', 'inquilino', 'imovel').all().order_by('-data_inicio')

def cadastrar_contrato(request):
    """
    View para cadastrar um novo contrato.
    """
    if request.method == 'POST':
        form = ContratoForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Contrato cadastrado com sucesso!")
            return redirect('listar_contratos')
        else:
            messages.error(request, "Por favor, corrija os erros no formulário.")
    else:
        form = ContratoForm()
    return render(request, 'contratos/cadastro_contrato.html', {'form': form, 'titulo': 'Cadastro de Contrato', 'botao_acao': 'Cadastrar'})

def editar_contrato(request, contrato_id):
    """
    View para editar um contrato existente.
    """
    contrato = get_object_or_404(Contrato, id=contrato_id)
    if request.method == 'POST':
        form = ContratoForm(request.POST, request.FILES, instance=contrato)
        if form.is_valid():
            form.save()
            messages.success(request, "Contrato atualizado com sucesso!")
            return redirect('listar_contratos')
        else:
            messages.error(request, "Por favor, corrija os erros no formulário.")
    else:
        form = ContratoForm(instance=contrato)
    return render(request, 'contratos/cadastro_contrato.html', {
        'form': form,
        'contrato': contrato,
        'titulo': 'Editar Contrato',
        'botao_acao': 'Salvar'
    })

def dashboard(request, id):
    """
    View para exibir o dashboard de um contrato específico.
    Otimizada com select_related e prefetch_related.
    """
    # Optimize fetching related objects
    contrato = get_object_or_404(
        Contrato.objects.select_related('proprietario', 'inquilino', 'imovel')
                      .prefetch_related(
                          Prefetch('cobrancas', queryset=Cobranca.objects.order_by('ano_referencia', 'mes_referencia')),
                          Prefetch('despesas', queryset=Despesa.objects.order_by('data_inicio'))
                      ),
        id=id
    )

    aluguel_projetado = contrato.calcular_aluguel_projetado()

    ano_filtro = request.GET.get('ano', str(date.today().year))
    status_filtro = request.GET.get('status', '')

    # Use prefetched cobrancas
    cobrancas_qs = contrato.cobrancas.all() # Already ordered by prefetch

    if ano_filtro:
        try:
            cobrancas_qs = cobrancas_qs.filter(ano_referencia=int(ano_filtro))
        except ValueError:
            pass # Ignore invalid year filter
    if status_filtro:
        cobrancas_qs = cobrancas_qs.filter(status=status_filtro)

    # Use prefetched despesas
    despesas_qs = contrato.despesas.all() # Already ordered by prefetch
    despesa_form = DespesaForm()

    # Optimize aggregation using the prefetched queryset
    total_receitas = cobrancas_qs.filter(status='paga').aggregate(
        total=Sum('valor')
    )['total'] or Decimal('0.00')

    # Calculate total expenses based on paid invoices and admin fees
    total_despesas_calc = Decimal('0.00')
    for cobranca in cobrancas_qs.filter(status='paga'):
        # Assuming valor_repasse correctly calculates the net amount after admin fees
        # If not, adjust the calculation here
        total_despesas_calc += cobranca.valor_repasse

    saldo = total_receitas - total_despesas_calc

    # Optimize distinct years query
    anos_disponiveis = Cobranca.objects.filter(contrato=contrato).dates('data_vencimento', 'year').distinct()

    context = {
        'contrato': contrato,
        'aluguel_projetado': format_currency(aluguel_projetado),
        'cobrancas': cobrancas_qs, # Pass the filtered queryset
        'despesas': despesas_qs, # Pass the prefetched queryset
        'despesa_form': despesa_form,
        'total_receitas': format_currency(total_receitas),
        'total_despesas': format_currency(total_despesas_calc), # Use calculated expenses
        'saldo': format_currency(saldo),
        'saldo_positivo': saldo >= 0,
        'contrato_valor_caucao': format_currency(contrato.valor_caucao or 0),
        'contrato_valor_aluguel': format_currency(contrato.valor_aluguel or 0),
        'contrato_valor_taxa_administracao_fixo	': format_currency(contrato.valor_taxa_administracao_fixo or 0),
        'contrato_valor_taxa_administracao_percentual': contrato.valor_taxa_administracao_percentual or 0, # Keep as percentage
        'ano_selecionado': ano_filtro,
        'status_selecionado': status_filtro,
        'anos_disponiveis': anos_disponiveis,
    }

    return render(request, 'contratos/dashboard.html', context)

def gerar_pdf(request, contrato_id):
    """
    View para gerar o PDF do contrato.
    (Placeholder - requires actual PDF generation logic)
    """
    contrato = get_object_or_404(Contrato, id=contrato_id)
    # response = gerar_pdf_contrato(contrato)
    # return response
    messages.info(request, "Funcionalidade de gerar PDF do contrato ainda não implementada.")
    return redirect('dashboard', id=contrato_id)

def gerar_extrato_rendimento(request, contrato_id):
    """
    View para gerar o PDF do extrato de rendimento.
    (Placeholder - requires actual PDF generation logic)
    """
    contrato = get_object_or_404(Contrato, id=contrato_id)
    # response = gerar_pdf_extrato_rendimento(contrato)
    # return response
    messages.info(request, "Funcionalidade de gerar extrato de rendimento ainda não implementada.")
    return redirect('dashboard', id=contrato_id)
