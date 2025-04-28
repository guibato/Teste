from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.db.models import Sum, Prefetch, Q
from datetime import date, datetime
from decimal import Decimal
import threading

from ..forms import CobrancaForm, GerarCobrancasForm
from ..models import Cobranca, Contrato
from ..utils.asaas_service import AsaasService

def lista_cobrancas(request):
    """
    View para listar todas as cobranças com paginação e filtros.
    Otimizada com select_related para reduzir consultas.
    """
    query = request.GET.get('q', '')
    status_filtro = request.GET.get('status', '')
    mes_filtro = request.GET.get('mes', '')
    ano_filtro = request.GET.get('ano', '')

    # Otimização: usar select_related para carregar dados relacionados em uma única consulta
    cobrancas_list = Cobranca.objects.select_related(
        'contrato', 'contrato__proprietario', 'contrato__inquilino', 'contrato__imovel', 'inquilino'
    ).order_by('-data_vencimento')

    # Aplicar filtros
    if query:
        cobrancas_list = cobrancas_list.filter(
            Q(contrato__inquilino__nome__icontains=query) |
            Q(contrato__imovel__endereco__icontains=query)
        )
    if status_filtro:
        cobrancas_list = cobrancas_list.filter(status=status_filtro)
    if mes_filtro:
        try:
            cobrancas_list = cobrancas_list.filter(mes_referencia=int(mes_filtro))
        except ValueError:
            pass  # Ignorar filtro inválido
    if ano_filtro:
        try:
            cobrancas_list = cobrancas_list.filter(ano_referencia=int(ano_filtro))
        except ValueError:
            pass  # Ignorar filtro inválido

    paginator = Paginator(cobrancas_list, 20)  # 20 cobranças por página
    page = request.GET.get('page')

    try:
        cobrancas = paginator.page(page)
    except PageNotAnInteger:
        cobrancas = paginator.page(1)
    except EmptyPage:
        cobrancas = paginator.page(paginator.num_pages)

    # Otimização: usar valores em cache para anos disponíveis
    anos = Cobranca.objects.dates('data_vencimento', 'year').distinct()

    context = {
        'cobrancas': cobrancas,
        'query': query,
        'status_filtro': status_filtro,
        'mes_filtro': mes_filtro,
        'ano_filtro': ano_filtro,
        'anos': anos,
        'status_choices': Cobranca.STATUS_CHOICES,
    }

    return render(request, 'cobrancas/listar_cobrancas.html', context)

def gerar_cobrancas_view(request):
    """
    View para gerar cobranças em lote.
    Otimizada com select_related para reduzir consultas.
    """
    if request.method == 'POST':
        form = GerarCobrancasForm(request.POST)
        if form.is_valid():
            mes = form.cleaned_data['mes']
            ano = form.cleaned_data['ano']

            # Verificar se já existem cobranças para este mês/ano
            cobranças_existentes = Cobranca.objects.filter(
                mes_referencia=mes,
                ano_referencia=ano
            ).exists()  # Otimização: usar exists() em vez de contar todos os registros

            if cobranças_existentes:
                messages.warning(request, f"Já existem cobranças para {mes}/{ano}. Verifique a lista de cobranças.")
                return redirect('lista_cobrancas')

            # Otimização: carregar todos os dados necessários em uma única consulta
            contratos_ativos = Contrato.objects.filter(ativo=True).select_related(
                'proprietario', 'inquilino', 'imovel'
            )

            cobranças_geradas = 0

            for contrato in contratos_ativos:
                # Calcular data de vencimento (dia de pagamento do contrato no mês/ano especificado)
                try:
                    dia_pagamento = min(contrato.dia_pagamento, 28)  # Limitar a 28 para evitar problemas com fevereiro
                    data_vencimento = date(ano, mes, dia_pagamento)

                    # Verificar se o contrato estava ativo na data de vencimento
                    if contrato.data_inicio <= data_vencimento and contrato.data_fim >= data_vencimento:
                        # Calcular valor da cobrança
                        valor = contrato.calcular_valor_total()

                        # Criar cobrança
                        cobranca = Cobranca.objects.create(
                            contrato=contrato,
                            mes_referencia=mes,
                            ano_referencia=ano,
                            data_vencimento=data_vencimento,
                            valor=valor,
                            inquilino=contrato.inquilino,
                            descricao=f"Aluguel {mes}/{ano} - {contrato.imovel.endereco_resumido}"
                        )

                        # Integração com Asaas (se o inquilino tiver asaas_id)
                        if contrato.inquilino.asaas_id:
                            asaas_service = AsaasService()
                            resposta = asaas_service.gerar_cobranca(
                                contrato.inquilino.asaas_id,
                                valor,
                                data_vencimento.strftime('%Y-%m-%d'),
                                contrato.inquilino.nome,
                                f"Aluguel {mes}/{ano} - {contrato.imovel.endereco_resumido}"
                            )

                            if resposta and "id" in resposta:
                                # Otimização: atualizar todos os campos em uma única operação
                                Cobranca.objects.filter(id=cobranca.id).update(
                                    asaas_payment_id=resposta["id"],
                                    asaas_boleto_url=resposta.get("bankSlipUrl", ""),
                                    asaas_pix_copia_cola=resposta.get("pixCopiaECola", ""),
                                    asaas_pix_url=resposta.get("pixUrl", ""),
                                    asaas_codigo_barras=resposta.get("barCode", "")
                                )

                        cobranças_geradas += 1
                except Exception as e:
                    messages.error(request, f"Erro ao gerar cobrança para contrato {contrato.id}: {str(e)}")

            if cobranças_geradas > 0:
                messages.success(request, f"{cobranças_geradas} cobranças geradas com sucesso para {mes}/{ano}!")
            else:
                messages.warning(request, f"Nenhuma cobrança gerada para {mes}/{ano}. Verifique se existem contratos ativos para este período.")

            return redirect('lista_cobrancas')
        else:
            messages.error(request, "Por favor, corrija os erros no formulário.")
    else:
        # Sugerir mês/ano atual para o formulário
        hoje = date.today()
        proximo_mes = hoje.month + 1 if hoje.month < 12 else 1
        proximo_ano = hoje.year if hoje.month < 12 else hoje.year + 1

        form = GerarCobrancasForm(initial={
            'mes': proximo_mes,
            'ano': proximo_ano
        })

    return render(request, 'cobrancas/gerar_cobrancas.html', {'form': form})

