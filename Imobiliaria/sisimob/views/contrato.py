from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.utils import timezone
from datetime import date, datetime
from decimal import Decimal
from dateutil.relativedelta import relativedelta
from sisimob.models import Contrato, Cliente, Imovel
from sisimob.forms import ContratoForm, ContratoFiltroForm, ReajusteContratosForm
from financeiro.services.contrato_financeiro import (
    ContratoFinanceiroService,
)
from financeiro.models.indice import IndiceInflacao








def cadastrar_contrato(request):
    """
    View para cadastro de novos contratos
    """
    if request.method == 'POST':
        form = ContratoForm(request.POST, request.FILES)
        if form.is_valid():
            contrato = form.save()
            messages.success(request, "Contrato cadastrado com sucesso!")
            return redirect('listar_contratos')
        else:
            messages.error(request, "Por favor, corrija os erros no formulário.")
    else:
        form = ContratoForm()
    
    return render(request, 'contratos/cadastro_contrato.html', {
        'form': form,
        'titulo': 'Cadastro de Contrato',
        'botao_acao': 'Cadastrar'
    })

 
def listar_contratos(request):
    """
    View para listagem de contratos com filtros
    """
    contratos = Contrato.objects.prefetch_related(
        'inquilino', 'proprietario', 'imovel', 'fiador'
    ).all()
    
    # Aplicar filtros
    filtro_form = ContratoFiltroForm(request.GET)
    
    if filtro_form.is_valid():
        filtro_tipo = filtro_form.cleaned_data.get('filtro_tipo')
        buscar = filtro_form.cleaned_data.get('buscar')
        
        if filtro_tipo == 'ativo':
            contratos = contratos.filter(ativo=True)
        elif filtro_tipo == 'inativo':
            contratos = contratos.filter(ativo=False)
        
        if buscar:
            contratos = contratos.filter(
                Q(proprietario__nome__icontains=buscar) |
                Q(inquilino__nome__icontains=buscar) |
                Q(imovel__endereco__icontains=buscar)
            )
    
    # Paginação
    paginator = Paginator(contratos, 15)
    page_number = request.GET.get('page')
    
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    
    context = {
        'page_obj': page_obj,
        'filtro_form': filtro_form,
        'total_contratos': contratos.count(),
    }
    
    return render(request, 'contratos/listar_contratos.html', context)


