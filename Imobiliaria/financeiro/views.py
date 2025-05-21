# financeiro/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponse
from django.db.models import Sum
from decimal import Decimal
from .models import Cobranca, LembreteEnviado, MovimentoConta, Repasse, Despesa
from .forms import CobrancaForm, DespesaForm
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from sisimob.models import Contrato
from datetime import date
from decimal import Decimal

@require_http_methods(["GET", "POST"])
def gerar_cobrancas(request):
    contratos = Contrato.objects.all()
    meses = [(i, date(2000, i, 1).strftime('%B').capitalize()) for i in range(1, 13)]
    ano_atual = timezone.now().year
    mes_atual = timezone.now().month

    mes = int(request.GET.get('mes', mes_atual))
    ano = int(request.GET.get('ano', ano_atual))
    contrato_id = request.GET.get('contrato')
    contrato_selecionado = int(contrato_id) if contrato_id and contrato_id.isdigit() else None

    cobrancas_sugeridas = []

    if request.method == 'GET' and mes and ano:
        contratos_filtrados = contratos
        if contrato_selecionado:
            contratos_filtrados = contratos.filter(pk=contrato_selecionado)

        for contrato in contratos_filtrados:
            if not Cobranca.objects.filter(contrato=contrato, mes_referencia=mes, ano_referencia=ano).exists():
                valor_aluguel = contrato.valor_aluguel  # Supondo que você tem esse método no modelo Contrato
                cobranca = Cobranca(
                    contrato=contrato,
                    inquilino=contrato.inquilino.first(),
                    mes_referencia=mes,
                    ano_referencia=ano,
                    valor_aluguel=valor_aluguel,
                    valor_total=valor_aluguel,  # despesas serão somadas depois
                    data_vencimento=contrato.get_data_vencimento(mes, ano),  # precisa existir
                    descricao=f"Cobrança {mes}/{ano}"
                )
                cobranca.valor_total = cobranca.calcular_valor_total()
                cobrancas_sugeridas.append(cobranca)

    if request.method == 'POST':
        ids = request.POST.getlist('cobrancas')
        contratos_selecionados = contratos
        if contrato_selecionado:
            contratos_selecionados = contratos.filter(pk=contrato_selecionado)

        criadas = 0
        for contrato in contratos_selecionados:
            if not Cobranca.objects.filter(contrato=contrato, mes_referencia=mes, ano_referencia=ano).exists():
                valor_aluguel = contrato.valor_aluguel_atual()
                cobranca = Cobranca.objects.create(
                    contrato=contrato,
                    inquilino=inquilino,
                    mes_referencia=mes,
                    ano_referencia=ano,
                    valor_aluguel=valor_aluguel,
                    valor_total=valor_aluguel,  # despesas somadas abaixo
                    data_vencimento=contrato.get_data_vencimento(mes, ano),
                    descricao=f"Cobrança {mes}/{ano}"
                )
                cobranca.atualizar_valor_total()
                cobranca.gerar_cobranca_gateway()  # integra com o Asaas
                criadas += 1

        messages.success(request, f"{criadas} cobranças geradas com sucesso.")
        return redirect('listar_cobrancas')

    context = {
        'meses': meses,
        'mes': mes,
        'ano': ano,
        'ano_atual': ano_atual,
        'mes_atual': mes_atual,
        'contratos': contratos,
        'contrato_selecionado': contrato_selecionado,
        'cobrancas_sugeridas': cobrancas_sugeridas
    }
    return render(request, 'financeiro/gerar_cobrancas.html', context)


# ==== UTILITÁRIOS ====
def format_currency(valor):
    return f"R$ {valor:.2f}".replace('.', ',')


# ==== VISÕES DE COBRANÇAS ====
def listar_cobrancas(request):
    cobrancas = Cobranca.objects.select_related('contrato', 'inquilino').order_by('-data_vencimento')
    return render(request, 'financeiro/listar_cobrancas.html', {'cobrancas': cobrancas})


def detalhe_cobranca(request, pk):
    cobranca = get_object_or_404(Cobranca, pk=pk)
    lembretes = cobranca.lembretes_enviados.order_by('-data_envio')
    return render(request, 'financeiro/detalhe_cobranca.html', {
        'cobranca': cobranca,
        'lembretes': lembretes,
    })


def criar_cobranca(request):
    if request.method == 'POST':
        form = CobrancaForm(request.POST)
        if form.is_valid():
            cobranca = form.save(commit=False)
            cobranca.valor_total = cobranca.calcular_valor_total()
            cobranca.save()
            messages.success(request, 'Cobrança criada com sucesso.')
            return redirect('listar_cobrancas')
    else:
        form = CobrancaForm()
    return render(request, 'financeiro/form_cobranca.html', {'form': form})


