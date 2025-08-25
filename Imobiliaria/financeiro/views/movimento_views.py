# financeiro/views/movimento_views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count, Max, Min  # ← CORREÇÃO: Adicionei Max e Min
from django.db import transaction
from django.utils import timezone
from django.urls import reverse  # ← CORREÇÃO: Adicionei reverse
from datetime import datetime, date, timedelta
from django.views.decorators.http import require_http_methods
from decimal import Decimal
import csv

from financeiro.models.movimento import MovimentoConta, SaldoProprietario
from cadastro.models import Cliente, Contrato
from financeiro.forms.movimento_forms import (
    MovimentoManualForm, AjusteSaldoForm, FiltroMovimentoForm, 
    ImportacaoExtratoForm, ConciliacaoForm
)



def extrato_proprietario(request, proprietario_id):
    """Extrato detalhado de movimentações de um proprietário"""
    proprietario = get_object_or_404(Cliente, pk=proprietario_id, tipo='proprietario')
    
    # Buscar ou criar saldo
    saldo_obj, created = SaldoProprietario.objects.get_or_create(
        proprietario=proprietario,
        defaults={'saldo_atual': Decimal('0.00')}
    )
    
    # Filtros
    form_filtro = FiltroMovimentoForm(request.GET)
    movimentos = MovimentoConta.objects.filter(proprietario=proprietario)
    
    if form_filtro.is_valid():
        data_inicio = form_filtro.cleaned_data.get('data_inicio')
        data_fim = form_filtro.cleaned_data.get('data_fim')
        tipo = form_filtro.cleaned_data.get('tipo')
        contrato = form_filtro.cleaned_data.get('contrato')
        search = form_filtro.cleaned_data.get('search')
        
        if data_inicio:
            movimentos = movimentos.filter(data__gte=data_inicio)
        if data_fim:
            movimentos = movimentos.filter(data__lte=data_fim)
        if tipo:
            movimentos = movimentos.filter(tipo=tipo)
        if contrato:
            movimentos = movimentos.filter(contrato=contrato)
        if search:
            movimentos = movimentos.filter(
                Q(descricao__icontains=search) |
                Q(contrato__imovel__endereco__icontains=search)
            )
    
    movimentos = movimentos.select_related('contrato').order_by('-data', '-id')
    
    # Paginação
    paginator = Paginator(movimentos, 20)
    page_number = request.GET.get('page')
    movimentos_page = paginator.get_page(page_number)
    
    # Calcular saldo progressivo para os movimentos da página
    # Para isso, precisamos do saldo inicial da página
    if movimentos_page.has_previous():
        # Saldo até o movimento anterior à página
        movimentos_anteriores = MovimentoConta.objects.filter(
            proprietario=proprietario,
            id__gt=movimentos_page.object_list.last().id if movimentos_page.object_list else 0
        )
        saldo_inicial_pagina = saldo_obj.saldo_atual
        for mov in movimentos_anteriores:
            if mov.tipo == 'credito':
                saldo_inicial_pagina -= mov.valor
            else:
                saldo_inicial_pagina += mov.valor
    else:
        saldo_inicial_pagina = saldo_obj.saldo_atual
        for mov in movimentos[:movimentos_page.start_index()-1]:
            if mov.tipo == 'credito':
                saldo_inicial_pagina -= mov.valor
            else:
                saldo_inicial_pagina += mov.valor
    
    # Adicionar saldo progressivo a cada movimento
    saldo_atual_temp = saldo_inicial_pagina
    for movimento in reversed(movimentos_page.object_list):
        if movimento.tipo == 'credito':
            saldo_atual_temp += movimento.valor
        else:
            saldo_atual_temp -= movimento.valor
        movimento.saldo_apos = saldo_atual_temp
    
    # Estatísticas do período
    stats = {}
    if form_filtro.is_valid():
        movimentos_stats = MovimentoConta.objects.filter(proprietario=proprietario)
        if data_inicio:
            movimentos_stats = movimentos_stats.filter(data__gte=data_inicio)
        if data_fim:
            movimentos_stats = movimentos_stats.filter(data__lte=data_fim)
        
        stats = {
            'total_creditos': movimentos_stats.filter(tipo='credito').aggregate(
                total=Sum('valor'))['total'] or Decimal('0.00'),
            'total_debitos': movimentos_stats.filter(tipo='debito').aggregate(
                total=Sum('valor'))['total'] or Decimal('0.00'),
            'total_repasses': movimentos_stats.filter(tipo='repasse').aggregate(
                total=Sum('valor'))['total'] or Decimal('0.00'),
            'quantidade_movimentos': movimentos_stats.count(),
        }
        stats['saldo_periodo'] = stats['total_creditos'] - stats['total_debitos'] - stats['total_repasses']
    
    context = {
        'proprietario': proprietario,
        'saldo_obj': saldo_obj,
        'movimentos': movimentos_page,
        'form_filtro': form_filtro,
        'stats': stats,
    }
    
    return render(request, 'financeiro/movimentos/extrato.html', context)



