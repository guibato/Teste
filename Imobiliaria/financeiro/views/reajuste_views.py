# financeiro/views/reajuste_views.py

from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.db.models import Q
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError
import json

from sisimob.models import Contrato
from financeiro.models.reajuste import ReajusteAluguel
from financeiro.services.reajuste_service import ReajusteService



def lista_reajustes(request):
    """
    View para listagem de reajustes com filtros
    """
    # Parâmetros de filtro
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    contrato_id = request.GET.get('contrato')
    indice = request.GET.get('indice')
    busca = request.GET.get('busca')
    
    # Query base
    reajustes = ReajusteAluguel.objects.select_related('contrato', 'contrato__imovel').all()
    
    # Aplicar filtros
    if data_inicio:
        try:
            data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
            reajustes = reajustes.filter(data_reajuste__gte=data_inicio)
        except ValueError:
            messages.error(request, 'Data de início inválida')
    
    if data_fim:
        try:
            data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
            reajustes = reajustes.filter(data_reajuste__lte=data_fim)
        except ValueError:
            messages.error(request, 'Data de fim inválida')
    
    if contrato_id:
        reajustes = reajustes.filter(contrato_id=contrato_id)
    
    if indice:
        reajustes = reajustes.filter(indice_utilizado=indice)
    
    if busca:
        # Busca em campos genéricos para compatibilidade
        filtros_busca = Q(contrato__imovel__endereco__icontains=busca) | Q(observacao__icontains=busca)
        
        # Adicionar filtros condicionalmente baseado nos campos disponíveis
        try:
            # Tentar buscar por diferentes campos de locatário
            filtros_busca |= Q(contrato__nome_locatario__icontains=busca)
        except:
            pass
        
        try:
            filtros_busca |= Q(contrato__locatario__nome__icontains=busca)
        except:
            pass
            
        try:
            filtros_busca |= Q(contrato__inquilino__icontains=busca)
        except:
            pass
            
        reajustes = reajustes.filter(filtros_busca)
    
    # Ordenação
    reajustes = reajustes.order_by('-data_reajuste', '-data_cadastro')
    
    # Paginação
    paginator = Paginator(reajustes, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Dados para os filtros
    contratos = Contrato.objects.filter(ativo=True).select_related('imovel').order_by('imovel__endereco')
    indices_choices = ReajusteAluguel._meta.get_field('indice_utilizado').choices
    
    # Adicionar campos calculados aos reajustes
    for reajuste in page_obj.object_list:
        reajuste.diferenca = reajuste.valor_reajustado - reajuste.valor_anterior
        reajuste.variacao_percentual = (
            (reajuste.valor_reajustado - reajuste.valor_anterior) / reajuste.valor_anterior * 100
        ) if reajuste.valor_anterior > 0 else 0
    stats = {
        'total_exibidos': len(page_obj.object_list),
        'total_geral': paginator.count,
        'valor_total_pagina': sum(r.valor_reajustado - r.valor_anterior for r in page_obj.object_list),
        'fator_medio_pagina': sum(r.fator_aplicado for r in page_obj.object_list) / len(page_obj.object_list) if page_obj.object_list else 0
    }
    
    context = {
        'page_obj': page_obj,
        'contratos': contratos,
        'indices_choices': indices_choices,
        'stats': stats,
        'filtros': {
            'data_inicio': request.GET.get('data_inicio', ''),
            'data_fim': request.GET.get('data_fim', ''),
            'contrato': request.GET.get('contrato', ''),
            'indice': request.GET.get('indice', ''),
            'busca': request.GET.get('busca', ''),
        }
    }
    
    return render(request, 'financeiro/reajustes/reajustes_list.html', context)



def sugestoes_reajustes(request):
    """
    View para exibir sugestões de reajustes pendentes
    """
    # Parâmetros
    meses_antecedencia = int(request.GET.get('meses', 2))
    data_limite = date.today() + relativedelta(months=meses_antecedencia)
    
    contratos_ids = request.GET.getlist('contratos')
    if contratos_ids:
        contratos_ids = [int(id) for id in contratos_ids if id.isdigit()]
    
    # Obter sugestões
    try:
        sugestoes = ReajusteService.obter_sugestoes_pendentes(
            data_limite=data_limite,
            contratos_ids=contratos_ids or None
        )
    except Exception as e:
        messages.error(request, f'Erro ao obter sugestões: {str(e)}')
        sugestoes = []
    
    # Adicionar campos calculados às sugestões
    for sugestao in sugestoes:
        if 'variacao_percentual' not in sugestao:
            sugestao['variacao_percentual'] = ReajusteService._calcular_variacao_percentual(
                sugestao['valor_anterior'], 
                sugestao['valor_sugerido']
            )
    stats = {
        'total': len(sugestoes),
        'vencidos': len([s for s in sugestoes if s['status'] == 'vencido']),
        'urgentes': len([s for s in sugestoes if s['status'] == 'urgente']),
        'pendentes': len([s for s in sugestoes if s['status'] == 'pendente']),
        'valor_total_atual': sum(s['valor_anterior'] for s in sugestoes),
        'valor_total_sugerido': sum(s['valor_sugerido'] for s in sugestoes),
    }
    
    if stats['valor_total_atual'] > 0:
        stats['aumento_percentual'] = (
            (stats['valor_total_sugerido'] - stats['valor_total_atual']) / 
            stats['valor_total_atual'] * 100
        )
        stats['aumento_valor'] = stats['valor_total_sugerido'] - stats['valor_total_atual']
    else:
        stats['aumento_percentual'] = 0
        stats['aumento_valor'] = 0
    
    # Contratos para filtro
    contratos = Contrato.objects.filter(ativo=True).select_related('imovel').order_by('imovel__endereco')
    
    context = {
        'sugestoes': sugestoes,
        'stats': stats,
        'contratos': contratos,
        'meses_antecedencia': meses_antecedencia,
        'contratos_selecionados': contratos_ids,
    }
    
    return render(request, 'financeiro/reajustes/sugestoes_reajustes.html', context)



@require_http_methods(["POST"])
def processar_reajustes_lote(request):
    """
    View para processar reajustes em lote
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Dados JSON inválidos'
        }, status=400)
    
    sugestoes_ids = data.get('sugestoes_ids', [])
    observacao_padrao = data.get('observacao', '')
    
    if not sugestoes_ids:
        return JsonResponse({
            'success': False,
            'message': 'Nenhuma sugestão selecionada'
        })
    
    try:
        resultado = ReajusteService.processar_reajustes_lote(
            sugestoes_ids=sugestoes_ids,
            usuario_id=request.user.id,
            observacao_padrao=observacao_padrao
        )
        
        return JsonResponse({
            'success': True,
            'message': f'{resultado["total_processados"]} reajustes processados com sucesso',
            'detalhes': {
                'sucessos': resultado["total_processados"],
                'erros': resultado["total_erros"],
                'lista_erros': resultado["erros"]
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erro ao processar reajustes: {str(e)}'
        }, status=500)



def form_reajuste(request, contrato_id=None, sugestao_data=None):
    """
    View para formulário de reajuste manual
    """
    contrato = get_object_or_404(Contrato, id=contrato_id) if contrato_id else None
    sugestao = None
    
    # Se há uma sugestão específica, buscar dados
    if contrato and sugestao_data:
        try:
            sugestao_data_obj = datetime.strptime(sugestao_data, '%Y-%m-%d').date()
            sugestao_temp = ReajusteAluguel.sugerir_reajuste(contrato)
            
            if (sugestao_temp and 
                sugestao_temp['data_reajuste'] == sugestao_data_obj):
                sugestao = sugestao_temp
        except ValueError:
            messages.error(request, 'Data de sugestão inválida')
    
    if request.method == 'POST':
        try:
            # Dados do formulário
            contrato_id = request.POST.get('contrato_id')
            valor_anterior = request.POST.get('valor_anterior')
            valor_reajustado = request.POST.get('valor_reajustado')
            fator_aplicado = request.POST.get('fator_aplicado')
            indice_utilizado = request.POST.get('indice_utilizado')
            data_reajuste = request.POST.get('data_reajuste')
            observacao = request.POST.get('observacao')
            
            # Validações básicas
            if not all([contrato_id, valor_anterior, valor_reajustado, fator_aplicado, indice_utilizado, data_reajuste]):
                raise ValidationError('Todos os campos obrigatórios devem ser preenchidos')
            
            # Conversões
            contrato = get_object_or_404(Contrato, id=contrato_id)
            valor_anterior = Decimal(valor_anterior)
            valor_reajustado = Decimal(valor_reajustado)
            fator_aplicado = Decimal(fator_aplicado)
            data_reajuste = datetime.strptime(data_reajuste, '%Y-%m-%d').date()
            
            # Validações de negócio
            if valor_anterior <= 0:
                raise ValidationError('Valor anterior deve ser maior que zero')
            if valor_reajustado <= 0:
                raise ValidationError('Valor reajustado deve ser maior que zero')
            if fator_aplicado < 0:
                raise ValidationError('Fator aplicado não pode ser negativo')
            if data_reajuste < contrato.data_inicio:
                raise ValidationError('Data do reajuste não pode ser anterior ao início do contrato')
            
            # Criar reajuste
            reajuste = ReajusteService.criar_reajuste(
                contrato=contrato,
                valor_anterior=valor_anterior,
                valor_reajustado=valor_reajustado,
                fator_aplicado=fator_aplicado,
                indice_utilizado=indice_utilizado,
                data_reajuste=data_reajuste,
                observacao=observacao
            )
            
            messages.success(
                request, 
                f'Reajuste criado com sucesso! Valor: R$ {valor_reajustado:.2f} (+{fator_aplicado:.2f}%)'
            )
            return redirect('financeiro:reajustes_list')
            
        except ValidationError as e:
            messages.error(request, str(e))
        except ValueError as e:
            messages.error(request, f'Erro nos dados fornecidos: {str(e)}')
        except Exception as e:
            messages.error(request, f'Erro ao criar reajuste: {str(e)}')
    
    # Dados para o formulário
    contratos = Contrato.objects.filter(ativo=True).select_related('imovel').order_by('imovel__endereco')
    indices_choices = ReajusteAluguel._meta.get_field('indice_utilizado').choices
    
    # Último reajuste do contrato (se houver)
    ultimo_reajuste = None
    if contrato:
        ultimo_reajuste = ReajusteAluguel.obter_ultimo_reajuste(contrato)
    
    context = {
        'contrato': contrato,
        'sugestao': sugestao,
        'contratos': contratos,
        'indices_choices': indices_choices,
        'ultimo_reajuste': ultimo_reajuste,
    }
    
    return render(request, 'financeiro/reajustes/form_reajuste.html', context)



def historico_contrato(request, contrato_id):
    """
    View para histórico de reajustes de um contrato
    """
    contrato = get_object_or_404(Contrato, id=contrato_id)
    
    # Parâmetros de filtro
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    
    if data_inicio:
        try:
            data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
        except ValueError:
            data_inicio = None
            messages.error(request, 'Data de início inválida')
    
    if data_fim:
        try:
            data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
        except ValueError:
            data_fim = None
            messages.error(request, 'Data de fim inválida')
    
    # Obter histórico
    try:
        historico = ReajusteService.obter_historico_contrato(
            contrato=contrato,
            data_inicio=data_inicio,
            data_fim=data_fim
        )
    except Exception as e:
        messages.error(request, f'Erro ao obter histórico: {str(e)}')
        historico = []
    
    # Próxima sugestão
    proxima_sugestao = None
    try:
        proxima_sugestao = ReajusteAluguel.sugerir_reajuste(contrato)
    except Exception as e:
        messages.warning(request, f'Não foi possível obter sugestão automática: {str(e)}')
    
    # Estatísticas do contrato
    reajustes_contrato = ReajusteAluguel.objects.filter(contrato=contrato)
    
    # Tentar obter valor_atual ou usar valor_base como fallback
    valor_atual = contrato.valor_base
    if hasattr(contrato, 'valor_atual') and contrato.valor_atual:
        valor_atual = contrato.valor_atual
    elif reajustes_contrato.exists():
        ultimo_reajuste = reajustes_contrato.order_by('-data_reajuste').first()
        valor_atual = ultimo_reajuste.valor_reajustado
    
    stats_contrato = {
        'total_reajustes': reajustes_contrato.count(),
        'valor_inicial': contrato.valor_base,
        'valor_atual': valor_atual,
        'variacao_total': 0,
        'tempo_contrato_meses': 0
    }
    
    if stats_contrato['total_reajustes'] > 0:
        ultimo_reajuste = reajustes_contrato.order_by('-data_reajuste').first()
        
        stats_contrato['variacao_total'] = (
            (ultimo_reajuste.valor_reajustado - contrato.valor_base) / contrato.valor_base * 100
        )
        
        # Calcular tempo de contrato
        delta = date.today() - contrato.data_inicio
        stats_contrato['tempo_contrato_meses'] = delta.days // 30
    
    context = {
        'contrato': contrato,
        'historico': historico,
        'proxima_sugestao': proxima_sugestao,
        'stats_contrato': stats_contrato,
        'filtros': {
            'data_inicio': request.GET.get('data_inicio', ''),
            'data_fim': request.GET.get('data_fim', ''),
        }
    }
    
    return render(request, 'financeiro/reajustes/historico_contrato.html', context)



def dashboard_reajustes(request):
    """
    View para dashboard com estatísticas de reajustes
    """
    # Período padrão: último ano
    data_fim = date.today()
    data_inicio = data_fim - relativedelta(years=1)
    
    # Parâmetros personalizados
    periodo_rapido = request.GET.get('periodo')
    if periodo_rapido:
        try:
            dias = int(periodo_rapido)
            data_inicio = data_fim - relativedelta(days=dias)
        except ValueError:
            pass
    
    if request.GET.get('data_inicio'):
        try:
            data_inicio = datetime.strptime(
                request.GET.get('data_inicio'), '%Y-%m-%d'
            ).date()
        except ValueError:
            messages.error(request, 'Data de início inválida')
    
    if request.GET.get('data_fim'):
        try:
            data_fim = datetime.strptime(
                request.GET.get('data_fim'), '%Y-%m-%d'
            ).date()
        except ValueError:
            messages.error(request, 'Data de fim inválida')
    
    # Obter estatísticas
    try:
        estatisticas = ReajusteService.obter_estatisticas_reajustes(
            data_inicio=data_inicio,
            data_fim=data_fim
        )
    except Exception as e:
        messages.error(request, f'Erro ao obter estatísticas: {str(e)}')
        estatisticas = {
            'total_reajustes': 0,
            'valor_total_reajustado': Decimal('0'),
            'fator_medio': Decimal('0'),
            'maior_reajuste': None,
            'menor_reajuste': None,
            'distribuicao_indices': {}
        }
    
    # Sugestões pendentes
    try:
        sugestoes = ReajusteService.obter_sugestoes_pendentes()
        sugestoes_stats = {
            'total': len(sugestoes),
            'vencidos': len([s for s in sugestoes if s['status'] == 'vencido']),
            'urgentes': len([s for s in sugestoes if s['status'] == 'urgente']),
            'valor_potencial': sum(s['valor_sugerido'] - s['valor_anterior'] for s in sugestoes)
        }
    except Exception as e:
        messages.warning(request, f'Erro ao obter sugestões: {str(e)}')
        sugestoes_stats = {
            'total': 0,
            'vencidos': 0,
            'urgentes': 0,
            'valor_potencial': 0
        }
    
    context = {
        'estatisticas': estatisticas,
        'sugestoes_stats': sugestoes_stats,
        'periodo': {
            'inicio': data_inicio,
            'fim': data_fim
        },
        'filtros': {
            'data_inicio': request.GET.get('data_inicio', data_inicio.strftime('%Y-%m-%d')),
            'data_fim': request.GET.get('data_fim', data_fim.strftime('%Y-%m-%d')),
            'periodo': periodo_rapido or ''
        }
    }
    
    return render(request, 'financeiro/reajustes/dashboard_reajustes.html', context)



@require_http_methods(["POST"])
def api_calcular_reajuste(request):
    """
    API para calcular reajuste em tempo real
    """
    try:
        data = json.loads(request.body)
        valor_anterior = Decimal(str(data.get('valor_anterior', 0)))
        percentual = Decimal(str(data.get('percentual', 0)))
        
        if valor_anterior <= 0:
            return JsonResponse({'error': 'Valor anterior deve ser maior que zero'}, status=400)
        
        if percentual < 0:
            return JsonResponse({'error': 'Percentual não pode ser negativo'}, status=400)
        
        valor_reajustado = ReajusteAluguel.calcular_reajuste(
            valor_anterior, percentual
        )
        
        diferenca = valor_reajustado - valor_anterior
        
        return JsonResponse({
            'valor_reajustado': float(valor_reajustado),
            'diferenca': float(diferenca),
            'percentual_aplicado': float(percentual),
            'variacao_percentual': float((diferenca / valor_anterior * 100)) if valor_anterior > 0 else 0
        })
        
    except (ValueError, TypeError, json.JSONDecodeError) as e:
        return JsonResponse({'error': f'Dados inválidos: {str(e)}'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)



def api_sugestao_contrato(request, contrato_id):
    """
    API para obter sugestão de reajuste para um contrato específico
    """
    try:
        contrato = get_object_or_404(Contrato, id=contrato_id)
        sugestao = ReajusteAluguel.sugerir_reajuste(contrato)
        
        if not sugestao:
            return JsonResponse({
                'success': False,
                'message': 'Não há sugestão disponível para este contrato. Verifique se há índices suficientes cadastrados.'
            })
        
        # Verificar se já existe reajuste
        ja_existe = ReajusteService._ja_possui_reajuste(
            contrato, sugestao['data_reajuste']
        )
        
        return JsonResponse({
            'success': True,
            'sugestao': {
                'valor_anterior': float(sugestao['valor_anterior']),
                'valor_sugerido': float(sugestao['valor_sugerido']),
                'fator_aplicado': float(sugestao['fator_aplicado']),
                'indice_utilizado': sugestao['indice_utilizado'],
                'data_reajuste': sugestao['data_reajuste'].isoformat(),
                'ja_existe': ja_existe,
                'diferenca': float(sugestao['valor_sugerido'] - sugestao['valor_anterior']),
                'variacao_percentual': float(
                    (sugestao['valor_sugerido'] - sugestao['valor_anterior']) / 
                    sugestao['valor_anterior'] * 100
                )
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)



def api_buscar_contratos(request):
    """
    API para buscar contratos com autocomplete
    """
    termo = request.GET.get('q', '')
    
    # Busca flexível em múltiplos campos
    filtros_busca = Q(imovel__endereco__icontains=termo)
    
    # Adicionar filtros condicionalmente baseado nos campos disponíveis
    try:
        filtros_busca |= Q(nome_locatario__icontains=termo)
    except:
        pass
    
    try:
        filtros_busca |= Q(locatario__nome__icontains=termo)
    except:
        pass
        
    try:
        filtros_busca |= Q(inquilino__icontains=termo)
    except:
        pass
    
    contratos = Contrato.objects.filter(
        filtros_busca,
        ativo=True
    ).select_related('imovel')[:10]
    
    resultados = []
    for contrato in contratos:
        ultimo_reajuste = ReajusteAluguel.obter_ultimo_reajuste(contrato)
        valor_atual = ultimo_reajuste.valor_reajustado if ultimo_reajuste else contrato.valor_base
        
        # Obter nome do locatário de forma flexível
        nome_locatario = 'N/A'
        if hasattr(contrato, 'nome_locatario') and contrato.nome_locatario:
            nome_locatario = contrato.nome_locatario
        elif hasattr(contrato, 'locatario') and contrato.locatario:
            if hasattr(contrato.locatario, 'nome'):
                nome_locatario = contrato.locatario.nome
            else:
                nome_locatario = str(contrato.locatario)
        elif hasattr(contrato, 'inquilino') and contrato.inquilino:
            nome_locatario = contrato.inquilino
        
        resultados.append({
            'id': contrato.id,
            'text': f"{contrato.imovel.endereco} - {nome_locatario}",
            'endereco': contrato.imovel.endereco,
            'locatario': nome_locatario,
            'valor_atual': float(valor_atual),
            'data_inicio': contrato.data_inicio.isoformat(),
            'fator_reajuste': getattr(contrato, 'fator_reajuste', 'IPCA')
        })
    
    return JsonResponse({'results': resultados})



@require_http_methods(["DELETE"])
def excluir_reajuste(request, reajuste_id):
    """
    API para excluir um reajuste (se permitido)
    """
    try:
        reajuste = get_object_or_404(ReajusteAluguel, id=reajuste_id)
        
        # Verificar se é o último reajuste do contrato
        ultimo_reajuste = ReajusteAluguel.objects.filter(
            contrato=reajuste.contrato
        ).order_by('-data_reajuste').first()
        
        if reajuste != ultimo_reajuste:
            return JsonResponse({
                'success': False,
                'message': 'Só é possível excluir o último reajuste do contrato'
            }, status=400)
        
        # Verificar se não há reajustes posteriores dependentes
        reajustes_posteriores = ReajusteAluguel.objects.filter(
            contrato=reajuste.contrato,
            data_reajuste__gt=reajuste.data_reajuste
        )
        
        if reajustes_posteriores.exists():
            return JsonResponse({
                'success': False,
                'message': 'Não é possível excluir este reajuste pois há reajustes posteriores'
            }, status=400)
        
        # Salvar dados para log
        dados_reajuste = {
            'contrato': str(reajuste.contrato),
            'valor_anterior': float(reajuste.valor_anterior),
            'valor_reajustado': float(reajuste.valor_reajustado),
            'data_reajuste': reajuste.data_reajuste.isoformat()
        }
        
        reajuste.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Reajuste excluído com sucesso',
            'dados': dados_reajuste
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erro ao excluir reajuste: {str(e)}'
        }, status=500)