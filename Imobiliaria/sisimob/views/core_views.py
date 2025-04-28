from django.shortcuts import render, redirect
from django.contrib.auth import logout
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.apps import apps
import threading

from ..utils import atualizar_indices_inflacao

def home(request):
    """
    View para a página inicial.
    """
    return render(request, 'imoveis/home.html')

def logout_view(request):
    """
    View para realizar o logout do usuário.
    """
    logout(request)
    return redirect('home')

def buscar(request):
    """
    View para a página de busca.
    """
    return render(request, 'imoveis/buscar.html')

def sucesso(request):
    """
    View para a página de sucesso após operações.
    """
    return render(request, 'sucesso.html', {'mensagem': 'Operação realizada com sucesso!'})

def autocomplete_field(request, model_name, field_name):
    """
    View genérica para autocompletar campos de formulários.
    """
    query = request.GET.get('q', '')
    try:
        Model = apps.get_model('sisimob', model_name)
        suggestions = Model.objects.filter(
            **{f"{field_name}__icontains": query}
        ).values_list(field_name, flat=True).distinct()
        return JsonResponse(list(suggestions), safe=False)
    except LookupError:
        return JsonResponse([], safe=False)

def confirmar_exclusao(request, model_name, id):
    """
    View genérica para confirmar exclusão de objetos.
    """
    from ..models import Cliente, Imovel, Contrato

    models = {
        'cliente': Cliente,
        'imovel': Imovel,
        'contrato': Contrato,
    }

    if model_name not in models:
        return redirect('home')

    model_class = models[model_name]
    obj = model_class.objects.get(id=id)

    if request.method == 'POST':
        obj.delete()
        return redirect(f'listar_{model_name}s')

    return render(request, 'imoveis/confirmar_exclusao.html', {
        'model_name': model_name,
        'obj': obj,
        'plural_name': f"{model_name}s",
    })

@csrf_exempt
def atualizar_indices_view(request):
    """
    View para atualizar índices de inflação.
    """
    if request.method == "POST":
        def atualizar():
            atualizar_indices_inflacao()

        # Executa a função em uma thread para não travar a requisição
        thread = threading.Thread(target=atualizar)
        thread.start()

        return JsonResponse({"status": "Atualização iniciada"})

    return JsonResponse({"error": "Método inválido"}, status=400)

def extrato(request):
    """
    View para a página de extrato.
    """
    # Implementar lógica de extrato
    return render(request, 'imoveis/extrato.html')

def extrato_repasses_pdf(request, proprietario_id):
    """
    View para gerar PDF de extrato de repasses.
    """
    from ..models import Cliente
    from ..gerar_extrato_repasses_pdf import gerar_extrato_repasses_pdf

    proprietario = Cliente.objects.get(id=proprietario_id)
    response = gerar_extrato_repasses_pdf(proprietario)
    return response