def lista_saldos(request):
    """Lista de saldos de todos os proprietários"""
    saldos = SaldoProprietario.objects.select_related('proprietario').all()
    
    # Filtros
    search = request.GET.get('search', '')
    saldo_minimo = request.GET.get('saldo_minimo', '')
    saldo_maximo = request.GET.get('saldo_maximo', '')
    
    if search:
        saldos = saldos.filter(proprietario__nome__icontains=search)
    
    if saldo_minimo:
        try:
            saldos = saldos.filter(saldo_atual__gte=Decimal(saldo_minimo))
        except:
            pass
    
    if saldo_maximo:
        try:
            saldos = saldos.filter(saldo_atual__lte=Decimal(saldo_maximo))
        except:
            pass
    
    saldos = saldos.order_by('-saldo_atual')
    
    # Paginação
    paginator = Paginator(saldos, 20)
    page_number = request.GET.get('page')
    saldos_page = paginator.get_page(page_number)
    
    # Estatísticas
    stats = {
        'total_proprietarios': saldos.count(),
        'saldo_total': saldos.aggregate(total=Sum('saldo_atual'))['total'] or Decimal('0.00'),
        'saldos_positivos': saldos.filter(saldo_atual__gt=0).count(),
        'saldos_negativos': saldos.filter(saldo_atual__lt=0).count(),
        'maior_saldo': saldos.aggregate(maior=Max('saldo_atual'))['maior'] or Decimal('0.00'),
        'menor_saldo': saldos.aggregate(menor=Min('saldo_atual'))['menor'] or Decimal('0.00'),
    }
    
    context = {
        'saldos': saldos_page,
        'stats': stats,
        'filtros': {
            'search': search,
            'saldo_minimo': saldo_minimo,
            'saldo_maximo': saldo_maximo,
        }
    }
    
    return render(request, 'financeiro/movimentos/lista_saldos.html', context)



def lancamento_manual(request, proprietario_id):
    """Lançamento manual de movimento"""
    proprietario = get_object_or_404(Cliente, pk=proprietario_id, tipo='proprietario')
    
    if request.method == 'POST':
        form = MovimentoManualForm(request.POST, proprietario=proprietario)
        if form.is_valid():
            try:
                with transaction.atomic():
                    tipo = form.cleaned_data['tipo']
                    valor = form.cleaned_data['valor']
                    descricao = form.cleaned_data['descricao']
                    contrato = form.cleaned_data.get('contrato')
                    data_referencia = form.cleaned_data.get('data_referencia')
                    
                    # Buscar ou criar saldo
                    saldo_obj, created = SaldoProprietario.objects.get_or_create(
                        proprietario=proprietario,
                        defaults={'saldo_atual': Decimal('0.00')}
                    )
                    
                    # Realizar lançamento
                    if tipo == 'credito':
                        saldo_obj.adicionar_credito(
                            valor=valor,
                            descricao=descricao,
                            contrato=contrato,
                            data_referencia=data_referencia
                        )
                    elif tipo == 'debito':
                        permitir_negativo = form.cleaned_data.get('permitir_negativo', False)
                        saldo_obj.debitar(
                            valor=valor,
                            descricao=descricao,
                            contrato=contrato,
                            data_referencia=data_referencia,
                            permitir_negativo=permitir_negativo
                        )
                    elif tipo == 'repasse':
                        saldo_obj.registrar_repasse(
                            valor=valor,
                            descricao=descricao,
                            contrato=contrato,
                            data_referencia=data_referencia
                        )
                    
                    messages.success(request, 'Lançamento realizado com sucesso!')
                    return redirect('financeiro:extrato_proprietario', proprietario_id=proprietario.pk)
                    
            except ValueError as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f'Erro ao realizar lançamento: {str(e)}')
    else:
        form = MovimentoManualForm(proprietario=proprietario)
    
    context = {
        'proprietario': proprietario,
        'form': form,
    }
    
    return render(request, 'financeiro/movimentos/lancamento_manual.html', context)



