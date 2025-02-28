from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth import logout
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .forms import ClienteForm, ImovelForm, ContratoForm
from .models import Cliente, Imovel, Contrato, Cobranca
from django.views.generic import ListView
from django.db.models import Q
from django.contrib import messages
from datetime import date
from .forms import GerarCobrancasForm
import pandas as pd
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .utils import atualizar_indices_inflacao
from decimal import Decimal
from dateutil.relativedelta import relativedelta
from bson.decimal128 import Decimal128
from django.utils import timezone

@csrf_exempt
def atualizar_indices_view(request):
    if request.method == 'POST':
        try:
            atualizar_indices_inflacao()
            return JsonResponse({"status": "success", "message": "Índices atualizados com sucesso."})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)
    else:
        return JsonResponse({"status": "error", "message": "Método não permitido."}, status=405)

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

def dashboard(request, contrato_id):
    # Obter o contrato pelo ID
    contrato = get_object_or_404(Contrato, id=contrato_id)
    
    # Resto do código que utiliza o contrato...
    
    return render(request, 'imoveis/dashboard.html', {
        'contrato': contrato,
        # outras variáveis de contexto...
    })

def marcar_repasse(request, cobranca_id):
    if request.method == 'POST':
        cobranca = get_object_or_404(Cobranca, id=cobranca_id)
        data_repasse = request.POST.get('data_repasse')
        
        if data_repasse:
            try:
                # Converter a string em data
                data_repasse_dt = datetime.strptime(data_repasse, '%Y-%m-%d').date()
                
                # Atualizar a cobrança
                cobranca.data_repasse = data_repasse_dt
                cobranca.status = 'REPASSADO'  # Atualizar o status
                cobranca.save()
                
                messages.success(request, f'Repasse da cobrança {cobranca.id} marcado para {data_repasse_dt.strftime("%d/%m/%Y")}.')
            except ValueError:
                messages.error(request, 'Formato de data inválido.')
        else:
            messages.error(request, 'Data de repasse não fornecida.')
    
    # Redirecionar de volta para o dashboard com os mesmos filtros
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))

def editar_contrato(request, contrato_id):
    contrato = Contrato.objects.get(id=contrato_id)
    return render(request, 'editar_contrato.html', {'contrato': contrato})

def excluir_contrato(request, contrato_id):
    contrato = Contrato.objects.get(id=contrato_id)
    contrato.delete()
    return redirect('listar_contratos')

def gerar_cobrancas(request):
    if request.method == 'POST':
        mes = int(request.POST.get('mes'))
        ano = int(request.POST.get('ano'))

        # Validar mês e ano
        if not (1 <= mes <= 12):
            messages.error(request, 'Mês inválido. Deve estar entre 1 e 12.')
            return redirect('listar_contratos')
        if ano < 2000 or ano > 3000:
            messages.error(request, 'Ano inválido.')
            return redirect('listar_contratos')

        data_inicio_mes = date(ano, mes, 1)
        data_fim_mes = data_inicio_mes + relativedelta(months=1) - relativedelta(days=1)

        contratos = Contrato.objects.filter(
            data_inicio__lte=data_fim_mes,
            data_fim__gte=data_inicio_mes
        )

        for contrato in contratos:
            def convert_decimal(value):
                return value.to_decimal() if isinstance(value, Decimal128) else Decimal(value)

            if contrato.tipo_pagamento == 'Despesas_Separadas':
                valor_total = (
                    convert_decimal(contrato.valor_aluguel) +
                    convert_decimal(contrato.valor_condominio) +
                    convert_decimal(contrato.valor_iptu) +
                    convert_decimal(contrato.valor_outros)
                )
            else:
                valor_total = convert_decimal(contrato.valor_pacote)

            data_vencimento = data_inicio_mes.replace(day=contrato.dia_pagamento)

            cobranca_existente = Cobranca.objects.filter(
                contrato=contrato,
                data_vencimento__year=ano,
                data_vencimento__month=mes
            ).first()

            if not cobranca_existente:
                CobrancaAluguel.objects.create(
                    contrato=contrato,
                    valor_total=valor_total,
                    data_vencimento=data_vencimento,
                    status_pagamento='PENDENTE',
                    status_repasse='PENDENTE'
                )

        messages.success(request, 'Cobranças geradas com sucesso.')
        return redirect('listar_contratos')

class ListarContratosView(ListView):
    model = Contrato
    template_name = 'imoveis/listar_contratos.html'
    paginate_by = 10
    context_object_name = 'page_obj'

    def get_queryset(self):
        queryset = Contrato.objects.prefetch_related('proprietario', 'inquilino', 'imovel').all()

        # Aplicar filtros
        filtro_tipo = self.request.GET.get('filtro_tipo')
        buscar = self.request.GET.get('buscar')

        if filtro_tipo == 'ativo':
            queryset = queryset.filter(ativo=True)
        elif filtro_tipo == 'inativo':
            queryset = queryset.filter(ativo=False)

        if buscar:
            queryset = queryset.filter(
                Q(proprietario__nome__icontains=buscar) |
                Q(inquilino__nome__icontains=buscar) |
                Q(imovel__endereco__icontains=buscar)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obter data atual para pré-selecionar o mês e ano no formulário
        hoje = timezone.now().date()
        mes_atual = hoje.month
        ano_atual = hoje.year
        
        # Adicionar informações para o formulário de geração de cobranças
        context['form'] = GerarCobrancasForm(initial={
            'mes': mes_atual,
            'ano': ano_atual
        })
        
        # Adicionar opções de meses e anos para o formulário
        context['meses'] = [
            (1, 'Janeiro'), (2, 'Fevereiro'), (3, 'Março'), 
            (4, 'Abril'), (5, 'Maio'), (6, 'Junho'),
            (7, 'Julho'), (8, 'Agosto'), (9, 'Setembro'),
            (10, 'Outubro'), (11, 'Novembro'), (12, 'Dezembro')
        ]
        
        context['range_anos'] = range(ano_atual - 2, ano_atual + 3)  # 2 anos atrás e 3 anos à frente
        context['mes_selecionado'] = mes_atual
        context['ano_selecionado'] = ano_atual
        
        print("Contexto:", context)  # Log para depuração
        return context
    