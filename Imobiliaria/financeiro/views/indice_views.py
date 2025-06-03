# financeiro/views/indice_views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages

from django.views.generic import ListView, CreateView, UpdateView
from django.urls import reverse_lazy
from django.db.models import Q
from datetime import datetime

from ..models.indice import IndiceInflacao
from financeiro.forms.indice_forms import IndiceInflacaoForm
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from financeiro.services.indice_service import IndiceAPIService
import json

class IndiceListView(ListView):
    model = IndiceInflacao
    template_name = 'financeiro/indices/indices_list.html'
    context_object_name = 'indices'
    paginate_by = 50

    def get_queryset(self):
        queryset = IndiceInflacao.objects.all()
        
        # Filtros básicos
        tipo = self.request.GET.get('tipo')
        ano = self.request.GET.get('ano')
        
        if tipo:
            queryset = queryset.filter(tipo=tipo)
        
        if ano:
            try:
                ano_int = int(ano)
                queryset = queryset.filter(data_referencia__year=ano_int)
            except ValueError:
                pass
        
        return queryset.order_by('-data_referencia')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tipos'] = IndiceInflacao.TIPO_CHOICES
        context['anos'] = range(2020, datetime.now().year + 2)
        context['filters'] = {
            'tipo': self.request.GET.get('tipo', ''),
            'ano': self.request.GET.get('ano', ''),
        }
        return context


class IndiceCreateView(CreateView):
    model = IndiceInflacao
    form_class = IndiceInflacaoForm
    template_name = 'financeiro/indices/indices_form.html'
    success_url = reverse_lazy('financeiro:indice_list')

    def form_valid(self, form):
        messages.success(self.request, 'Índice cadastrado com sucesso!')
        return super().form_valid(form)


class IndiceUpdateView(UpdateView):
    model = IndiceInflacao
    form_class = IndiceInflacaoForm
    template_name = 'financeiro/indices/indices_form.html'
    success_url = reverse_lazy('financeiro:indice_list')

    def form_valid(self, form):
        messages.success(self.request, 'Índice atualizado com sucesso!')
        return super().form_valid(form)
    
def atualizar_indices_api(request):
    """View para atualizar índices via AJAX"""
    try:
        data = json.loads(request.body)
        tipo = data.get('tipo')
        
        service = IndiceAPIService()
        
        if tipo and tipo in ['IPCA', 'IGPM']:
            resultado = service.atualizar_indice(tipo)
            return JsonResponse({
                'sucesso': True,
                'mensagem': f'{tipo} atualizado com sucesso',
                'dados': resultado
            })
        else:
            resultados = service.atualizar_todos_indices()
            total_criados = sum(r.get('criados', 0) for r in resultados.values() if r.get('sucesso'))
            total_atualizados = sum(r.get('atualizados', 0) for r in resultados.values() if r.get('sucesso'))
            
            return JsonResponse({
                'sucesso': True,
                'mensagem': f'Índices atualizados: {total_criados} criados, {total_atualizados} atualizados',
                'dados': resultados
            })
            
    except Exception as e:
        return JsonResponse({
            'sucesso': False,
            'mensagem': f'Erro na atualização: {str(e)}'
        }, status=500)