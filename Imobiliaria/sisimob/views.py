from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth import logout
from django.core.paginator import Paginator
from .forms import ClienteForm, ImovelForm, ContratoForm
from .models import Cliente, Imovel, Contrato

def home(request):
    return render(request, 'imoveis/home.html')

def logout_view(request):
    logout(request)
    return redirect('home')

def buscar(request):
    return render(request, 'imoveis/buscar.html')

def cadastrar_cliente(request):
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('listar_clientes')  # Redireciona para a lista de clientes após o cadastro
    else:
        form = ClienteForm()

    # Passa o contexto com o título e o texto do botão
    return render(request, 'imoveis/cadastro_cliente.html', {
        'form': form,
        'titulo': 'Cadastro de Cliente',
        'botao_acao': 'Cadastrar'
    })

def cadastrar_imovel(request):
    if request.method == 'POST':
        form = ImovelForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('listar_imoveis')  # Redireciona para a lista de imóveis após o cadastro
    else:
        form = ImovelForm()  # Instancia o formulário vazio para GET

    # Passa o formulário para o template
    return render(request, 'imoveis/cadastro_imovel.html', {'form': form})

def cadastrar_contrato(request):
    if request.method == 'POST':
        form = ContratoForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('listar_contratos')
        else:
            print(form.errors)  # <<< Isso imprime os erros no terminal
    else:
        form = ContratoForm()

    return render(request, 'imoveis/cadastro_contrato.html', {'form': form})

def listar_clientes(request):
    clientes = Cliente.objects.all()
    paginator = Paginator(clientes, 10)  # Exibe 10 clientes por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'imoveis/listar_clientes.html', {'page_obj': page_obj})

def listar_imoveis(request):
    imoveis = Imovel.objects.all()  # Recupera todos os imóveis
    paginator = Paginator(imoveis, 10)  # Exibe 10 imóveis por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'imoveis/listar_imoveis.html', {'page_obj': page_obj})

def listar_contratos(request):
    return render(request, 'imoveis/listar_contratos.html')

def editar_cliente(request, id):
    cliente = get_object_or_404(Cliente, id=id)  # Recupera o cliente pelo ID
    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            return redirect('listar_clientes')  # Redireciona para a lista de clientes após salvar
    else:
        form = ClienteForm(instance=cliente)

    # Passa o contexto com o título e o texto do botão
    return render(request, 'imoveis/cadastro_cliente.html', {
        'form': form,
        'titulo': 'Editar Cliente',
        'botao_acao': 'Salvar'
    })

def confirmar_exclusao(request, model_name, id):
    # Mapeia o nome do modelo para a classe correspondente
    models = {
        'cliente': Cliente,
        'imovel': Imovel,
        'contrato': Contrato,
    }

    # Verifica se o modelo existe no mapeamento
    if model_name not in models:
        messages.error(request, "Modelo inválido.")
        return redirect('home')

    # Obtém o modelo e o objeto correspondente ao ID
    model_class = models[model_name]
    obj = get_object_or_404(model_class, id=id)

    if request.method == 'POST':
        # Exclui o objeto e redireciona para a lista correspondente
        obj.delete()
        messages.success(request, f"{model_name.capitalize()} excluído com sucesso.")
        return redirect(f'listar_{model_name}s')  # Redireciona para a lista de clientes, imóveis ou contratos

    # Renderiza a página de confirmação de exclusão
    return render(request, 'imoveis/confirmar_exclusao.html', {
        'obj': obj,
        'model_name': model_name,
    })

def editar_imovel(request, id):
    imovel = get_object_or_404(Imovel, id=id)  # Recupera o imóvel pelo ID
    if request.method == 'POST':
        form = ImovelForm(request.POST, instance=imovel)
        if form.is_valid():
            form.save()
            return redirect('listar_imoveis')  # Redireciona para a lista de imóveis após salvar
    else:
        form = ImovelForm(instance=imovel)

    return render(request, 'imoveis/cadastro_imovel.html', {
        'form': form,
        'titulo': 'Editar Imóvel',
        'botao_acao': 'Salvar'
    })

