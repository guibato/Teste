from django.shortcuts import render, redirect
from django.contrib import messages
from ..forms import ClienteForm
from ..models import Cliente
from django.shortcuts import get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse

def cadastrar_cliente(request):
    """
    View para cadastrar um novo cliente.
    """
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            cliente = form.save(commit=False)
            cliente.save()
            messages.success(request, f'Cliente {cliente.nome} cadastrado com sucesso!')
            return redirect('listar_clientes')
        else:
            messages.error(request, 'Erro ao cadastrar cliente. Verifique os dados informados.')
    else:
        form = ClienteForm()

    return render(request, 'clientes/cadastrar_cliente.html', {'form': form})

def listar_clientes(request):
    """
    View para listar todos os clientes com paginação.
    """
    query = request.GET.get('q', '')

    if query:
        clientes_list = Cliente.objects.filter(nome__icontains=query)
    else:
        clientes_list = Cliente.objects.all().order_by('nome')

    paginator = Paginator(clientes_list, 10)  # 10 clientes por página
    page = request.GET.get('page')

    try:
        clientes = paginator.page(page)
    except PageNotAnInteger:
        clientes = paginator.page(1)
    except EmptyPage:
        clientes = paginator.page(paginator.num_pages)

    return render(request, 'clientes/listar_clientes.html', {'clientes': clientes, 'query': query})

def editar_cliente(request, id):
    """
    View para editar um cliente existente.
    """
    cliente = get_object_or_404(Cliente, id=id)

    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            messages.success(request, f'Cliente {cliente.nome} atualizado com sucesso!')
            return redirect('listar_clientes')
        else:
            messages.error(request, 'Erro ao atualizar cliente. Verifique os dados informados.')
    else:
        form = ClienteForm(instance=cliente)

    return render(request, 'clientes/editar_cliente.html', {'form': form, 'cliente': cliente})

def nacionalidade_autocomplete(request):
    """
    View para autocompletar o campo de nacionalidade.
    """
    query = request.GET.get('q', '')
    suggestions = Cliente.objects.filter(
        nacionalidade__icontains=query
    ).values_list('nacionalidade', flat=True).distinct()
    return JsonResponse(list(suggestions), safe=False)