def editar_cobranca(request, pk):
    cobranca = get_object_or_404(Cobranca, pk=pk)
    if request.method == 'POST':
        form = CobrancaForm(request.POST, instance=cobranca)
        if form.is_valid():
            cobranca = form.save(commit=False)
            cobranca.valor_total = cobranca.calcular_valor_total()
            cobranca.save()
            messages.success(request, 'Cobrança atualizada.')
            return redirect('listar_cobrancas')
    else:
        form = CobrancaForm(instance=cobranca)
    return render(request, 'financeiro/form_cobranca.html', {'form': form, 'cobranca': cobranca})


def excluir_cobranca(request, pk):
    cobranca = get_object_or_404(Cobranca, pk=pk)
    if request.method == 'POST':
        cobranca.delete()
        messages.success(request, 'Cobrança excluída com sucesso.')
        return redirect('listar_cobrancas')
    return render(request, 'financeiro/confirmar_exclusao.html', {'obj': cobranca})


def registrar_pagamento(request, pk):
    cobranca = get_object_or_404(Cobranca, pk=pk)
    cobranca.marcar_como_paga()
    messages.success(request, 'Cobrança marcada como paga.')
    return redirect('detalhe_cobranca', pk=cobranca.pk)


def gerar_recibo_pagamento(request, pk):
    cobranca = get_object_or_404(Cobranca, pk=pk)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="recibo_pagamento.pdf"'
    # Aqui você chamaria a função geradora do PDF (ex: gerar_recibo_pdf(cobranca, response))
    response.write(b"Recibo em PDF gerado aqui")  # Placeholder
    return response


# ==== LEMBRETES ====
def lembretes_enviados_por_cobranca(request, pk):
    cobranca = get_object_or_404(Cobranca, pk=pk)
    lembretes = cobranca.lembretes_enviados.order_by('-data_envio')
    return render(request, 'financeiro/lembretes_por_cobranca.html', {
        'cobranca': cobranca,
        'lembretes': lembretes,
    })


# ==== DASHBOARD FINANCEIRO (opcional) ====
def dashboard_financeiro(request):
    hoje = timezone.now().date()
    total_recebido = Cobranca.objects.filter(status='paga').aggregate(total=Sum('valor_total'))['total'] or Decimal('0.00')
    total_pendente = Cobranca.objects.filter(status='pendente').aggregate(total=Sum('valor_total'))['total'] or Decimal('0.00')
    total_repassado = Repasse.objects.filter(status='efetuado').aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
    return render(request, 'financeiro/dashboard.html', {
        'total_recebido': format_currency(total_recebido),
        'total_pendente': format_currency(total_pendente),
        'total_repassado': format_currency(total_repassado),
    })

def cadastrar_despesa(request, contrato_id=None):
    contrato = None
    if contrato_id:
        contrato = get_object_or_404(Contrato, id=contrato_id)

    if request.method == 'POST':
        form = DespesaForm(request.POST, request.FILES)
        if form.is_valid():
            despesa = form.save()
            messages.success(request, 'Despesa cadastrada com sucesso.')
            return redirect('listar_cobrancas')  # Ou outro destino apropriado
    else:
        form = DespesaForm(initial={'contrato': contrato})

    return render(request, 'financeiro/form_despesa.html', {
        'form': form,
        'titulo': 'Lançar Nova Despesa',
        'contrato': contrato  # <- ESSENCIAL PARA O TEMPLATE FUNCIONAR
    })


def listar_despesas(request):
    despesas = Despesa.objects.select_related('contrato', 'tipo').order_by('-data_inicio')
    return render(request, 'financeiro/listar_despesas.html', {'despesas': despesas})


def editar_despesa(request, pk):
    despesa = get_object_or_404(Despesa, pk=pk)
    if request.method == 'POST':
        form = DespesaForm(request.POST, request.FILES, instance=despesa)
        if form.is_valid():
            form.save()
            messages.success(request, "Despesa atualizada com sucesso.")
            return redirect('listar_despesas')
    else:
        form = DespesaForm(instance=despesa)
    return render(request, 'financeiro/form_despesa.html', {
        'form': form,
        'titulo': f'Editar Despesa #{despesa.pk}'
    })


def excluir_despesa(request, pk):
    despesa = get_object_or_404(Despesa, pk=pk)
    if request.method == 'POST':
        despesa.delete()
        messages.success(request, 'Despesa excluída com sucesso.')
        return redirect('listar_despesas')
    return render(request, 'financeiro/confirmar_exclusao.html', {
        'objeto': despesa,
        'titulo': 'Confirmar Exclusão de Despesa'
    })

