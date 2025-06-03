# financeiro/views/lembrete_views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta
from django.views.decorators.http import require_http_methods

from financeiro.models.lembrete import LembreteEnviado
from financeiro.models.cobranca import Cobranca
from financeiro.forms.lembrete_forms import ConfiguracaoLembreteForm, EnvioManualForm



def lembrete_list(request):
    """Lista de lembretes enviados com filtros"""
    lembretes = LembreteEnviado.objects.select_related('cobranca', 'cobranca__contrato', 'cobranca__inquilino').all()
    
    # Filtros
    tipo_filtro = request.GET.get('tipo', '')
    status_filtro = request.GET.get('status', '')
    data_inicio = request.GET.get('data_inicio', '')
    data_fim = request.GET.get('data_fim', '')
    search = request.GET.get('search', '')
    
    if tipo_filtro:
        lembretes = lembretes.filter(tipo=tipo_filtro)
    
    if status_filtro:
        lembretes = lembretes.filter(status=status_filtro)
    
    if data_inicio:
        lembretes = lembretes.filter(data_envio__gte=data_inicio)
    
    if data_fim:
        lembretes = lembretes.filter(data_envio__lte=data_fim)
    
    if search:
        lembretes = lembretes.filter(
            Q(cobranca__inquilino__nome__icontains=search) |
            Q(cobranca__contrato__imovel__endereco__icontains=search) |
            Q(observacao__icontains=search)
        )
    
    # Paginação
    paginator = Paginator(lembretes, 20)
    page_number = request.GET.get('page')
    lembretes_page = paginator.get_page(page_number)
    
    # Estatísticas
    stats = {
        'total': lembretes.count(),
        'enviados': lembretes.filter(status='enviado').count(),
        'falhas': lembretes.filter(status='falha').count(),
        'hoje': lembretes.filter(data_envio__date=timezone.now().date()).count()
    }
    
    context = {
        'lembretes': lembretes_page,
        'stats': stats,
        'filtros': {
            'tipo': tipo_filtro,
            'status': status_filtro,
            'data_inicio': data_inicio,
            'data_fim': data_fim,
            'search': search
        },
        'tipos_choices': LembreteEnviado.CANAIS,
        'status_choices': LembreteEnviado.STATUS,
    }
    
    return render(request, 'financeiro/lembretes/lembrete_list.html', context)



def lembrete_detail(request, pk):
    """Detalhes de um lembrete específico"""
    lembrete = get_object_or_404(LembreteEnviado, pk=pk)
    
    # Outros lembretes da mesma cobrança
    outros_lembretes = LembreteEnviado.objects.filter(
        cobranca=lembrete.cobranca
    ).exclude(pk=pk).order_by('-data_envio')
    
    context = {
        'lembrete': lembrete,
        'outros_lembretes': outros_lembretes,
    }
    
    return render(request, 'financeiro/lembretes/detail.html', context)



def configuracao_lembretes(request):
    """Configuração de lembretes automáticos"""
    if request.method == 'POST':
        form = ConfiguracaoLembreteForm(request.POST)
        if form.is_valid():
            # Salvar configurações (implementar modelo de configuração se necessário)
            messages.success(request, 'Configurações de lembretes atualizadas com sucesso!')
            return redirect('financeiro:configuracao_lembretes')
    else:
        # Carregar configurações existentes
        form = ConfiguracaoLembreteForm()
    
    context = {
        'form': form,
    }
    
    return render(request, 'financeiro/lembretes/configuracao.html', context)



def envio_manual(request):
    """Envio manual de lembretes"""
    if request.method == 'POST':
        form = EnvioManualForm(request.POST)
        if form.is_valid():
            cobrancas = form.cleaned_data['cobrancas']
            tipo_envio = form.cleaned_data['tipo']
            template_personalizado = form.cleaned_data.get('template_personalizado')
            
            # Processar envio para cada cobrança
            enviados = 0
            falhas = 0
            
            for cobranca in cobrancas:
                try:
                    # Aqui você implementaria a lógica de envio real
                    # Por exemplo, integração com WhatsApp, email, etc.
                    
                    # Simular envio (substituir por implementação real)
                    sucesso = simular_envio_lembrete(cobranca, tipo_envio, template_personalizado)
                    
                    # Registrar lembrete
                    dias_antes = (cobranca.data_vencimento - timezone.now().date()).days
                    LembreteEnviado.objects.create(
                        cobranca=cobranca,
                        tipo=tipo_envio,
                        dias_antes_vencimento=dias_antes,
                        status='enviado' if sucesso else 'falha',
                        observacao=template_personalizado if template_personalizado else None
                    )
                    
                    if sucesso:
                        enviados += 1
                    else:
                        falhas += 1
                        
                except Exception as e:
                    falhas += 1
                    # Log do erro
                    
            messages.success(
                request, 
                f'Envio concluído! {enviados} enviados com sucesso, {falhas} falhas.'
            )
            return redirect('financeiro:lembrete_list')
    else:
        form = EnvioManualForm()
    
    context = {
        'form': form,
    }
    
    return render(request, 'financeiro/lembretes/envio_manual.html', context)