def editar_cobranca(request, pk):
    """
    View para editar uma cobrança existente.
    Otimizada com select_related para reduzir consultas.
    """
    # Otimização: carregar dados relacionados em uma única consulta
    cobranca = get_object_or_404(
        Cobranca.objects.select_related('contrato', 'contrato__proprietario', 'contrato__inquilino', 'inquilino'),
        pk=pk
    )

    if request.method == 'POST':
        form = CobrancaForm(request.POST, instance=cobranca)
        if form.is_valid():
            form.save()
            messages.success(request, "Cobrança atualizada com sucesso!")
            return redirect('lista_cobrancas')
        else:
            messages.error(request, "Por favor, corrija os erros no formulário.")
    else:
        form = CobrancaForm(instance=cobranca)

    return render(request, 'cobrancas/editar_cobranca.html', {
        'form': form,
        'cobranca': cobranca
    })

def excluir_cobranca(request, pk):
    """
    View para excluir uma cobrança.
    """
    cobranca = get_object_or_404(Cobranca, pk=pk)

    if request.method == 'POST':
        cobranca.delete()
        messages.success(request, "Cobrança excluída com sucesso!")
        return redirect('lista_cobrancas')

    return render(request, 'cobrancas/confirmar_exclusao.html', {
        'cobranca': cobranca
    })

def marcar_como_recebida(request, pk):
    """
    View para marcar uma cobrança como recebida.
    """
    cobranca = get_object_or_404(Cobranca, pk=pk)

    if request.method == 'POST':
        data_pagamento = request.POST.get('data_pagamento')

        try:
            data_pagamento_dt = datetime.strptime(data_pagamento, '%Y-%m-%d').date()

            # Otimização: atualizar diretamente no banco de dados em vez de carregar, modificar e salvar
            Cobranca.objects.filter(pk=pk).update(
                data_pagamento=data_pagamento_dt,
                status='paga'
            )

            messages.success(request, f"Cobrança {cobranca.id} marcada como recebida em {data_pagamento_dt.strftime('%d/%m/%Y')}.")
        except ValueError:
            messages.error(request, "Formato de data inválido.")

    referer = request.META.get('HTTP_REFERER', 'lista_cobrancas')
    return redirect(referer)

def marcar_como_repassada(request, pk):
    """
    View para marcar uma cobrança como repassada ao proprietário.
    """
    cobranca = get_object_or_404(Cobranca, pk=pk)

    if request.method == 'POST':
        data_repasse = request.POST.get('data_repasse')

        try:
            data_repasse_dt = datetime.strptime(data_repasse, '%Y-%m-%d').date()

            # Otimização: atualizar diretamente no banco de dados em vez de carregar, modificar e salvar
            Cobranca.objects.filter(pk=pk).update(
                data_repasse=data_repasse_dt,
                status_repasse='repassado'
            )

            messages.success(request, f"Repasse da cobrança {cobranca.id} marcado para {data_repasse_dt.strftime('%d/%m/%Y')}.")
        except ValueError:
            messages.error(request, "Formato de data inválido.")

    referer = request.META.get('HTTP_REFERER', 'lista_cobrancas')
    return redirect(referer)