def ajuste_saldo(request, proprietario_id):
    """Ajuste de saldo (para correções)"""
    proprietario = get_object_or_404(Cliente, pk=proprietario_id, tipo='proprietario')
    saldo_obj, created = SaldoProprietario.objects.get_or_create(
        proprietario=proprietario,
        defaults={'saldo_atual': Decimal('0.00')}
    )
    
    if request.method == 'POST':
        form = AjusteSaldoForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    novo_saldo = form.cleaned_data['novo_saldo']
                    motivo = form.cleaned_data['motivo']
                    
                    saldo_anterior = saldo_obj.saldo_atual
                    diferenca = novo_saldo - saldo_anterior
                    
                    # Criar movimento de ajuste
                    if diferenca != 0:
                        tipo_movimento = 'credito' if diferenca > 0 else 'debito'
                        valor_movimento = abs(diferenca)
                        
                        MovimentoConta.objects.create(
                            proprietario=proprietario,
                            tipo=tipo_movimento,
                            descricao=f"Ajuste de saldo: {motivo}",
                            valor=valor_movimento,
                            origem_simplificada=True
                        )
                        
                        # Atualizar saldo
                        saldo_obj.saldo_atual = novo_saldo
                        saldo_obj.save()
                    
                    messages.success(
                        request, 
                        f'Saldo ajustado de R$ {saldo_anterior:.2f} para R$ {novo_saldo:.2f}'
                    )
                    return redirect('financeiro:extrato_proprietario', proprietario_id=proprietario.pk)
                    
            except Exception as e:
                messages.error(request, f'Erro ao ajustar saldo: {str(e)}')
    else:
        form = AjusteSaldoForm(initial={'novo_saldo': saldo_obj.saldo_atual})
    
    context = {
        'proprietario': proprietario,
        'saldo_obj': saldo_obj,
        'form': form,
    }
    
    return render(request, 'financeiro/movimentos/ajuste_saldo.html', context)



def dashboard_financeiro(request):
    """Dashboard financeiro geral"""
    # Estatísticas gerais
    hoje = timezone.now().date()
    inicio_mes = hoje.replace(day=1)
    inicio_ano = hoje.replace(month=1, day=1)
    
    # Movimentações do mês
    movimentos_mes = MovimentoConta.objects.filter(data__gte=inicio_mes)
    creditos_mes = movimentos_mes.filter(tipo='credito').aggregate(
        total=Sum('valor'))['total'] or Decimal('0.00')
    debitos_mes = movimentos_mes.filter(tipo='debito').aggregate(
        total=Sum('valor'))['total'] or Decimal('0.00')
    repasses_mes = movimentos_mes.filter(tipo='repasse').aggregate(
        total=Sum('valor'))['total'] or Decimal('0.00')
    
    # Saldos
    saldos = SaldoProprietario.objects.all()
    saldo_total = saldos.aggregate(total=Sum('saldo_atual'))['total'] or Decimal('0.00')
    proprietarios_positivos = saldos.filter(saldo_atual__gt=0).count()
    proprietarios_negativos = saldos.filter(saldo_atual__lt=0).count()
    
    # Movimentações recentes
    movimentos_recentes = MovimentoConta.objects.select_related(
        'proprietario', 'contrato'
    ).order_by('-data', '-id')[:10]
    
    # Proprietários com maior saldo
    maiores_saldos = saldos.select_related('proprietario').order_by('-saldo_atual')[:5]
    
    # Alertas
    alertas = []
    
    # Saldos negativos
    saldos_negativos = saldos.filter(saldo_atual__lt=0).select_related('proprietario')
    if saldos_negativos.exists():
        alertas.append({
            'tipo': 'warning',
            'titulo': 'Saldos Negativos',
            'mensagem': f'{saldos_negativos.count()} proprietário(s) com saldo negativo',
            'link': reverse('financeiro:lista_saldos') + '?saldo_maximo=0'
        })
    
    # Movimentações hoje
    movimentos_hoje = MovimentoConta.objects.filter(data=hoje).count()
    if movimentos_hoje > 20:  # Limite arbitrário
        alertas.append({
            'tipo': 'info',
            'titulo': 'Alta Movimentação',
            'mensagem': f'{movimentos_hoje} movimentações registradas hoje',
            'link': None
        })
    
    context = {
        'stats': {
            'creditos_mes': creditos_mes,
            'debitos_mes': debitos_mes,
            'repasses_mes': repasses_mes,
            'saldo_liquido_mes': creditos_mes - debitos_mes - repasses_mes,
            'saldo_total': saldo_total,
            'proprietarios_positivos': proprietarios_positivos,
            'proprietarios_negativos': proprietarios_negativos,
            'total_proprietarios': saldos.count(),
        },
        'movimentos_recentes': movimentos_recentes,
        'maiores_saldos': maiores_saldos,
        'alertas': alertas,
    }
    
    return render(request, 'financeiro/movimentos/dashboard.html', context)



