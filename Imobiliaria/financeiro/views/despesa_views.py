# financeiro/views/despesa_views.py
"""
Views para gerenciamento de Despesas
====================================
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.views.generic import ListView, CreateView, UpdateView, DetailView
from django.urls import reverse_lazy
from django.db.models import Q, Sum
from django.http import JsonResponse

from ..models import Despesa
from ..forms.despesa_forms import DespesaForm


class DespesaListView(ListView):
    """
    View para listagem de despesas com filtros e paginação
    """
    model = Despesa
    template_name = 'financeiro/despesa/despesa_list.html'
    context_object_name = 'despesas'
    paginate_by = 20
    
    def get_queryset(self):
        """Aplica filtros na queryset baseado nos parâmetros GET"""
        queryset = Despesa.objects.select_related('contrato', 'tipo').all()
        
        # Filtro por status (ativa/inativa)
        status = self.request.GET.get('status', 'ativa')
        if status == 'ativa':
            queryset = queryset.filter(is_ativa=True)
        elif status == 'inativa':
            queryset = queryset.filter(is_ativa=False)
        
        # Filtro por quem paga
        paga_por = self.request.GET.get('paga_por')
        if paga_por and paga_por != 'todos':
            queryset = queryset.filter(paga_por=paga_por)
        
        # Filtro por tipo
        tipo_id = self.request.GET.get('tipo')
        if tipo_id:
            queryset = queryset.filter(tipo_id=tipo_id)
        
        # Filtro por busca geral
        busca = self.request.GET.get('busca', '').strip()
        if busca:
            queryset = queryset.filter(
                Q(descricao__icontains=busca) |
                Q(tipo__nome__icontains=busca) |
                Q(observacoes__icontains=busca)
            )
        
        return queryset.order_by('-data_cadastro')
    
    def get_context_data(self, **kwargs):
        """Adiciona dados extras ao contexto do template"""
        context = super().get_context_data(**kwargs)
        
        # Mantém os filtros no contexto
        context['filtro_status'] = self.request.GET.get('status', 'ativa')
        context['filtro_paga_por'] = self.request.GET.get('paga_por', 'todos')
        context['filtro_tipo'] = self.request.GET.get('tipo', '')
        context['filtro_busca'] = self.request.GET.get('busca', '')
        
        # Estatísticas
        context['total_despesas'] = Despesa.objects.count()
        context['despesas_ativas'] = Despesa.objects.filter(is_ativa=True).count()
        context['despesas_inativas'] = Despesa.objects.filter(is_ativa=False).count()
        
        # Soma de valores para despesas ativas
        valor_total = Despesa.objects.filter(is_ativa=True).aggregate(
            total=Sum('valor_total')
        )['total'] or 0
        context['valor_total_ativo'] = valor_total
        
        return context


class DespesaCreateView(CreateView):
    """
    View para criação de novas despesas - COM SUPORTE A RECORRENTES
    """
    model = Despesa
    form_class = DespesaForm
    template_name = 'financeiro/despesa/despesa_form.html'
    success_url = reverse_lazy('financeiro:despesa_list')
    
    def form_valid(self, form):
        """
        Processa o formulário válido, cria a despesa principal e recorrentes se necessário
        """
        from dateutil.relativedelta import relativedelta
        
        # Salvar a despesa principal
        self.object = form.save()
        
        # Verificar se deve gerar recorrentes
        gerar_recorrentes = form.cleaned_data.get('gerar_recorrentes', False)
        quantidade_recorrentes = form.cleaned_data.get('quantidade_recorrentes', 0)
        
        despesas_criadas = 1  # A despesa principal
        
        if gerar_recorrentes and quantidade_recorrentes > 0:
            try:
                # Mapear periodicidade para meses
                meses_por_periodo = {
                    'mensal': 1,
                    'bimestral': 2, 
                    'trimestral': 3,
                    'semestral': 6,
                    'anual': 12,
                    'unica': 1
                }
                
                intervalo_meses = meses_por_periodo.get(self.object.periodicidade, 1)
                data_base = self.object.data_inicio
                
                # Criar despesas recorrentes
                for i in range(1, quantidade_recorrentes):  # Começa do 1 porque a principal já foi criada
                    nova_data = data_base + relativedelta(months=intervalo_meses * i)
                    
                    # Criar nova despesa baseada na original
                    nova_despesa = Despesa.objects.create(
                        contrato=self.object.contrato,
                        tipo=self.object.tipo,
                        descricao=f"{self.object.descricao or self.object.get_descricao_padrao()} (#{i+1})",
                        valor_total=self.object.valor_total,
                        paga_por=self.object.paga_por,
                        numero_parcelas=self.object.numero_parcelas,
                        periodicidade=self.object.periodicidade,
                        data_inicio=nova_data,
                        percentual_repassado=self.object.percentual_repassado,
                        is_base_calculo_administracao=self.object.is_base_calculo_administracao,
                        is_recorrente=True,  # Marcar como recorrente
                        is_ativa=True,
                        observacoes=f"Despesa recorrente baseada na despesa #{self.object.pk}\n{self.object.observacoes or ''}"
                    )
                    despesas_criadas += 1
                
                # Marcar a despesa original como recorrente também
                self.object.is_recorrente = True
                self.object.save()
                
                messages.success(
                    self.request,
                    f'Despesa criada com sucesso! '
                    f'Foram geradas {despesas_criadas} despesas recorrentes automaticamente.'
                )
                
            except Exception as e:
                # Se der erro na criação das recorrentes, avisar mas não falhar
                messages.warning(
                    self.request,
                    f'Despesa principal criada, mas houve erro ao gerar recorrentes: {str(e)}'
                )
        else:
            messages.success(
                self.request, 
                f'Despesa "{self.object.get_descricao_padrao()}" criada com sucesso!'
            )
        
        return redirect(self.success_url)
    
    def form_invalid(self, form):
        """Adiciona mensagem de erro quando o formulário é inválido"""
        messages.error(
            self.request, 
            'Erro ao criar despesa. Verifique os dados informados.'
        )
        return super().form_invalid(form)
    
    def get_context_data(self, **kwargs):
        """Adiciona título da página ao contexto"""
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nova Despesa'
        context['botao_submit'] = 'Criar Despesa'
        return context
    
    def get_initial(self):
        """Define valores iniciais do formulário"""
        initial = super().get_initial()
        
        # Pré-selecionar tipo se veio na URL
        from ..models import TipoDespesa
        tipo_id = self.request.GET.get('tipo')
        if tipo_id:
            try:
                inicial_tipo = TipoDespesa.objects.get(pk=tipo_id)
                initial['tipo'] = inicial_tipo
            except TipoDespesa.DoesNotExist:
                pass
        
        # Data de início padrão = hoje
        from datetime import date
        initial['data_inicio'] = date.today()
        
        return initial

class DespesaUpdateView(UpdateView):
    """
    View para edição de despesas existentes
    """
    model = Despesa
    form_class = DespesaForm
    template_name = 'financeiro/despesa/despesa_form.html'
    success_url = reverse_lazy('financeiro:despesa_list')
    
    def form_valid(self, form):
        """Processa o formulário válido e adiciona mensagem de sucesso"""
        messages.success(
            self.request, 
            f'Despesa "{form.instance.get_descricao_padrao()}" atualizada com sucesso!'
        )
        return super().form_valid(form)
    
    def form_invalid(self, form):
        """Adiciona mensagem de erro quando o formulário é inválido"""
        messages.error(
            self.request, 
            'Erro ao atualizar despesa. Verifique os dados informados.'
        )
        return super().form_invalid(form)
    
    def get_context_data(self, **kwargs):
        """Adiciona título da página ao contexto"""
        context = super().get_context_data(**kwargs)
        context['titulo'] = f'Editar Despesa - {self.object.get_descricao_padrao()}'
        context['botao_submit'] = 'Salvar Alterações'
        return context


class DespesaDetailView(DetailView):
    """
    View para visualização detalhada de uma despesa
    """
    model = Despesa
    template_name = 'financeiro/despesa/despesa_detail.html'
    context_object_name = 'despesa'
    
    def get_context_data(self, **kwargs):
        """Adiciona informações detalhadas ao contexto"""
        context = super().get_context_data(**kwargs)
        
        # Cálculos financeiros
        context['valor_parcela'] = self.object.calcular_valor_parcela()
        context['valor_repassado'] = self.object.calcular_valor_repassado()
        context['parcelas_pagas'] = self.object.parcelas_pagas()
        
        # Status da despesa
        context['esta_ativa'] = self.object.parcela_ativa_em_data()
        
        return context


def despesa_toggle_status(request, pk):
    """
    View para alternar o status ativo/inativo de uma despesa
    """
    despesa = get_object_or_404(Despesa, pk=pk)
    
    # Alterna o status
    despesa.is_ativa = not despesa.is_ativa
    despesa.save()
    
    status_texto = 'ativada' if despesa.is_ativa else 'inativada'
    message = f'Despesa "{despesa.get_descricao_padrao()}" {status_texto} com sucesso!'
    
    # Resposta para AJAX
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': message,
            'novo_status': despesa.is_ativa,
            'status_display': 'Ativa' if despesa.is_ativa else 'Inativa'
        })
    
    # Resposta para requisição normal
    messages.success(request, message)
    return redirect('financeiro:despesa_list')


def despesa_duplicar(request, pk):
    """
    View para duplicar uma despesa existente
    """
    despesa_original = get_object_or_404(Despesa, pk=pk)
    
    # Criar nova despesa baseada na original
    nova_despesa = Despesa.objects.create(
        contrato=despesa_original.contrato,
        tipo=despesa_original.tipo,
        descricao=f"Cópia de {despesa_original.get_descricao_padrao()}",
        valor_total=despesa_original.valor_total,
        paga_por=despesa_original.paga_por,
        numero_parcelas=despesa_original.numero_parcelas,
        periodicidade=despesa_original.periodicidade,
        data_inicio=despesa_original.data_inicio,
        percentual_repassado=despesa_original.percentual_repassado,
        is_base_calculo_administracao=despesa_original.is_base_calculo_administracao,
        is_recorrente=despesa_original.is_recorrente,
        is_ativa=True,  # Nova despesa sempre ativa
        observacoes=despesa_original.observacoes
    )
    
    messages.success(
        request, 
        f'Despesa duplicada com sucesso! ID: {nova_despesa.pk}'
    )
    
    return redirect('financeiro:despesa_update', pk=nova_despesa.pk)

def despesa_visualizar_recorrentes(request, pk):
    """
    View para visualizar todas as despesas recorrentes relacionadas
    """
    despesa_base = get_object_or_404(Despesa, pk=pk)
    
    # Buscar outras despesas com mesmo contrato, tipo e que são recorrentes
    despesas_relacionadas = Despesa.objects.filter(
        contrato=despesa_base.contrato,
        tipo=despesa_base.tipo,
        is_recorrente=True
    ).order_by('data_inicio')
    
    context = {
        'despesa_base': despesa_base,
        'despesas_relacionadas': despesas_relacionadas,
        'total_despesas': despesas_relacionadas.count(),
        'valor_total_recorrentes': sum(d.valor_total for d in despesas_relacionadas)
    }
    
    return render(request, 'financeiro/despesa/despesa_recorrentes.html', context)