def editar_contrato(request, contrato_id):
    """
    View para edição de contratos existentes
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


def detalhes_contrato(request, contrato_id):
    """
    View para exibir detalhes completos de um contrato
    """
    contrato = get_object_or_404(Contrato, id=contrato_id)

    financeiro = ContratoFinanceiroService.obter_detalhes_contrato(contrato)
    inquilinos = contrato.inquilino.all()
    inquilino_principal = inquilinos.first() if inquilinos.exists() else None

    proprietarios = contrato.proprietario.all()
    proprietario_principal = proprietarios.first() if proprietarios.exists() else None

    imovel = contrato.imovel
    contrato_ativo = contrato.esta_ativo if hasattr(contrato, 'esta_ativo') else contrato.ativo

    context = {
        'contrato': contrato,
        'imovel': imovel,
        'inquilinos': inquilinos,
        'inquilino_principal': inquilino_principal,
        'proprietarios': proprietarios,
        'proprietario_principal': proprietario_principal,
        'contrato_ativo': contrato_ativo,
        'status_vencimento': getattr(contrato, 'status_vencimento', 'normal'),
        'dias_restantes': getattr(contrato, 'dias_restantes', 0),
        'valor_aluguel_atual': getattr(contrato, 'valor_aluguel', contrato.valor_base),
        'valor_taxa_administracao': contrato.valor_taxa_administracao(),
        'valor_repasse': getattr(contrato, 'valor_repasse', 0),
    }
    context.update(financeiro)

    return render(request, 'contratos/detalhes_contrato.html', context)


# Função auxiliar para debug (temporária)
def debug_contrato_relationships(request, contrato_id):
    """
    Função de debug para verificar relacionamentos do contrato
    Adicione esta URL temporariamente: path('debug/<int:contrato_id>/', debug_contrato_relationships)
    """
    from django.http import JsonResponse
    
    contrato = get_object_or_404(Contrato, id=contrato_id)
    
    # Testar diferentes relacionamentos
    relationships = {}
    
    # Teste para cobranças
    cobranca_tests = [
        'cobrancas_financeiro',
        'cobrancas',
        'cobranca_set'
    ]
    
    for rel_name in cobranca_tests:
        try:
    
    
            if hasattr(contrato, rel_name):
                manager = getattr(contrato, rel_name)
                relationships[rel_name] = {
                    'exists': True,
                    'count': manager.count(),
                    'type': str(type(manager))
                }
            else:
                relationships[rel_name] = {'exists': False}
        except Exception as e:
            relationships[rel_name] = {'exists': False, 'error': str(e)}
    
    # Teste para repasses
    repasse_tests = [
        'repasses',
        'repasse_set'
    ]
    
    for rel_name in repasse_tests:
        try:
            if hasattr(contrato, rel_name):
                manager = getattr(contrato, rel_name)
                relationships[rel_name] = {
                    'exists': True,
                    'count': manager.count(),
                    'type': str(type(manager))
                }
            else:
                relationships[rel_name] = {'exists': False}
        except Exception as e:
            relationships[rel_name] = {'exists': False, 'error': str(e)}
    
    debug_info = {
        'contrato_id': contrato.id,
        'contrato_str': str(contrato),
        'relationships_found': relationships,
        'all_attributes': [attr for attr in dir(contrato) if not attr.startswith('_')],
    }
    
    return JsonResponse(debug_info, indent=2)
def excluir_contrato(request, contrato_id):
    """
    View para exclusão de contratos
    """
    contrato = get_object_or_404(Contrato, id=contrato_id)
    
    if request.method == 'POST':
        # Verificar se o contrato tem cobranças associadas
        if contrato.cobrancas.exists():
            messages.error(
                request, 
                "Não é possível excluir este contrato pois ele possui cobranças associadas."
            )
            return redirect('listar_contratos')
        
        contrato_id = contrato.id
        contrato.delete()
        messages.success(request, f"Contrato #{contrato_id} excluído com sucesso.")
        return redirect('listar_contratos')
    
    return render(request, 'contratos/confirmar_exclusao.html', {
        'contrato': contrato,
        'objeto_tipo': 'Contrato'
    })


def reajustar_contratos(request):
    """
    View para reajuste de contratos
    """
    form = ReajusteContratosForm(request.POST or None)
    contratos_com_indices = []
    
    if request.method == 'POST' and form.is_valid():
        data_inicio = form.cleaned_data['data_inicio'].replace(day=1)
        valor_manual = form.cleaned_data['valor_manual']

        for contrato in Contrato.objects.filter(data_inicio__lte=data_inicio):
            # Determina o período correto para o cálculo do reajuste
            if hasattr(contrato, 'data_ultimo_reajuste') and contrato.data_ultimo_reajuste:
                # Se já teve reajuste, usa a data do último como referência
                data_base = contrato.data_ultimo_reajuste
            else:
                # Se nunca teve reajuste, usa a data de início do contrato
                data_base = contrato.data_inicio.replace(day=1)
            
            # O período vai do mês da data_base até 11 meses depois
            data_fim = data_base + relativedelta(months=11)

            fator_acumulado, valor_projetado = calcular_fator_acumulado(contrato, data_base, data_fim)

            if fator_acumulado:
                contratos_com_indices.append({
                    'contrato': contrato,
                    'fator_acumulado': fator_acumulado,
                    'valor_projetado': valor_projetado,
                })

        return render(request, 'contratos/reajustar_contratos.html', {
            'form': form,
            'contratos_com_indices': contratos_com_indices,
            'data_inicio': data_inicio,
            'valor_manual': valor_manual
        })

    else:
        # Mostrar contratos elegíveis para reajuste
        for contrato in Contrato.objects.filter(ativo=True):
            if hasattr(contrato, 'data_ultimo_reajuste') and contrato.data_ultimo_reajuste:
                data_base = contrato.data_ultimo_reajuste
            else:
                data_base = contrato.data_inicio.replace(day=1)
                
            # O período vai do mês da data_base até 11 meses depois
            data_fim = data_base + relativedelta(months=11)

            fator_acumulado, valor_projetado = calcular_fator_acumulado(contrato, data_base, data_fim)

            if fator_acumulado:
                contratos_com_indices.append({
                    'contrato': contrato,
                    'fator_acumulado': fator_acumulado,
                    'valor_projetado': valor_projetado,
                })

    return render(request, 'contratos/reajustar_contratos.html', {
        'form': form,
        'contratos_com_indices': contratos_com_indices
    })


def reajustar_contrato_individual(request, contrato_id):
    """
    View para reajuste individual de um contrato
    """
    contrato = get_object_or_404(Contrato, id=contrato_id)

    if request.method == 'POST':
        data_inicio_str = request.POST.get('data_inicio')
        valor_manual = request.POST.get('valor_manual')
        valor_manual_tipo = request.POST.get('tipo_valor_manual')

        if not data_inicio_str:
            messages.error(request, "Informe a data de início do reajuste.")
            return redirect('reajustar_contrato_individual', contrato_id=contrato_id)

        data_inicio = datetime.strptime(data_inicio_str, "%Y-%m-%d").date().replace(day=1)

        # Determina o período para o cálculo do reajuste
        if hasattr(contrato, 'data_ultimo_reajuste') and contrato.data_ultimo_reajuste:
            base_reajuste = contrato.data_ultimo_reajuste
        else:
            base_reajuste = contrato.data_inicio.replace(day=1)

        # Coleta dos índices de inflação - 12 meses consecutivos incluindo o mês base
        indices = []
        for i in range(12):
            mes = base_reajuste + relativedelta(months=i)
            indice = IndiceInflacao.objects.filter(
                tipo=contrato.fator_reajuste,
                data_referencia__year=mes.year,
                data_referencia__month=mes.month
            ).first()

            if not indice:
                messages.error(request, f"Índice não disponível para {mes.strftime('%m/%Y')}.")
                return redirect('reajustar_contrato_individual', contrato_id=contrato_id)

            indices.append(indice)

        # Cálculo do fator acumulado padrão com base nos índices
        fator_acumulado = Decimal('1.00')
        for indice in indices:
            fator_acumulado *= (1 + indice.valor / Decimal('100'))

        # Aplica o reajuste automático inicialmente
        valor_base = contrato.valor_base
        novo_valor = valor_base * fator_acumulado
        if novo_valor < valor_base:
            novo_valor = valor_base

        # Se informado, substitui pelo valor manual
        if valor_manual:
            try:
                valor_decimal = Decimal(valor_manual.replace(",", "."))
                if valor_manual_tipo == 'percentual':
                    novo_valor = valor_base * (1 + (valor_decimal / Decimal('100')))
                elif valor_manual_tipo == 'fator':
                    novo_valor = valor_base * valor_decimal
                elif valor_manual_tipo == 'fixo':
                    novo_valor = valor_decimal
                else:
                    messages.error(request, "Tipo de reajuste inválido.")
                    return redirect('reajustar_contrato_individual', contrato_id=contrato_id)

                if novo_valor < valor_base:
                    novo_valor = valor_base

            except:
                messages.error(request, "Valor manual inválido.")
                return redirect('reajustar_contrato_individual', contrato_id=contrato_id)

        # Atualiza o contrato com o novo valor
        contrato.valor_base = novo_valor
        if hasattr(contrato, 'data_ultimo_reajuste'):
            contrato.data_ultimo_reajuste = data_inicio
        
        # Histórico de reajuste
        historico = contrato.historico_aluguel or {}
        data_registro = data_inicio.isoformat()
        historico[data_registro] = float(novo_valor)
        contrato.historico_aluguel = historico

        contrato.save()

        messages.success(request, f"Contrato {contrato.id} reajustado com sucesso.")
        return redirect('reajustar_contratos')

    # GET request: mostra dados para reajuste
    if hasattr(contrato, 'data_ultimo_reajuste') and contrato.data_ultimo_reajuste:
        base_reajuste = contrato.data_ultimo_reajuste
    else:
        base_reajuste = contrato.data_inicio.replace(day=1)

    indices = []
    # Coleta os índices de 12 meses consecutivos
    for i in range(12):
        mes = base_reajuste + relativedelta(months=i)
        indice = IndiceInflacao.objects.filter(
            tipo=contrato.fator_reajuste,
            data_referencia__year=mes.year,
            data_referencia__month=mes.month
        ).first()
        if indice:
            indices.append({
                'mes': mes.strftime('%m/%Y'),
                'valor': indice.valor,
                'indice': indice
            })

    fator_acumulado = Decimal('1.00')
    for item in indices:
        fator_acumulado *= (1 + item['indice'].valor / Decimal('100'))

    valor_base = contrato.valor_base
    valor_projetado = valor_base * fator_acumulado
    if valor_projetado < valor_base:
        valor_projetado = valor_base

    return render(request, 'contratos/reajustar_contrato_individual.html', {
        'contrato': contrato,
        'indices': indices,
        'data_inicio': base_reajuste,
        'proxima_data_reajuste': base_reajuste + relativedelta(months=12),
        'valor_manual': request.GET.get('valor_manual', ''),
        'fator_acumulado': fator_acumulado,
        'fator_percentual': (fator_acumulado - Decimal('1.00')) * Decimal('100'),
        'valor_atual': contrato.valor_base,
        'valor_projetado': valor_projetado
    })


def calcular_fator_acumulado(contrato, data_base, data_fim):
    """
    Calcula o fator acumulado para um determinado período.
    """
    indices = []
    mes_atual = data_base
    
    # Coleta os índices mês a mês no período especificado (inclusive)
    while mes_atual <= data_fim:
        indice = IndiceInflacao.objects.filter(
            tipo=contrato.fator_reajuste,
            data_referencia__year=mes_atual.year,
            data_referencia__month=mes_atual.month
        ).first()
        
        if indice:
            indices.append(indice)
        
        mes_atual += relativedelta(months=1)
    
    # Se não temos todos os índices necessários, retornamos None
    if len(indices) < 12:
        return None, None
    
    # Calcula o fator acumulado
    fator_acumulado = Decimal('1.00')
    for indice in indices:
        fator_acumulado *= (1 + indice.valor / Decimal('100'))
    
    # Calcula o valor projetado
    valor_base = contrato.valor_base
    valor_projetado = valor_base * fator_acumulado
    if valor_projetado < valor_base:
        valor_projetado = valor_base
        
    return fator_acumulado, valor_projetado


# Views baseadas em classe (CBV)

class ContratoListView(ListView):
    """
    Class-based view para listagem de contratos
    """
    model = Contrato
    template_name = 'contratos/listar_contratos.html'
    context_object_name = 'contratos'
    paginate_by = 15
    ordering = ['-ativo', 'dia_pagamento', '-data_inicio']
    
    def get_queryset(self):
        queryset = super().get_queryset().prefetch_related(
            'inquilino', 'proprietario', 'imovel', 'fiador'
        )
        
        # Aplicar filtros da URL
        filtro_tipo = self.request.GET.get('filtro_tipo')
        buscar = self.request.GET.get('buscar')
        
        if filtro_tipo == 'ativo':
            queryset = queryset.filter(ativo=True)
        elif filtro_tipo == 'inativo':
            queryset = queryset.filter(ativo=False)
        
        if buscar:
            queryset = queryset.filter(
                Q(proprietario__nome__icontains=buscar) |
                Q(inquilino__nome__icontains=buscar) |
                Q(imovel__endereco__icontains=buscar)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filtro_form'] = ContratoFiltroForm(self.request.GET)
        context['total_contratos'] = self.get_queryset().count()
        return context


class ContratoCreateView(CreateView):
    """
    Class-based view para criação de contratos
    """
    model = Contrato
    form_class = ContratoForm
    template_name = 'contratos/cadastro_contrato.html'
    success_url = reverse_lazy('listar_contratos')
    
    def form_valid(self, form):
        messages.success(self.request, "Contrato cadastrado com sucesso!")
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Cadastro de Contrato'
        context['botao_acao'] = 'Cadastrar'
        return context


class ContratoUpdateView(UpdateView):
    """
    Class-based view para edição de contratos
    """
    model = Contrato
    form_class = ContratoForm
    template_name = 'contratos/cadastro_contrato.html'
    success_url = reverse_lazy('listar_contratos')
    pk_url_kwarg = 'contrato_id'
    
    def form_valid(self, form):
        messages.success(self.request, "Contrato atualizado com sucesso!")
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Contrato'
        context['botao_acao'] = 'Salvar'
        context['contrato'] = self.object
        return context


def dashboard_contrato(request, id):
    contrato = get_object_or_404(Contrato, id=id)

    ano_selecionado = int(request.GET.get('ano', timezone.now().year))
    status_selecionado = request.GET.get('status', '')

    context = ContratoFinanceiroService.obter_dashboard_contrato(
        contrato,
        ano_selecionado=ano_selecionado,
        status_selecionado=status_selecionado,
    )
    context.update({
        'contrato': contrato,
        'ano_selecionado': ano_selecionado,
        'status_selecionado': status_selecionado,
    })

    return render(request, 'contratos/dashboard.html', context)