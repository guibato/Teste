from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy

from core.models import Imovel
from core.forms import ImovelForm, ImovelFiltroForm, ImovelBuscaForm

def detalhes_imovel(request, id):
    """
    View para exibir detalhes completos de um imóvel
    """
    imovel = get_object_or_404(Imovel, id=id)
    
    # Buscar contratos relacionados
    contratos = imovel.contratos_imovel.all().order_by('-data_inicio')
    contrato_ativo = imovel.get_contrato_atual()
    
    context = {
        'imovel': imovel,
        'contratos': contratos,
        'contrato_ativo': contrato_ativo,
        'status_ocupacao': imovel.status_ocupacao,
        'status_ocupacao_display': imovel.status_ocupacao_display,
    }
    
    return render(request, 'imoveis/detalhes_imovel.html', context)


class ImovelListView(ListView):
    """
    Class-based view para listagem de imóveis
    """
    model = Imovel
    template_name = 'imoveis/listar_imoveis.html'
    context_object_name = 'imoveis'
    paginate_by = 15
    ordering = ['endereco', 'numero']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Aplicar filtros da URL
        endereco = self.request.GET.get('endereco')
        bairro = self.request.GET.get('bairro')
        cidade = self.request.GET.get('cidade')
        estado = self.request.GET.get('estado')
        busca = self.request.GET.get('busca')
        
        if endereco:
            queryset = queryset.filter(endereco__icontains=endereco)
        if bairro:
            queryset = queryset.filter(bairro__icontains=bairro)
        if cidade:
            queryset = queryset.filter(cidade__icontains=cidade)
        if estado:
            queryset = queryset.filter(estado__icontains=estado)
        if busca:
            queryset = queryset.filter(
                Q(endereco__icontains=busca) |
                Q(bairro__icontains=busca) |
                Q(cidade__icontains=busca) |
                Q(complemento__icontains=busca) |
                Q(numero__icontains=busca)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filtro_form'] = ImovelFiltroForm(self.request.GET)
        context['busca_form'] = ImovelBuscaForm(self.request.GET)
        context['total_imoveis'] = self.get_queryset().count()
        return context


class ImovelCreateView(CreateView):
    """
    Class-based view para criação de imóveis
    """
    model = Imovel
    form_class = ImovelForm
    template_name = 'imoveis/cadastro_imovel.html'
    success_url = reverse_lazy('listar_imoveis')
    
    def form_valid(self, form):
        messages.success(self.request, "Imóvel cadastrado com sucesso!")
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Cadastro de Imóvel'
        context['botao_acao'] = 'Cadastrar'
        return context


class ImovelUpdateView(UpdateView):
    """
    Class-based view para edição de imóveis
    """
    model = Imovel
    form_class = ImovelForm
    template_name = 'imoveis/cadastro_imovel.html'
    success_url = reverse_lazy('listar_imoveis')
    
    def form_valid(self, form):
        messages.success(self.request, "Imóvel atualizado com sucesso!")
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Imóvel'
        context['botao_acao'] = 'Salvar'
        context['imovel'] = self.object
        return context


class ImovelDeleteView(DeleteView):
    """
    Class-based view para exclusão de imóveis
    """
    model = Imovel
    template_name = 'imoveis/confirmar_exclusao.html'
    success_url = reverse_lazy('listar_imoveis')
    
    def delete(self, request, *args, **kwargs):
        imovel = self.get_object()
        
        # Verificar se o imóvel tem contratos associados
        if imovel.contratos_imovel.exists():
            messages.error(
                request, 
                "Não é possível excluir este imóvel pois ele possui contratos associados."
            )
            return redirect('listar_imoveis')
        
        endereco_imovel = str(imovel)
        response = super().delete(request, *args, **kwargs)
        messages.success(request, f"Imóvel {endereco_imovel} excluído com sucesso.")
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['objeto_tipo'] = 'Imóvel'
        return context


def buscar_cep(request):
    """
    View AJAX para buscar dados do CEP via API externa
    """
    import requests
    from django.http import JsonResponse
    
    cep = request.GET.get('cep', '').replace('-', '').replace('.', '')
    
    if not cep or len(cep) != 8:
        return JsonResponse({'erro': 'CEP inválido'}, status=400)
    
    try:
        # Buscar dados do CEP via ViaCEP
        response = requests.get(f'https://viacep.com.br/ws/{cep}/json/')
        
        if response.status_code == 200:
            dados = response.json()
            
            if 'erro' not in dados:
                return JsonResponse({
                    'endereco': dados.get('logradouro', ''),
                    'bairro': dados.get('bairro', ''),
                    'cidade': dados.get('localidade', ''),
                    'estado': dados.get('uf', ''),
                    'cep': dados.get('cep', ''),
                })
            else:
                return JsonResponse({'erro': 'CEP não encontrado'}, status=404)
        else:
            return JsonResponse({'erro': 'Erro na consulta do CEP'}, status=500)
            
    except Exception as e:
        return JsonResponse({'erro': f'Erro interno: {str(e)}'}, status=500)