def limpar_valor(valor):
    return float(valor.replace("R$", "").replace("%", "").replace(".", "").replace(",", ".").strip())

preco = limpar_valor("R$ 1.500,75")  # 1500.75
taxa = limpar_valor("10,5%")  # 10.5

def sucesso(request):
    return render(request, 'sucesso.html', {'mensagem': 'Contrato cadastrado com sucesso!'})

from django.views.generic import ListView
from django.db.models import Q
from .models import Contrato

class ListarContratosView(ListView):
    model = Contrato
    template_name = 'imoveis/listar_contratos.html'
    paginate_by = 10
    context_object_name = 'page_obj'

    def get_queryset(self):
        queryset = Contrato.objects.select_related(
            'proprietario', 'inquilino', 'imovel'
        ).all()

        # Filtro por status
        filtro_tipo = self.request.GET.get('filtro_tipo')
        if filtro_tipo == 'ativo':
            queryset = queryset.filter(ativo=True)
        elif filtro_tipo == 'inativo':
            queryset = queryset.filter(ativo=False)

        # Busca por nome ou endereço
        buscar = self.request.GET.get('buscar')
        if buscar:
            queryset = queryset.filter(
                Q(proprietario__nome__icontains=buscar) |
                Q(inquilino__nome__icontains=buscar) |
                Q(imovel__endereco__icontains=buscar)
            )

        return queryset

from django.shortcuts import redirect
from django.contrib import messages
from .models import Contrato, Cobranca
from datetime import date

def gerar_cobrancas(request):
    if request.method == 'POST':
        # Obter contratos ativos
        contratos_ativos = Contrato.objects.filter(ativo=True).select_related(
            'proprietario', 'inquilino', 'imovel'
        )

        cobrancas_geradas = 0
        for contrato in contratos_ativos:
            try:
                # Gerar número de referência (ex: 0324 para março/2024)
                mes = date.today().month
                ano = date.today().year
                num_referencia = f"{mes:02d}{ano % 100:02d}"

                # Determinar o valor da cobrança
                if contrato.tipo_pagamento == 'Pacote':
                    valor_cobranca = contrato.valor_pacote
                else:  # Despesas_Separadas
                    valor_cobranca = (
                        contrato.valor_aluguel +
                        contrato.valor_condominio +
                        contrato.valor_iptu +
                        contrato.valor_outros
                    )

                # Criar ou atualizar a cobrança
                Cobranca.objects.update_or_create(
                    contrato=contrato,
                    vencimento=date(ano, mes, contrato.dia_pagamento),
                    defaults={
                        'valor': valor_cobranca,
                        'numero_referencia': num_referencia,
                        'status': 'PENDENTE'
                    }
                )
                cobrancas_geradas += 1

            except Exception as e:
                messages.error(
                    request,
                    f'Erro ao gerar cobrança para contrato {contrato.id}: {str(e)}'
                )
                continue

        if cobrancas_geradas > 0:
            messages.success(request, f'{cobrancas_geradas} cobranças geradas com sucesso!')
        else:
            messages.warning(request, 'Nenhuma nova cobrança foi gerada.')

    return redirect('listar_contratos')

def dashboard(request, contrato_id):
    contrato = Contrato.objects.get(id=contrato_id)
    return render(request, 'dashboard.html', {'contrato': contrato})

# Editar Contrato
def editar_contrato(request, contrato_id):
    contrato = Contrato.objects.get(id=contrato_id)
    return render(request, 'editar_contrato.html', {'contrato': contrato})

# Excluir Contrato
def excluir_contrato(request, contrato_id):
    contrato = Contrato.objects.get(id=contrato_id)
    contrato.delete()
    return redirect('listar_contratos')