def cobranca_update(request, pk):
    """
    View para atualizar uma cobrança via AJAX.
    """
    if request.method == 'POST':
        field = request.POST.get('field')
        value = request.POST.get('value')

        # Otimização: atualizar diretamente no banco de dados sem carregar o objeto
        if field == 'status':
            Cobranca.objects.filter(pk=pk).update(status=value)
            return JsonResponse({'success': True})
        elif field == 'status_repasse':
            Cobranca.objects.filter(pk=pk).update(status_repasse=value)
            return JsonResponse({'success': True})

    return JsonResponse({'success': False, 'error': 'Método ou campo inválido'})

def pagar_cobranca(request, pk):
    """
    View para registrar o pagamento de uma cobrança.
    """
    # Otimização: carregar dados relacionados em uma única consulta
    cobranca = get_object_or_404(
        Cobranca.objects.select_related('contrato'),
        pk=pk
    )

    if request.method == 'POST':
        data_pagamento = request.POST.get('data_pagamento', date.today().strftime('%Y-%m-%d'))

        try:
            data_pagamento_dt = datetime.strptime(data_pagamento, '%Y-%m-%d').date()

            # Otimização: atualizar diretamente no banco de dados
            Cobranca.objects.filter(pk=pk).update(
                data_pagamento=data_pagamento_dt,
                status='paga'
            )

            messages.success(request, f"Pagamento da cobrança {cobranca.id} registrado com sucesso!")
        except ValueError:
            messages.error(request, "Formato de data inválido.")

    return redirect('dashboard', id=cobranca.contrato.id)

def repassar_valor(request, pk):
    """
    View para registrar o repasse de uma cobrança ao proprietário.
    """
    # Otimização: carregar dados relacionados em uma única consulta
    cobranca = get_object_or_404(
        Cobranca.objects.select_related('contrato'),
        pk=pk
    )

    if request.method == 'POST':
        data_repasse = request.POST.get('data_repasse', date.today().strftime('%Y-%m-%d'))

        try:
            data_repasse_dt = datetime.strptime(data_repasse, '%Y-%m-%d').date()

            # Otimização: atualizar diretamente no banco de dados
            Cobranca.objects.filter(pk=pk).update(
                data_repasse=data_repasse_dt,
                status_repasse='repassado'
            )

            messages.success(request, f"Repasse da cobrança {cobranca.id} registrado com sucesso!")
        except ValueError:
            messages.error(request, "Formato de data inválido.")

    return redirect('dashboard', id=cobranca.contrato.id)

def atualizar_datas_cobranca(request, pk):
    """
    View para atualizar as datas de uma cobrança.
    """
    # Otimização: carregar dados relacionados em uma única consulta
    cobranca = get_object_or_404(
        Cobranca.objects.select_related('contrato'),
        pk=pk
    )

    if request.method == 'POST':
        data_vencimento = request.POST.get('data_vencimento')
        data_pagamento = request.POST.get('data_pagamento')
        data_repasse = request.POST.get('data_repasse')

        try:
            # Preparar dicionário de atualizações
            updates = {}

            if data_vencimento:
                updates['data_vencimento'] = datetime.strptime(data_vencimento, '%Y-%m-%d').date()

            if data_pagamento:
                updates['data_pagamento'] = datetime.strptime(data_pagamento, '%Y-%m-%d').date()
                updates['status'] = 'paga'

            if data_repasse:
                updates['data_repasse'] = datetime.strptime(data_repasse, '%Y-%m-%d').date()
                updates['status_repasse'] = 'repassado'

            # Otimização: atualizar diretamente no banco de dados em uma única operação
            if updates:
                Cobranca.objects.filter(pk=pk).update(**updates)

            messages.success(request, f"Datas da cobrança {cobranca.id} atualizadas com sucesso!")
        except ValueError:
            messages.error(request, "Formato de data inválido.")

    return redirect('dashboard', id=cobranca.contrato.id)

def gerar_recibo_pagamento(request, pk):
    """
    View para gerar o recibo de pagamento de uma cobrança.
    (Placeholder - requires actual PDF generation logic)
    """
    cobranca = get_object_or_404(
        Cobranca.objects.select_related('contrato', 'inquilino'),
        pk=pk
    )

    # Placeholder - implement actual PDF generation
    messages.info(request, "Funcionalidade de gerar recibo ainda não implementada.")
    return redirect('dashboard', id=cobranca.contrato.id)
