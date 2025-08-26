from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import logout
from django.contrib import messages
from django.http import JsonResponse
from django.apps import apps


def home(request):
    """
    View para a página inicial
    """
    return render(request, 'base/home.html')


def logout_view(request):
    """
    View para logout do usuário
    """
    logout(request)
    return redirect('home')


def buscar(request):
    """
    View para página de busca geral
    """
    context = {
        'titulo': 'Buscar',
        'pagina_busca': True
    }
    return render(request, 'base/base.html', context)


def sucesso(request):
    """
    View para página de sucesso genérica
    """
    mensagem = request.GET.get('mensagem', 'Operação realizada com sucesso!')
    context = {
        'titulo': 'Sucesso',
        'mensagem': mensagem,
        'pagina_sucesso': True
    }
    return render(request, 'base/base.html', context)


def autocomplete_field(request, model_name, field_name):
    """
    View AJAX para autocomplete de campos
    """
    query = request.GET.get('q', '')
    
    try:
        Model = apps.get_model('core', model_name)
        suggestions = Model.objects.filter(
            **{f"{field_name}__icontains": query}
        ).values_list(field_name, flat=True).distinct()[:10]
        
        return JsonResponse(list(suggestions), safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


def nacionalidade_autocomplete(request):
    """
    View AJAX para autocomplete de nacionalidade
    """
    from core.models import Cliente
    
    query = request.GET.get('q', '')
    suggestions = Cliente.objects.filter(
        nacionalidade__icontains=query
    ).values_list('nacionalidade', flat=True).distinct()[:10]
    
    return JsonResponse(list(suggestions), safe=False)


def confirmar_exclusao(request, model_name, id):
    """
    View genérica para confirmação de exclusão
    """
    from core.models import Cliente, Imovel, Contrato
    
    models = {
        'cliente': Cliente,
        'imovel': Imovel,
        'contrato': Contrato,
    }
    
    if model_name not in models:
        messages.error(request, "Modelo inválido.")
        return redirect('home')
    
    model_class = models[model_name]
    obj = get_object_or_404(model_class, id=id)
    
    if request.method == 'POST':
        obj.delete()
        messages.success(request, f"{model_name.capitalize()} excluído(a) com sucesso.")
        return redirect(f'listar_{model_name}s')
    
    context = {
        'titulo': 'Confirmar Exclusão',
        'model_name': model_name,
        'obj': obj,
        'plural_name': f"{model_name}s",
        'pagina_confirmacao': True
    }
    return render(request, 'base/base.html', context)