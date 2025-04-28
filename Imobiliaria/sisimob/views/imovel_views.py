from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from ..forms import ImovelForm
from ..models import Imovel

def cadastrar_imovel(request):
    """
    View para cadastrar um novo imóvel.
    """
    if request.method == 'POST':
        form = ImovelForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Imóvel cadastrado com sucesso!")
            return redirect('listar_imoveis')
        else:
            messages.error(request, "Por favor, corrija os erros no formulário.")
    else:
        form = ImovelForm()
    return render(request, 'imoveis/cadastro_imovel.html', {'form': form, 'titulo': 'Cadastro de Imóvel', 'botao_acao': 'Cadastrar'})

def listar_imoveis(request):
    """
    View para listar todos os imóveis com paginação.
    """
    query = request.GET.get('q', '')

    if query:
        # Assuming you want to search by address
        imoveis_list = Imovel.objects.filter(endereco__icontains=query)
    else:
        imoveis_list = Imovel.objects.all().order_by('endereco')

    paginator = Paginator(imoveis_list, 10)  # 10 imóveis por página
    page = request.GET.get('page')

    try:
        imoveis = paginator.page(page)
    except PageNotAnInteger:
        imoveis = paginator.page(1)
    except EmptyPage:
        imoveis = paginator.page(paginator.num_pages)

    return render(request, 'imoveis/listar_imoveis.html', {'imoveis': imoveis, 'query': query})

def editar_imovel(request, id):
    """
    View para editar um imóvel existente.
    """
    imovel = get_object_or_404(Imovel, id=id)
    if request.method == 'POST':
        form = ImovelForm(request.POST, instance=imovel)
        if form.is_valid():
            form.save()
            messages.success(request, "Imóvel atualizado com sucesso!")
            return redirect('listar_imoveis')
        else:
            messages.error(request, "Por favor, corrija os erros no formulário.")
    else:
        form = ImovelForm(instance=imovel)
    return render(request, 'imoveis/cadastro_imovel.html', {
        'form': form,
        'imovel': imovel,
        'titulo': 'Editar Imóvel',
        'botao_acao': 'Salvar'
    })
