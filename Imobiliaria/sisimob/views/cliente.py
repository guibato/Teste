from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
import traceback

from sisimob.models import Cliente
from sisimob.forms import ClienteForm, ClienteFiltroForm, ClienteBuscaForm




def detalhes_cliente(request, id):
    """
    View para exibir detalhes completos de um cliente
    """
    cliente = get_object_or_404(Cliente, id=id)
    
    # Buscar contratos relacionados
    contratos_proprietario = cliente.contratos_proprietario.all()
    contratos_inquilino = cliente.contratos_inquilino.all()
    contratos_fiador = cliente.contratos_fiador.all()
    
    context = {
        'cliente': cliente,
        'contratos_proprietario': contratos_proprietario,
        'contratos_inquilino': contratos_inquilino,
        'contratos_fiador': contratos_fiador,
    }
    
    return render(request, 'clientes/detalhes_cliente.html', context)


class ClienteListView(ListView):
    """
    Class-based view para listagem de clientes
    """
    model = Cliente
    template_name = 'clientes/listar_clientes.html'
    context_object_name = 'clientes'
    paginate_by = 15
    ordering = ['nome']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Aplicar filtros da URL
        nome = self.request.GET.get('nome')
        tipo = self.request.GET.get('tipo')
        tipo_pessoa = self.request.GET.get('tipo_pessoa')
        cidade = self.request.GET.get('cidade')
        busca = self.request.GET.get('busca')
        
        if nome:
            queryset = queryset.filter(nome__icontains=nome)
        if tipo:
            queryset = queryset.filter(tipo=tipo)
        if tipo_pessoa:
            queryset = queryset.filter(tipo_pessoa=tipo_pessoa)
        if cidade:
            queryset = queryset.filter(cidade__icontains=cidade)
        if busca:
            queryset = queryset.filter(
                Q(nome__icontains=busca) |
                Q(email__icontains=busca) |
                Q(CPF__icontains=busca) |
                Q(cnpj__icontains=busca) |
                Q(razao_social__icontains=busca)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filtro_form'] = ClienteFiltroForm(self.request.GET)
        context['busca_form'] = ClienteBuscaForm(self.request.GET)
        context['total_clientes'] = self.get_queryset().count()
        return context


class ClienteCreateView(CreateView):
    """
    Class-based view para criação de clientes
    """
    model = Cliente
    form_class = ClienteForm
    template_name = 'clientes/cadastro_cliente.html'
    success_url = reverse_lazy('listar_clientes')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Integração com Asaas após salvar
        try:
            resposta = cadastrar_cliente_no_asaas(self.object)
            if resposta:
                self.object.asaas_id = resposta
                self.object.save()
                messages.success(self.request, "Cliente cadastrado com sucesso!")
            else:
                messages.warning(
                    self.request, 
                    "Cliente cadastrado, mas houve erro na integração com Asaas."
                )
        except Exception as e:
            messages.error(self.request, f"Erro na integração com Asaas: {str(e)}")
        
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Cadastro de Cliente'
        context['botao_acao'] = 'Cadastrar'
        return context


class ClienteUpdateView(UpdateView):
    """
    Class-based view para edição de clientes
    """
    model = Cliente
    form_class = ClienteForm
    template_name = 'clientes/cadastro_cliente.html'
    success_url = reverse_lazy('listar_clientes')
    
    def form_valid(self, form):
        messages.success(self.request, "Cliente atualizado com sucesso!")
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Cliente'
        context['botao_acao'] = 'Salvar'
        context['cliente'] = self.object
        return context


class ClienteDeleteView(DeleteView):
    """
    Class-based view para exclusão de clientes
    """
    model = Cliente
    template_name = 'clientes/confirmar_exclusao.html'
    success_url = reverse_lazy('listar_clientes')
    
    def delete(self, request, *args, **kwargs):
        cliente = self.get_object()
        
        # Verificar se o cliente tem contratos associados
        if (cliente.contratos_proprietario.exists() or 
            cliente.contratos_inquilino.exists() or 
            cliente.contratos_fiador.exists()):
            messages.error(
                request, 
                "Não é possível excluir este cliente pois ele possui contratos associados."
            )
            return redirect('listar_clientes')
        
        nome_cliente = cliente.nome
        response = super().delete(request, *args, **kwargs)
        messages.success(request, f"Cliente {nome_cliente} excluído com sucesso.")
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['objeto_tipo'] = 'Cliente'
        return context