# financeiro/views/tipodespesa_views.py
"""
Views para gerenciamento de Tipos de Despesa
============================================
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import ListView, CreateView, UpdateView, DetailView
from django.urls import reverse_lazy
from django.db.models import Q
from django.http import JsonResponse

from ..models import TipoDespesa
from ..forms import TipoDespesaForm



class TipoDespesaListView(ListView):
    """
    View para listagem de tipos de despesa com filtros e paginação
    
    Funcionalidades:
    - Lista todos os tipos ativos por padrão
    - Filtro por status (ativo/inativo)
    - Busca por nome e descrição
    - Paginação de 20 itens por página
    """
    model = TipoDespesa
    template_name = 'financeiro/tipodespesa/tipodespesa_list.html'
    context_object_name = 'tipos'
    paginate_by = 20
    
    def get_queryset(self):
        """Aplica filtros na queryset baseado nos parâmetros GET"""
        queryset = TipoDespesa.objects.all()
        
        # Filtro por status (ativo/inativo)
        status = self.request.GET.get('status', 'ativo')
        if status == 'ativo':
            queryset = queryset.filter(ativo=True)
        elif status == 'inativo':
            queryset = queryset.filter(ativo=False)
        # Se status='todos', não aplica filtro
        
        # Filtro por busca no nome
        busca = self.request.GET.get('busca', '').strip()
        if busca:
            queryset = queryset.filter(
                Q(nome__icontains=busca) | 
                Q(descricao__icontains=busca)
            )
        
        # Ordenação padrão por nome
        return queryset.order_by('nome')
    
    def get_context_data(self, **kwargs):
        """Adiciona dados extras ao contexto do template"""
        context = super().get_context_data(**kwargs)
        
        # Mantém os filtros no contexto para preservar no template
        context['filtro_status'] = self.request.GET.get('status', 'ativo')
        context['filtro_busca'] = self.request.GET.get('busca', '')
        
        # Estatísticas para o dashboard
        context['total_tipos'] = TipoDespesa.objects.count()
        context['tipos_ativos'] = TipoDespesa.objects.filter(ativo=True).count()
        context['tipos_inativos'] = TipoDespesa.objects.filter(ativo=False).count()
        
        return context



class TipoDespesaCreateView(CreateView):
    """
    View para criação de novos tipos de despesa
    """
    model = TipoDespesa
    form_class = TipoDespesaForm
    template_name = 'financeiro/tipodespesa/tipodespesa_form.html'
    success_url = reverse_lazy('financeiro:tipodespesa_list')
    
    def form_valid(self, form):
        """Processa o formulário válido e adiciona mensagem de sucesso"""
        messages.success(
            self.request, 
            f'Tipo de despesa "{form.instance.nome}" criado com sucesso!'
        )
        return super().form_valid(form)
    
    def form_invalid(self, form):
        """Adiciona mensagem de erro quando o formulário é inválido"""
        messages.error(
            self.request, 
            'Erro ao criar tipo de despesa. Verifique os dados informados.'
        )
        return super().form_invalid(form)
    
    def get_context_data(self, **kwargs):
        """Adiciona título da página ao contexto"""
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Novo Tipo de Despesa'
        context['botao_submit'] = 'Criar Tipo'
        return context



class TipoDespesaUpdateView(UpdateView):
    """
    View para edição de tipos de despesa existentes
    """
    model = TipoDespesa
    form_class = TipoDespesaForm
    template_name = 'financeiro/tipodespesa/tipodespesa_form.html'
    success_url = reverse_lazy('financeiro:tipodespesa_list')
    
    def form_valid(self, form):
        """Processa o formulário válido e adiciona mensagem de sucesso"""
        messages.success(
            self.request, 
            f'Tipo de despesa "{form.instance.nome}" atualizado com sucesso!'
        )
        return super().form_valid(form)
    
    def form_invalid(self, form):
        """Adiciona mensagem de erro quando o formulário é inválido"""
        messages.error(
            self.request, 
            'Erro ao atualizar tipo de despesa. Verifique os dados informados.'
        )
        return super().form_invalid(form)
    
    def get_context_data(self, **kwargs):
        """Adiciona título da página ao contexto"""
        context = super().get_context_data(**kwargs)
        context['titulo'] = f'Editar - {self.object.nome}'
        context['botao_submit'] = 'Salvar Alterações'
        
        # Verificar se o tipo está sendo usado
        context['em_uso'] = hasattr(self.object, 'despesas') and self.object.despesas.exists()
        
        return context


@method_decorator
class TipoDespesaDetailView(DetailView):
    """
    View para visualização detalhada de um tipo de despesa
    """
    model = TipoDespesa
    template_name = 'financeiro/tipodespesa/tipodespesa_detail.html'
    context_object_name = 'tipo'
    
    def get_context_data(self, **kwargs):
        """Adiciona estatísticas e despesas relacionadas ao contexto"""
        context = super().get_context_data(**kwargs)
        
        # Estatísticas do tipo (verificar se o related_name existe)
        if hasattr(self.object, 'despesas'):
            despesas_relacionadas = self.object.despesas.all()
            context['total_despesas'] = despesas_relacionadas.count()
            context['despesas_ativas'] = despesas_relacionadas.filter(is_ativa=True).count()
            # Últimas despesas (máximo 10)
            context['ultimas_despesas'] = despesas_relacionadas.order_by('-data_cadastro')[:10]
        else:
            context['total_despesas'] = 0
            context['despesas_ativas'] = 0
            context['ultimas_despesas'] = []
        
        return context



def tipodespesa_toggle_status(request, pk):
    """
    View para alternar o status ativo/inativo de um tipo de despesa
    """
    tipo = get_object_or_404(TipoDespesa, pk=pk)
    
    # Se está ativo, verifica se pode ser inativado
    if tipo.ativo and hasattr(tipo, 'despesas'):
        despesas_ativas = tipo.despesas.filter(is_ativa=True).count()
        
        if despesas_ativas > 0:
            message = f'Não é possível inativar. Existem {despesas_ativas} despesas ativas usando este tipo.'
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': message
                })
            else:
                messages.error(request, message)
                return redirect('financeiro:tipodespesa_list')
    
    # Alterna o status
    tipo.ativo = not tipo.ativo
    tipo.save()
    
    status_texto = 'ativado' if tipo.ativo else 'inativado'
    message = f'Tipo "{tipo.nome}" {status_texto} com sucesso!'
    
    # Resposta para AJAX
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': message,
            'novo_status': tipo.ativo,
            'status_display': 'Ativo' if tipo.ativo else 'Inativo'
        })
    
    # Resposta para requisição normal
    messages.success(request, message)
    return redirect('financeiro:tipodespesa_list')



def tipodespesa_check_uso(request, pk):
    """
    View AJAX para verificar se um tipo de despesa está sendo usado
    """
    tipo = get_object_or_404(TipoDespesa, pk=pk)
    
    if hasattr(tipo, 'despesas'):
        despesas_total = tipo.despesas.count()
        despesas_ativas = tipo.despesas.filter(is_ativa=True).count()
    else:
        despesas_total = 0
        despesas_ativas = 0
    
    return JsonResponse({
        'em_uso': despesas_total > 0,
        'despesas_total': despesas_total,
        'despesas_ativas': despesas_ativas,
        'pode_inativar': despesas_ativas == 0
    })