def exportar_extrato(request, proprietario_id):
    """Exportar extrato em CSV"""
    proprietario = get_object_or_404(Cliente, pk=proprietario_id, tipo='proprietario')
    
    # Aplicar mesmos filtros da listagem
    form_filtro = FiltroMovimentoForm(request.GET)
    movimentos = MovimentoConta.objects.filter(proprietario=proprietario)
    
    if form_filtro.is_valid():
        data_inicio = form_filtro.cleaned_data.get('data_inicio')
        data_fim = form_filtro.cleaned_data.get('data_fim')
        tipo = form_filtro.cleaned_data.get('tipo')
        contrato = form_filtro.cleaned_data.get('contrato')
        
        if data_inicio:
            movimentos = movimentos.filter(data__gte=data_inicio)
        if data_fim:
            movimentos = movimentos.filter(data__lte=data_fim)
        if tipo:
            movimentos = movimentos.filter(tipo=tipo)
        if contrato:
            movimentos = movimentos.filter(contrato=contrato)
    
    movimentos = movimentos.select_related('contrato').order_by('-data', '-id')
    
    # Criar resposta CSV
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="extrato_{proprietario.nome}_{hoje.strftime("%Y%m%d")}.csv"'
    response.write('\ufeff'.encode('utf8'))  # BOM para Excel
    
    writer = csv.writer(response)
    writer.writerow([
        'Data', 'Tipo', 'Descrição', 'Contrato', 'Valor', 'Data Referência'
    ])
    
    for movimento in movimentos:
        writer.writerow([
            movimento.data.strftime('%d/%m/%Y'),
            movimento.get_tipo_display(),
            movimento.descricao,
            str(movimento.contrato) if movimento.contrato else '',
            str(movimento.valor).replace('.', ','),
            movimento.data_referencia.strftime('%d/%m/%Y') if movimento.data_referencia else '',
        ])
    
    return response



def conciliacao_bancaria(request, proprietario_id):
    """Conciliação bancária"""
    proprietario = get_object_or_404(Cliente, pk=proprietario_id, tipo='proprietario')
    saldo_obj, created = SaldoProprietario.objects.get_or_create(
        proprietario=proprietario,
        defaults={'saldo_atual': Decimal('0.00')}
    )
    
    if request.method == 'POST':
        form = ConciliacaoForm(request.POST, request.FILES)
        if form.is_valid():
            # Processar conciliação bancária
            # Implementar lógica de conciliação
            messages.success(request, 'Conciliação processada com sucesso!')
            return redirect('financeiro:extrato_proprietario', proprietario_id=proprietario.pk)
    else:
        form = ConciliacaoForm()
    
    context = {
        'proprietario': proprietario,
        'saldo_obj': saldo_obj,
        'form': form,
    }
    
    return render(request, 'financeiro/movimentos/conciliacao.html', context)



@require_http_methods(["GET"])
def contratos_proprietario_api(request, proprietario_id):
    """API para buscar contratos de um proprietário (para AJAX)"""
    proprietario = get_object_or_404(Cliente, pk=proprietario_id, tipo='proprietario')
    term = request.GET.get('term', '')
    
    contratos = Contrato.objects.filter(proprietario=proprietario, status='ativo')
    
    if term:
        contratos = contratos.filter(
            Q(imovel__endereco__icontains=term) |
            Q(inquilino__nome__icontains=term)
        )
    
    contratos = contratos[:10]  # Limitar resultados
    
    results = []
    for contrato in contratos:
        results.append({
            'id': contrato.pk,
            'text': f"{contrato.imovel.endereco} - {contrato.inquilino.nome}",
        })
    
    return JsonResponse({'results': results})