@require_http_methods(["GET"])
def cobrancas_pendentes_api(request):
    """API para buscar cobranças pendentes (para AJAX)"""
    term = request.GET.get('term', '')
    
    cobrancas = Cobranca.objects.filter(
        status__in=['pendente', 'atrasada']
    ).select_related('inquilino', 'contrato')
    
    if term:
        cobrancas = cobrancas.filter(
            Q(inquilino__nome__icontains=term) |
            Q(contrato__imovel__endereco__icontains=term)
        )
    
    cobrancas = cobrancas[:20]  # Limitar resultados
    
    results = []
    for cobranca in cobrancas:
        results.append({
            'id': cobranca.pk,
            'text': f"{cobranca.inquilino.nome} - {cobranca.data_referencia_texto} - Venc: {cobranca.data_vencimento.strftime('%d/%m/%Y')}",
            'vencimento': cobranca.data_vencimento.strftime('%Y-%m-%d'),
            'valor': str(cobranca.valor_total)
        })
    
    return JsonResponse({'results': results})



def dashboard_lembretes(request):
    """Dashboard com estatísticas de lembretes"""
    hoje = timezone.now().date()
    ultima_semana = hoje - timedelta(days=7)
    ultimo_mes = hoje - timedelta(days=30)
    
    # Estatísticas gerais
    stats = {
        'total_ultima_semana': LembreteEnviado.objects.filter(
            data_envio__gte=ultima_semana
        ).count(),
        'total_ultimo_mes': LembreteEnviado.objects.filter(
            data_envio__gte=ultimo_mes
        ).count(),
        'taxa_sucesso_semana': 0,
        'taxa_sucesso_mes': 0,
    }
    
    # Taxa de sucesso
    lembretes_semana = LembreteEnviado.objects.filter(data_envio__gte=ultima_semana)
    if lembretes_semana.exists():
        enviados_semana = lembretes_semana.filter(status='enviado').count()
        stats['taxa_sucesso_semana'] = round((enviados_semana / lembretes_semana.count()) * 100, 1)
    
    lembretes_mes = LembreteEnviado.objects.filter(data_envio__gte=ultimo_mes)
    if lembretes_mes.exists():
        enviados_mes = lembretes_mes.filter(status='enviado').count()
        stats['taxa_sucesso_mes'] = round((enviados_mes / lembretes_mes.count()) * 100, 1)
    
    # Estatísticas por canal
    stats_por_canal = LembreteEnviado.objects.filter(
        data_envio__gte=ultimo_mes
    ).values('tipo').annotate(
        total=Count('id'),
        enviados=Count('id', filter=Q(status='enviado')),
        falhas=Count('id', filter=Q(status='falha'))
    )
    
    # Cobranças que precisam de lembrete
    cobrancas_pendentes = Cobranca.objects.filter(
        status__in=['pendente', 'atrasada'],
        data_vencimento__lte=hoje + timedelta(days=10)
    ).count()
    
    context = {
        'stats': stats,
        'stats_por_canal': stats_por_canal,
        'cobrancas_pendentes': cobrancas_pendentes,
    }
    
    return render(request, 'financeiro/lembretes/dashboard.html', context)


def simular_envio_lembrete(cobranca, tipo, template=None):
    """
    Função simulada de envio - substituir por implementação real
    """
    # Aqui você implementaria a integração real com:
    # - WhatsApp Business API
    # - Provedor de email (SendGrid, Mailgun, etc.)
    # - Provedor de SMS
    
    # Por enquanto, simular sucesso baseado em alguma lógica
    import random
    return random.choice([True, True, True, False])  # 75% de sucesso