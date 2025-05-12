from django.shortcuts import render, get_object_or_404, redirect, reverse
from django.contrib import messages
from django.contrib.auth import logout
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .forms import ClienteForm, ImovelForm, ContratoForm, GerarCobrancasForm, CobrancaForm, DespesaForm  # Importe DespesaForm aqui
from .models import Cliente, Imovel, Contrato, Cobranca, Despesa, IndiceInflacao, MovimentoConta, LancamentoContaCorrente, LembreteEnviado
from django.views.generic import ListView
from django.db.models import Q
from datetime import date, datetime
import pandas as pd
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .utils import atualizar_indices_inflacao
from decimal import Decimal
from dateutil.relativedelta import relativedelta
from django.utils import timezone
from django.apps import apps
from .rent_calculations import calcular_aluguel_projetado
from reportlab.lib.pagesizes import letter, portrait
from reportlab.lib.units import cm, mm
from reportlab.lib.colors import black, gray, lightgrey, HexColor
from reportlab.platypus import Table, TableStyle, SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT, TA_JUSTIFY
from reportlab.pdfgen import canvas
from django.conf import settings
import os
from django.db.models import F, Sum
from PIL import Image
import io
from django.views.generic import ListView
from .models import Contrato
from datetime import timedelta
from django.db.models import Sum
from datetime import date, timedelta
from django.shortcuts import redirect, render
from django.contrib import messages
from .models import Contrato, Cobranca
from django.db.models import Sum
from datetime import date, timedelta
from datetime import date
from datetime import datetime
import threading
from sisimob.utils.integracao_asaas import cadastrar_cliente_no_asaas
from .gerar_extrato_repasses_pdf import gerar_extrato_repasses_pdf
from django.http import HttpResponse
from .utils import obter_valor_historico
from django.db.models import Q
import requests


class ContratoListView(ListView):
    model = Contrato
    paginate_by = 30  # Número de itens por página
    queryset = Contrato.objects.all().order_by('-data_inicio')  # Ordenação explícita

def autocomplete_field(request, model_name, field_name):
    query = request.GET.get('q', '')
    Model = apps.get_model('sismob', model_name)
    suggestions = Model.objects.filter(
        **{f"{field_name}__icontains": query}
    ).values_list(field_name, flat=True).distinct()
    return JsonResponse(list(suggestions), safe=False)

def nacionalidade_autocomplete(request):
    query = request.GET.get('q', '')
    suggestions = Cliente.objects.filter(
        nacionalidade__icontains=query
    ).values_list('nacionalidade', flat=True).distinct()
    return JsonResponse(list(suggestions), safe=False)

@csrf_exempt
def atualizar_indices_view(request):
    if request.method == "POST":
        def atualizar():
            atualizar_indices_inflacao()

        # Executa a função em uma thread para não travar a requisição
        thread = threading.Thread(target=atualizar)
        thread.start()
        
        return JsonResponse({"status": "Atualização iniciada"})
    
    return JsonResponse({"error": "Método inválido"}, status=400)

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
            cliente = form.save(commit=False)  # Salva o cliente sem commitar para poder atualizar o asaas_id
            cliente.save()  # Salva o cliente no banco de dados
            
            print(f"🔧 Tentando cadastrar cliente {cliente.nome} no Asaas")
            
            try:
                # Chamada para o Asaas
                resposta = cadastrar_cliente_no_asaas(cliente)
                print(f"🔧 Resposta do Asaas: {resposta}")
                
                if resposta:  # Verifica se o ID do Asaas foi retornado
                    print(f"✅ SUCESSO: Cliente {cliente.nome} cadastrado no Asaas! ID: {resposta}")
                    
                    # Atualiza o cliente com o asaas_id
                    cliente.asaas_id = resposta
                    cliente.save()
                    print(f"💾 Dados do cliente atualizados no banco de dados")
                    
                    messages.success(request, "Cliente cadastrado com sucesso!")
                else:
                    print(f"❌ ERRO: Falha ao cadastrar cliente {cliente.nome} no Asaas")
                    messages.error(request, "Falha ao cadastrar cliente no Asaas. Verifique os dados e tente novamente.")
            except Exception as e:
                print(f"❌ ERRO na integração com Asaas: {str(e)}")
                traceback.print_exc()
                messages.error(request, f"Erro ao integrar com o Asaas: {str(e)}")
            
            return redirect('listar_clientes')
        else:
            messages.error(request, "Por favor, corrija os erros no formulário.")
    else:
        form = ClienteForm()
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
            messages.success(request, "Imóvel cadastrado com sucesso!")
            return redirect('listar_imoveis')
        else:
            messages.error(request, "Por favor, corrija os erros no formulário.")
    else:
        form = ImovelForm()
    return render(request, 'imoveis/cadastro_imovel.html', {'form': form})

def cadastrar_contrato(request):
    if request.method == 'POST':
        form = ContratoForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Contrato cadastrado com sucesso!")
            return redirect('listar_contratos')
        else:
            messages.error(request, "Por favor, corrija os erros no formulário.")
    else:
        form = ContratoForm()
    return render(request, 'imoveis/cadastro_contrato.html', {'form': form})

def listar_clientes(request):
    clientes = Cliente.objects.all()
    paginator = Paginator(clientes, 10)
    page_number = request.GET.get('page')
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    return render(request, 'imoveis/listar_clientes.html', {'page_obj': page_obj})

def listar_imoveis(request):
    imoveis = Imovel.objects.all()
    paginator = Paginator(imoveis, 10)
    page_number = request.GET.get('page')
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    return render(request, 'imoveis/listar_imoveis.html', {'page_obj': page_obj})

def editar_cliente(request, id):
    cliente = get_object_or_404(Cliente, id=id)
    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            messages.success(request, "Cliente atualizado com sucesso!")
            return redirect('listar_clientes')
        else:
            messages.error(request, "Por favor, corrija os erros no formulário.")
    else:
        form = ClienteForm(instance=cliente)
    return render(request, 'imoveis/cadastro_cliente.html', {
        'form': form,
        'titulo': 'Editar Cliente',
        'botao_acao': 'Salvar'
    })

def confirmar_exclusao(request, model_name, id):
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
    return render(request, 'imoveis/confirmar_exclusao.html', {
        'model_name': model_name,
        'obj': obj,
        'plural_name': f"{model_name}s",
    })

def editar_imovel(request, id):
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
        'titulo': 'Editar Imóvel',
        'botao_acao': 'Salvar'
    })

def sucesso(request):
    return render(request, 'sucesso.html', {'mensagem': 'Contrato cadastrado com sucesso!'})


def dashboard(request, id):  # Mantenha o parâmetro como 'id'
    contrato = get_object_or_404(Contrato, id=id)
    aluguel_projetado = contrato.calcular_aluguel_projetado()
    ano_filtro = request.GET.get('ano')
    status_filtro = request.GET.get('status')
    if ano_filtro:
        cobrancas = cobrancas.filter(ano_referencia=ano_filtro)
    if status_filtro:
        cobrancas = cobrancas.filter(status=status_filtro)
    total = contrato.calcular_valor_total()
    historico_aluguel = contrato.historico_aluguel or {}
    despesas = contrato.despesas.all().order_by('data_inicio')
    despesa_form = DespesaForm()  # Inclua o DespesaForm no contexto

    total_receitas = contrato.cobrancas.filter(status='paga').aggregate(
        total=Sum('valor')
    )['total'] or 0
    
    cobrancas = Cobranca.objects.filter(contrato_id=id)

    total_despesas = Decimal('0.00')
    for cobranca in cobrancas:
        # Verifica se a cobrança está paga para calcular as despesas
        if cobranca.status == 'paga':
            valor_liquido = cobranca.valor - cobranca.valor_administracao
            total_despesas += valor_liquido
    
    saldo = total_receitas - total_despesas

    ano_filtro = request.GET.get('ano', str(date.today().year))
    status_filtro = request.GET.get('status', '')
    
    cobrancas = contrato.cobrancas.all().order_by('ano_referencia', 'mes_referencia')
    
    if ano_filtro:
        cobrancas = cobrancas.filter(ano_referencia=int(ano_filtro))
    if status_filtro:
        cobrancas = cobrancas.filter(status=status_filtro)
    
    # Gerar lista de anos disponíveis
    anos_disponiveis = contrato.cobrancas.dates('data_vencimento', 'year').distinct()

    if contrato.tipo_taxa == Contrato.valor_taxa_administracao_percentual and not contrato.valor_taxa_administracao_percentual:
        contrato.valor_taxa_administracao_percentual = Decimal('0.00')
        contrato.save()
    elif contrato.tipo_taxa == Contrato.valor_taxa_administracao_fixo and not contrato.valor_taxa_administracao_fixo:
        contrato.valor_taxa_administracao_fixo = Decimal('0.00')
        contrato.save()

    
    
    

    

    context = {
        'contrato': contrato,
        'aluguel_projetado': aluguel_projetado,
        'cobrancas': cobrancas,
        'total': total,
        'historico_aluguel': historico_aluguel,
        'despesas': despesas,
        'despesa_form': despesa_form,
        'periodo': f"{date.today().year}",
        'cobrancas': cobrancas,
        'ano_selecionado': ano_filtro,
        'status_selecionado': status_filtro,
        'anos_disponiveis': anos_disponiveis,  # Adicione o DespesaForm ao contexto
        'total_receitas': format_currency(total_receitas),
        'total_despesas': format_currency(total_despesas),
        'saldo': format_currency(saldo),
        'aluguel_projetado': format_currency(aluguel_projetado),
        'total_receitas': format_currency(total_receitas),
        'total_despesas': format_currency(total_despesas),
        'saldo': format_currency(saldo),
        'aluguel_projetado': format_currency(aluguel_projetado),
        'contrato.valor_caucao': format_currency(contrato.valor_caucao),
        'contrato.valor_aluguel': format_currency(contrato.valor_aluguel),
        'contrato.valor_taxa_administracao_fixo': format_currency(contrato.valor_taxa_administracao_fixo or 0),
        'contrato.valor_taxa_administracao_percentual': format_currency(contrato.valor_taxa_administracao_percentual or 0),
        'contrato': contrato,
        'aluguel_projetado': format_currency(aluguel_projetado),
        'cobrancas': cobrancas,
        'despesas': despesas,
        'total_receitas': format_currency(total_receitas),
        'total_despesas': format_currency(total_despesas),
        'saldo': format_currency(saldo),
        'contrato_valor_caucao': format_currency(contrato.valor_caucao or 0),
        'contrato_valor_aluguel': format_currency(contrato.valor_aluguel or 0),
        'contrato_valor_taxa_administracao_fixo': format_currency(contrato.valor_taxa_administracao_fixo or 0),
        'contrato_valor_taxa_administracao_percentual': format_currency(contrato.valor_taxa_administracao_percentual or 0),
        'ano_selecionado': ano_filtro,
        'status_selecionado': status_filtro,
        'anos_disponiveis': contrato.cobrancas.dates('data_vencimento', 'year').distinct(),
        


    }

    context['saldo'] = float(total_receitas) - float(total_despesas)
    context['saldo_positivo'] = context['saldo'] >= 0
    
    return render(request, 'imoveis/dashboard.html', context)

def listar_indices_inflacao(request):
    indices = IndiceInflacao.objects.all().order_by('data_referencia')
    data = [
        {
            'tipo': indice.tipo,
            'valor': float(indice.valor),
            'data_referencia': indice.data_referencia.strftime('%Y-%m-%d')
        }
        for indice in indices
    ]
    return JsonResponse(data, safe=False)

def marcar_repasse(request, cobranca_id):
    if request.method == 'POST':
        cobranca = get_object_or_404(Cobranca, id=cobranca_id)
        data_repasse = request.POST.get('data_repasse')
        if data_repasse:
            try:
                data_repasse_dt = datetime.strptime(data_repasse, '%Y-%m-%d').date()
                cobranca.data_repasse = data_repasse_dt
                cobranca.status_repasse = 'repassado'
                cobranca.save()
                messages.success(request, f'Repasse da cobrança {cobranca.id} marcado para {data_repasse_dt.strftime("%d/%m/%Y")}.')
            except ValueError:
                messages.error(request, 'Formato de data inválido.')
        else:
            messages.error(request, 'Data de repasse não fornecida.')
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))

def editar_contrato(request, contrato_id):
    contrato = get_object_or_404(Contrato, id=contrato_id)
    if request.method == 'POST':
        form = ContratoForm(request.POST, request.FILES, instance=contrato)
        if form.is_valid():
            form.save()
            messages.success(request, "Contrato atualizado com sucesso!")
            return redirect('listar_contratos')
        else:
            messages.error(request, "Por favor, corrija os erros no formulário.")
    else:
        form = ContratoForm(instance=contrato)
    return render(request, 'imoveis/cadastro_contrato.html', {
        'form': form,
        'titulo': 'Editar Contrato',
        'botao_acao': 'Salvar'
    })


class ListarContratosView(ListView):
    model = Contrato
    template_name = 'imoveis/listar_contratos.html'
    paginate_by = 30
    context_object_name = 'page_obj'

    def get_queryset(self):
        queryset = Contrato.objects.prefetch_related('inquilino', 'proprietario', 'imovel', 'fiador').all()
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
        hoje = timezone.now().date()
        mes_atual = hoje.month
        ano_atual = hoje.year
        context['form'] = GerarCobrancasForm(initial={
            'mes': mes_atual,
            'ano': ano_atual
        })
        context['meses'] = [
            (1, 'Janeiro'), (2, 'Fevereiro'), (3, 'Março'),
            (4, 'Abril'), (5, 'Maio'), (6, 'Junho'),
            (7, 'Julho'), (8, 'Agosto'), (9, 'Setembro'),
            (10, 'Outubro'), (11, 'Novembro'), (12, 'Dezembro')
        ]
        context['range_anos'] = range(ano_atual - 2, ano_atual + 3)
        context['mes_selecionado'] = mes_atual
        context['ano_selecionado'] = ano_atual
        return context

def registrar_pagamento(request, cobranca_id):
    cobranca = get_object_or_404(Cobranca, id=cobranca_id)
    if request.method == 'POST':
        cobranca.status = 'paga'
        cobranca.data_pagamento = timezone.now().date()
        cobranca.save()
        cobranca.status_repasse = 'pendente'
        cobranca.save()
        messages.success(request, 'Pagamento registrado!')
        return redirect('dashboard', contrato_id=cobranca.contrato.id)
    return render(request, 'imoveis/registrar_pagamento.html', {'cobranca': cobranca})

def registrar_repasse(request, cobranca_id):
    cobranca = get_object_or_404(Cobranca, id=cobranca_id)
    if request.method == 'POST':
        cobranca.status_repasse = 'repassado'
        cobranca.data_repasse = timezone.now().date()
        cobranca.save()
        messages.success(request, 'Repasse ao proprietário concluído!')
        return redirect('dashboard', contrato_id=cobranca.contrato.id)
    return render(request, 'imoveis/registrar_repasse.html', {'cobranca': cobranca})

def cobranca_update(request, pk):
    cobranca = get_object_or_404(Cobranca, pk=pk)
    if request.method == 'POST':
        form = CobrancaForm(request.POST, instance=cobranca)
        if form.is_valid():
            form.save()
            messages.success(request, "Cobrança atualizada com sucesso!")
            return redirect('dashboard', contrato_id=cobranca.contrato.id)
    else:
        form = CobrancaForm(instance=cobranca)
    return render(request, 'imoveis/cobranca_form.html', {'form': form})

def pagar_cobranca(request, pk):
    cobranca = get_object_or_404(Cobranca, pk=pk)
    if cobranca.status == 'paga':
        messages.warning(request, "Esta cobrança já foi paga.")
    else:
        cobranca.status = 'paga'
        cobranca.data_pagamento = timezone.now().date()
        cobranca.save()
        cobranca.status_repasse = 'pendente'
        cobranca.save()
        messages.success(request, "Cobrança marcada como paga com sucesso!")
    return redirect('dashboard', contrato_id=cobranca.contrato.id)

def repassar_valor(request, pk):
    cobranca = get_object_or_404(Cobranca, pk=pk)
    if cobranca.status_repasse == 'repassado':
        messages.warning(request, "Este valor já foi repassado.")
    else:
        cobranca.status_repasse = 'repassado'
        cobranca.data_repasse = timezone.now().date()
        cobranca.save()
        messages.success(request, "Valor repassado com sucesso!")
    return redirect('dashboard', contrato_id=cobranca.contrato.id)

def detalhes_contrato(request, contrato_id):
    contrato = get_object_or_404(Contrato, id=contrato_id)
    cobrancas = Cobranca.objects.filter(contrato=contrato)
    return render(request, 'imoveis/detalhes_contrato.html', {
        'contrato': contrato,
        'cobrancas': cobrancas,
    })

def gerar_recibo_pagamento(request, pk):
    cobranca = get_object_or_404(Cobranca, pk=pk)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="recibo_pagamento_{cobranca.id}.pdf"'
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    def draw_text(text, x, y, font_size=12, align='left'):
        p.setFont("Helvetica", font_size)
        if align == 'center':
            p.drawCentredString(x, y, text)
        else:
            p.drawString(x, y, text)

    try:
        logo_path = os.path.join(settings.STATIC_ROOT, 'images', 'logo2.png')
        if os.path.exists(logo_path):
            img = Image.open(logo_path)
            img_width, img_height = img.size
            max_logo_width = 100
            aspect_ratio = img_height / img_width
            logo_width = max_logo_width
            logo_height = logo_width * aspect_ratio
            x_position = (width - logo_width) / 2
            y_position = height - logo_height - 1 * cm
            p.drawImage(
                logo_path,
                x_position,
                y_position,
                width=logo_width,
                height=logo_height,
                preserveAspectRatio=True,
                mask='auto'
            )
            title_position = y_position - 1 * cm
    except Exception as e:
        print(f"Erro ao carregar logo: {e}")
        title_position = height - 3 * cm

    draw_text("Recibo de Pagamento", width / 2, title_position, font_size=16, align='center')
    draw_text(f"Cobrança #{cobranca.id}", width / 2, title_position - 1 * cm, font_size=12, align='center')

    content_start = title_position - 2.5 * cm
    draw_text("Contrato:", 50, content_start, font_size=12)
    draw_text(f"{cobranca.contrato.imovel.endereco}", 200, content_start, font_size=12)
    draw_text("Valor Pago:", 50, content_start - 1 * cm, font_size=12)
    draw_text(f"R$ {cobranca.valor:.2f}", 200, content_start - 1 * cm, font_size=12)
    draw_text("Data de Pagamento:", 50, content_start - 2 * cm, font_size=12)
    draw_text(f"{cobranca.data_pagamento.strftime('%d/%m/%Y') if cobranca.data_pagamento else 'N/A'}", 200, content_start - 2 * cm, font_size=12)
    draw_text("Status:", 50, content_start - 3 * cm, font_size=12)
    draw_text("Pago", 200, content_start - 3 * cm, font_size=12)

    draw_text("Este recibo foi gerado automaticamente pelo sistema.", 50, 50, font_size=10)
    p.showPage()
    p.save()
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    return response

def atualizar_datas_cobranca(request, pk):
    cobranca = get_object_or_404(Cobranca, id=pk)
    if request.method == 'POST':
        data_pagamento = request.POST.get('data_pagamento')
        data_repasse = request.POST.get('data_repasse')

        # Atualiza a data de pagamento
        if data_pagamento:
            try:
                cobranca.data_pagamento = datetime.strptime(data_pagamento, '%Y-%m-%d').date()
                cobranca.status = 'paga'  # Marca como paga automaticamente
                cobranca.save()
                messages.success(request, "Data de pagamento atualizada com sucesso!")
            except ValueError:
                messages.error(request, "Formato de data inválido para pagamento.")

        # Atualiza a data de repasse
        if data_repasse:
            try:
                cobranca.data_repasse = datetime.strptime(data_repasse, '%Y-%m-%d').date()
                cobranca.status_repasse = 'repassado'  # Marca como repassado automaticamente
                cobranca.save()
                messages.success(request, "Data de repasse atualizada com sucesso!")
            except ValueError:
                messages.error(request, "Formato de data inválido para repasse.")

    return redirect('dashboard', id=cobranca.contrato.id)

def gerar_extrato_rendimento(request, contrato_id):
    ano = request.GET.get('ano', str(date.today().year - 1))
    try:
        ano = int(ano)
    except ValueError:
        return HttpResponse("Ano inválido.", status=400)
    contrato = get_object_or_404(Contrato, id=contrato_id)
    cobrancas = contrato.cobrancas.filter(
        status='paga',
        ano_referencia=ano
    ).order_by('mes_referencia')
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="extrato_rendimento_contrato_{contrato.id}_ano_{ano}.pdf"'
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=portrait(letter), 
                            leftMargin=1.5*cm, rightMargin=1.5*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    elements = []

    def format_currency(value):
        if value == 0:
            return "R$ 0,00"
        return f'R$ {value:,.2f}'.replace('.', 'X').replace(',', '.').replace('X', ',')

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=14,
        alignment=TA_CENTER,
        spaceAfter=0.2*cm
    )
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Heading2'],
        fontSize=12,
        alignment=TA_CENTER,
        spaceAfter=0.5*cm,
        textColor=HexColor('#000000')
    )
    normal_style = ParagraphStyle(
        'Normal',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_LEFT,
        spaceAfter=0.2*cm,
        leftIndent=0
    )

    logo_path = os.path.join(settings.STATIC_ROOT, 'images', 'logo2.png')
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=5*cm, height=2*cm, kind='proportional')
        elements.append(logo)
    elements.append(Spacer(1, 0.3 * cm))
    elements.append(Paragraph("<b>COMPROVANTE ANUAL DE RENDIMENTOS DE ALUGUÉIS</b>", title_style))
    elements.append(Paragraph(f"<b>Ano-calendário: {ano}</b>", subtitle_style))
    elements.append(Spacer(1, 0.3 * cm))

    endereco = f"{contrato.imovel.endereco}"
    if contrato.imovel.numero:
        endereco += f", {contrato.imovel.numero}"
    if contrato.imovel.complemento:
        endereco += f" - {contrato.imovel.complemento}"
    if contrato.imovel.bairro:
        endereco += f" - {contrato.imovel.bairro}"

    imovel_data = [
        [f"<b>Número do contrato:</b> {contrato.id}", f"<b>Início do contrato:</b> {contrato.data_inicio.strftime('%d/%m/%Y')}", f"<b>Tipo do imóvel:</b> Urbano"],
    ]
    endereco_row = [[f"<b>Endereço do imóvel:</b> {endereco}"]]
    imovel_data.extend(endereco_row)
    imovel_data.append([f"<b>UF:</b> {contrato.imovel.estado}", f"<b>Município:</b> {contrato.imovel.cidade}", f"<b>CEP:</b> {contrato.imovel.cep}"])

    imovel_table = Table(
        [[Paragraph(cell, normal_style) for cell in row] for row in imovel_data], 
        colWidths=[6*cm, 6*cm, 6*cm]
    )
    imovel_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('SPAN', (0, 1), (2, 1)),
    ]))
    elements.append(imovel_table)
    elements.append(Spacer(1, 0.5 * cm))

    elements.append(Paragraph("<b>CNPJ da Administradora do imóvel (Imobiliária):</b> 55.507.744/0001-99", normal_style))
    elements.append(Paragraph("<b>Nome:</b> Palestra Imóveis", normal_style))
    elements.append(Paragraph("<b>Endereço:</b> Rua Serra de Bragança, 1814, Vila Gomes Cardim, São Paulo-SP, CEP 03318-000", normal_style))
    elements.append(Spacer(1, 0.5 * cm))

    elements.append(Paragraph("<b>Locador(a):</b> " + contrato.proprietario.nome + " - CPF: " + (contrato.proprietario.CPF or ""), normal_style))
    elements.append(Paragraph("<b>Locatário(a):</b> " + contrato.inquilino.nome + " - CPF: " + (contrato.inquilino.CPF or ""), normal_style))
    elements.append(Spacer(1, 0.5 * cm))

    meses = {
        1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 
        5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto', 
        9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
    }
    header = ["Mês", "Rendimento Bruto", "Valor Comissão", "Imposto Retido"]
    data = [header]
    valores_por_mes = {mes: [0, 0, 0] for mes in range(1, 13)}

    for cobranca in cobrancas:
        mes = cobranca.mes_referencia
        valores_por_mes[mes][0] = cobranca.valor
        valores_por_mes[mes][1] = contrato.valor_taxa_administracao()
        valores_por_mes[mes][2] = 0

    total_aluguel = 0
    total_taxa = 0
    total_imposto = 0
    for mes_num in range(1, 13):
        mes_nome = f"{meses[mes_num]}"
        aluguel = valores_por_mes[mes_num][0]
        taxa = valores_por_mes[mes_num][1]
        imposto = valores_por_mes[mes_num][2]
        total_aluguel += aluguel
        total_taxa += taxa
        total_imposto += imposto
        row = [
            mes_nome,
            format_currency(aluguel),
            format_currency(taxa),
            format_currency(imposto)
        ]
        data.append(row)
    data.append([
        "TOTAL", 
        format_currency(total_aluguel), 
        format_currency(total_taxa), 
        format_currency(total_imposto)
    ])

    valores_table = Table(data, colWidths=[4*cm, 5*cm, 5*cm, 4*cm])
    valores_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#f2f2f2')),
        ('TEXTCOLOR', (0, 0), (-1, 0), black),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, black),
        ('BOX', (0, 0), (-1, -1), 1, black),
        ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (-1, -1), HexColor('#f2f2f2')),
    ])
    valores_table.setStyle(valores_style)
    elements.append(valores_table)
    elements.append(Spacer(1, 0.5 * cm))

    atencao_style = ParagraphStyle(
        'Atencao',
        parent=styles['Normal'],
        fontSize=9,
        alignment=TA_JUSTIFY,
        spaceAfter=0.2*cm
    )
    elements.append(Paragraph("<b>Atenção:</b>", atencao_style))
    elements.append(Paragraph("Para a inclusão na Declaração do Imposto de Renda da Pessoa Física - DIRPF dos rendimentos informados neste documento, certifique-se de que os mesmos não constam de outro comprovante emitido pela fonte pagadora.", atencao_style))

    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    return response

def editar_despesa(request, pk):
    despesa = get_object_or_404(Despesa, id=pk)
    if request.method == 'POST':
        form = DespesaForm(request.POST, instance=despesa)
        if form.is_valid():
            form.save()
            messages.success(request, "Despesa atualizada com sucesso!")
            return redirect('dashboard', contrato_id=despesa.contrato.id)
        else:
            messages.error(request, "Por favor, corrija os erros no formulário.")
    else:
        form = DespesaForm(instance=despesa)
    
    return render(request, 'imoveis/editar_despesa.html', {
        'form': form,
        'despesa': despesa,
    })

def editar_cobranca(request, pk):

    cobranca = get_object_or_404(Cobranca, id=pk)
    
    if request.method == 'POST':
        form = CobrancaForm(request.POST, instance=cobranca)
        if form.is_valid():
            form.save()
            return redirect('dashboard', id=cobranca.contrato.id)
    else:
        form = CobrancaForm(instance=cobranca)
    
    return render(request, 'imoveis/editar_cobranca.html', {
        'form': form,
        'cobranca': cobranca
    })

import os
import sys
import traceback
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from django.shortcuts import render, redirect
from django.contrib import messages
from sisimob.models import Contrato, Despesa, Cobranca
from sisimob.utils.cobrancas_asaas import gerar_cobranca  # Certifique-se de que esta importação está correta

from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import json
from django.shortcuts import render
from .models import Contrato, Despesa

def obter_valor_historico(historico_json, data_cobranca):
    """
    Retorna o valor de aluguel vigente na data da cobrança,
    baseado no histórico de reajustes.
    """
    if isinstance(data_cobranca, date) and not isinstance(data_cobranca, datetime):
        data_cobranca = datetime.combine(data_cobranca, datetime.min.time())

    try:
        historico = json.loads(historico_json) if isinstance(historico_json, str) else historico_json
    except (json.JSONDecodeError, TypeError):
        return 0  # Valor padrão em caso de erro no JSON

    historico_ordenado = []
    for data_str, valor in historico.items():
        try:
            data_reajuste = datetime.strptime(data_str.strip(), "%Y-%m-%d")
            historico_ordenado.append((data_reajuste, float(valor)))
        except (ValueError, TypeError):
            continue

    historico_ordenado.sort(key=lambda x: x[0])

    if not historico_ordenado:
        return 0

    valor_vigente = historico_ordenado[0][1]  # Valor inicial

    for data_reajuste, valor in historico_ordenado:
        if data_reajuste <= data_cobranca:
            valor_vigente = valor
        else:
            break

    return valor_vigente

def editar_cobranca(request, pk):
    cobranca = get_object_or_404(Cobranca, id=pk)
    if request.method == 'POST':
        form = CobrancaForm(request.POST, instance=cobranca)
        if form.is_valid():
            form.save()
            messages.success(request, "Cobrança atualizada com sucesso!")
            return redirect('listar_cobrancas')
    else:
        form = CobrancaForm(instance=cobranca)
    return render(request, 'editar_cobranca.html', {'form': form})
    
def excluir_cobranca(request, pk):
    cobranca = get_object_or_404(Cobranca, id=pk)
    if request.method == 'POST':
        cobranca.delete()
        messages.success(request, "Cobrança excluída com sucesso!")
        return redirect('listar_cobrancas')
    return render(request, 'confirmar_exclusao.html', {'obj': cobranca})

def marcar_como_recebida(request, pk):
    cobranca = get_object_or_404(Cobranca, id=pk)
    if request.method == 'POST':
        cobranca.status = 'paga'
        cobranca.data_pagamento = timezone.now().date()
        cobranca.save()
        messages.success(request, "Cobrança marcada como recebida!")
    return redirect('dashboard', id=cobranca.contrato.id)

def marcar_como_repassada(request, pk):
    cobranca = get_object_or_404(Cobranca, id=pk)
    if request.method == 'POST':
        cobranca.status_repasse = 'repassado'
        cobranca.data_repasse = timezone.now().date()
        cobranca.save()
        messages.success(request, "Cobrança marcada como repassada!")
    return redirect('dashboard', id=cobranca.contrato.id)

def format_currency(value):
    if not value:
        return 'R$ 0,00'
    try:
        # Converte o valor para Decimal, se necessário
        value = Decimal(value)
        # Formata o valor no padrão brasileiro
        formatted_value = f'R$ {value:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
        return formatted_value
    except Exception:
        return 'R$ 0,00'
    
def lista_cobrancas(request):
    cobrancas = Cobranca.objects.all()
    return render(request, "imoveis/lista_cobrancas.html", {"cobrancas": cobrancas})

def lancar_despesa(request, id):
    # Obter o contrato pelo ID
    try:
        contrato = Contrato.objects.get(id=id)
    except Contrato.DoesNotExist:
        messages.error(request, 'Contrato não encontrado.')
        return redirect('alguma_view_de_erro')
    
    if request.method == 'POST':
        # Remover o campo contrato do POST data e passá-lo separadamente
        post_data = request.POST.copy()
        form = DespesaForm(post_data, contrato=contrato)
        
        if form.is_valid():
            despesa = form.save(commit=False)
            despesa.contrato = contrato  # Garante que a despesa está associada ao contrato
            despesa.save()
            messages.success(request, 'Despesa lançada com sucesso!')
            return redirect('dashboard', id=id)
        else:
            messages.error(request, 'Erro ao lançar a despesa. Verifique os campos.')
            print(form.errors)  # Adicionar para debug
    else:
        form = DespesaForm(contrato=contrato)
    
    # Renderizar o template com o formulário
    return render(request, 'imoveis/lancar_despesa.html', {
        'form': form,
        'contrato': contrato
    })

def editar_despesa(request, id):
    despesa = get_object_or_404(Despesa, id=id)

    if request.method == 'POST':
        form = DespesaForm(request.POST, instance=despesa)
        if form.is_valid():
            form.save()
            return redirect('dashboard')  # Redireciona para a página do dashboard ou qualquer outra página
    else:
        form = DespesaForm(instance=despesa)

    return render(request, 'imoveis/editar_despesa.html', {'form': form, 'despesa': despesa})

def excluir_despesa(request, id):

    despesa = get_object_or_404(Despesa, id=id)
    contrato_id = despesa.contrato.id  # Pegando o ID do contrato antes de excluir

    despesa.delete()  # Exclui a despesa

    return redirect('dashboard', id=contrato_id)  # Redireciona corretamente

def extrato(request):
    proprietarios = Cliente.objects.all().order_by('nome')
    proprietario_id = request.GET.get('proprietario_id')

    hoje = timezone.now()
    primeiro_dia_mes = hoje.replace(day=1)
    ultimo_dia_mes = (primeiro_dia_mes + timezone.timedelta(days=32)).replace(day=1) - timezone.timedelta(days=1)

    data_inicial_str = request.GET.get('data_inicial', primeiro_dia_mes.date().isoformat())
    data_final_str = request.GET.get('data_final', ultimo_dia_mes.date().isoformat())

    try:
        data_inicial = datetime.strptime(data_inicial_str, '%Y-%m-%d').date()
        data_final = datetime.strptime(data_final_str, '%Y-%m-%d').date()
    except ValueError:
        data_inicial = primeiro_dia_mes.date()
        data_final = ultimo_dia_mes.date()

    context = {
        'proprietarios': proprietarios,
        'proprietario_selecionado': int(proprietario_id) if proprietario_id else None,
        'data_inicial': data_inicial,
        'data_final': data_final,
    }

    if proprietario_id:
        proprietario = Cliente.objects.get(id=proprietario_id)
        contratos = Contrato.objects.filter(proprietario=proprietario)
        
        # ===== DEBUG =====
        print(f"Processando extrato para proprietário ID {proprietario_id}: {proprietario.nome}")
        # ===== DEBUG =====
        
        # Lista para imóveis do proprietário
        imoveis_dict = {}
        
        # Primeiro, vamos coletar todos os imóveis do proprietário
        for contrato in contratos:
            imovel = contrato.imovel
            if imovel.id not in imoveis_dict:
                # Verificar se há contratos ativos para este imóvel
                contratos_ativos = Contrato.objects.filter(
                    imovel=imovel,
                    data_inicio__lte=hoje.date(),
                    ativo=True
                ).exists()
                
                # Determinar o status com base nos contratos
                if contratos_ativos:
                    status = 'alugado'
                    status_display = 'Alugado'
                else:
                    status = 'disponivel'
                    status_display = 'Disponível'
                
                # Criar endereço completo
                endereco_completo = ""
                if hasattr(imovel, 'endereco_completo'):
                    if callable(imovel.endereco_completo):
                        endereco_completo = imovel.endereco_completo()
                    else:
                        endereco_completo = imovel.endereco_completo
                else:
                    # Criar um endereço completo manualmente
                    partes = []
                    if hasattr(imovel, 'endereco') and imovel.endereco:
                        partes.append(imovel.endereco)
                    if hasattr(imovel, 'numero') and imovel.numero:
                        partes.append(imovel.numero)
                    if hasattr(imovel, 'complemento') and imovel.complemento:
                        partes.append(imovel.complemento)
                    endereco_completo = ', '.join(partes)
                
                imoveis_dict[imovel.id] = {
                    'id': imovel.id,
                    'obj': imovel,
                    'endereco': getattr(imovel, 'endereco', ''),
                    'endereco_completo': endereco_completo,
                    'status': status,  # Status baseado em contratos
                    'get_status_display': status_display,  # Display do status
                    'receitas': 0,
                    'despesas': 0,
                    'repasses': 0,
                    'saldo': 0
                }
                
                # ===== DEBUG =====
                print(f"Imóvel inicializado - ID: {imovel.id}, Endereço: {endereco_completo}")
                # ===== DEBUG =====

        lancamentos = []

        # RECEITAS (Aluguel)
        cobrancas = Cobranca.objects.filter(
            contrato__proprietario=proprietario,
            data_pagamento__range=(data_inicial, data_final),
            status='paga'
        ).select_related('contrato__imovel', 'contrato')

        total_cobrancas_pagas = cobrancas.count()
        
        # ===== DEBUG =====
        print(f"Total de cobranças pagas encontradas: {total_cobrancas_pagas}")
        # ===== DEBUG =====

        for cobranca in cobrancas:
            imovel = cobranca.contrato.imovel
            data = cobranca.data_pagamento
            mes_ano = f"{cobranca.mes_referencia}/{cobranca.ano_referencia}"
            
            # ===== DEBUG =====
            print(f"\n----- PROCESSANDO COBRANÇA -----")
            print(f"Imóvel ID: {imovel.id}, Endereço: {getattr(imovel, 'endereco', 'N/A')}")
            print(f"Referência: {mes_ano}, Data pagamento: {data}")
            print(f"Valor total da cobrança: {cobranca.valor}")
            # ===== DEBUG =====
            
            # Usar o valor do aluguel do contrato, não da cobrança
            contrato = cobranca.contrato
            valor_aluguel_contrato = getattr(contrato, 'valor_aluguel', None) or getattr(contrato, 'valor_pacote', 0)
            
            # O valor da taxa de administração ainda vem da cobrança
            valor_admin = cobranca.valor_administracao
            
            # Calcular IPTU e outros encargos presentes na cobrança mas não no valor do aluguel
            valor_cobranca_total = cobranca.valor
            valor_encargos = valor_cobranca_total - valor_aluguel_contrato
            
            # ===== DEBUG =====
            print(f"Componentes do valor:")
            print(f"- Valor do aluguel no contrato: {valor_aluguel_contrato}")
            print(f"- Taxa de administração: {valor_admin}")
            print(f"- Valor cobrança total: {valor_cobranca_total}")
            print(f"- Valor calculado de encargos: {valor_encargos}")
            
            if hasattr(cobranca, 'valor_iptu'):
                print(f"- IPTU explícito na cobrança: {cobranca.valor_iptu}")
            
            receitas_antes = imoveis_dict[imovel.id]['receitas'] if imovel.id in imoveis_dict else 0
            # ===== DEBUG =====
            
            # Atualizar receitas do imóvel
            if imovel.id in imoveis_dict:
                imoveis_dict[imovel.id]['receitas'] += valor_aluguel_contrato
                imoveis_dict[imovel.id]['despesas'] += valor_admin
            
            # ===== DEBUG =====
            receitas_depois = imoveis_dict[imovel.id]['receitas'] if imovel.id in imoveis_dict else 0
            print(f"Receitas do imóvel antes: {receitas_antes}, depois: {receitas_depois}")
            print(f"Incremento nas receitas: {receitas_depois - receitas_antes}")
            # ===== DEBUG =====
            
            # Adicionar lançamento para o valor do aluguel puro
            lancamentos.append({
                'data': data,
                'descricao': f'Aluguel {mes_ano}',
                'tipo': 'RECEITA',
                'get_tipo_display': 'Receita',
                'valor': valor_aluguel_contrato,
                'imovel': imovel,
            })
            
            # ===== DEBUG =====
            print(f"Adicionado lançamento: Aluguel {mes_ano} - valor: {valor_aluguel_contrato}")
            # ===== DEBUG =====
            
            # Se houver encargos adicionais na cobrança, adicionar como um lançamento separado
            if valor_encargos > 0:
                # ===== DEBUG =====
                print(f"Encargos encontrados no valor de {valor_encargos}. Verifique se isso inclui IPTU.")
                
                # VERIFICAR: O código original não adiciona estes encargos às receitas nem como lançamentos!
                # Isso pode ser parte do problema.
                
                # ===== DEBUG =====
                # Verificar todos os atributos da cobrança que possam estar relacionados ao IPTU
                print("Atributos da cobrança relacionados ao IPTU:")
                for attr_name in dir(cobranca):
                    if 'iptu' in attr_name.lower() and not attr_name.startswith('__'):
                        valor_attr = getattr(cobranca, attr_name)
                        print(f"- {attr_name}: {valor_attr}")
                # ===== DEBUG =====
                
                # AQUI É IMPORTANTE: Verificar se o IPTU está sendo adicionado às receitas em outro lugar
                # ou se há algum atributo específico para IPTU na cobrança que não está sendo processado corretamente
            
            # Adicionar lançamento para a taxa de administração
            lancamentos.append({
                'data': data,
                'descricao': f'Taxa de Administração {mes_ano}',
                'tipo': 'DESPESA',
                'get_tipo_display': 'Despesa',
                'valor': valor_admin,
                'imovel': imovel,
            })
            
            # ===== DEBUG =====
            print(f"Adicionado lançamento: Taxa de Administração {mes_ano} - valor: {valor_admin}")
            print("----- FIM DO PROCESSAMENTO DA COBRANÇA -----\n")
            # ===== DEBUG =====

        # DESPESAS
        despesas = Despesa.objects.filter(
            contrato__proprietario=proprietario,
            data_inicio__lte=data_final,
        ).select_related('contrato__imovel')

        total_despesas_pagas = despesas.count()
        
        # ===== DEBUG =====
        print(f"Total de despesas encontradas: {total_despesas_pagas}")
        # ===== DEBUG =====

        for despesa in despesas:
            imovel = despesa.contrato.imovel
            qtd_parcelas = despesa.numero_parcelas or 1
            valor_parcela = despesa.valor_total / qtd_parcelas
            
            # ===== DEBUG =====
            print(f"\n----- PROCESSANDO DESPESA -----")
            print(f"Despesa: {despesa.descricao}, Imóvel ID: {imovel.id if imovel else 'N/A'}")
            print(f"Valor total: {despesa.valor_total}, Parcelas: {qtd_parcelas}, Valor parcela: {valor_parcela}")
            # ===== DEBUG =====

            for parcela in range(qtd_parcelas):
                data_parcela = despesa.data_inicio + timezone.timedelta(days=parcela * 30)
                
                # Verificar se a data da parcela está no período E se já passou (não é uma data futura)
                hoje = timezone.now().date()
                
                # MODIFICAÇÃO AQUI: Verificar se a data da parcela já passou ou é hoje
                if data_inicial <= data_parcela <= data_final and data_parcela <= hoje:
                    responsavel = getattr(despesa, 'paga', 'proprietario')
                    tipo_lancamento = 'RECEITA' if responsavel == 'inquilino' else 'DESPESA'
                    tipo_display = 'Receita' if tipo_lancamento == 'RECEITA' else 'Despesa'
                    
                    # ===== DEBUG =====
                    print(f"Parcela {parcela+1}/{qtd_parcelas}: Data {data_parcela}, Responsável: {responsavel}")
                    
                    receitas_antes = imoveis_dict[imovel.id]['receitas'] if imovel and imovel.id in imoveis_dict else 0
                    despesas_antes = imoveis_dict[imovel.id]['despesas'] if imovel and imovel.id in imoveis_dict else 0
                    # ===== DEBUG =====

                    if imovel and imovel.id in imoveis_dict:
                        if tipo_lancamento == 'RECEITA':
                            imoveis_dict[imovel.id]['receitas'] += valor_parcela
                        else:
                            imoveis_dict[imovel.id]['despesas'] += valor_parcela
                    
                    # ===== DEBUG =====
                    receitas_depois = imoveis_dict[imovel.id]['receitas'] if imovel and imovel.id in imoveis_dict else 0
                    despesas_depois = imoveis_dict[imovel.id]['despesas'] if imovel and imovel.id in imoveis_dict else 0
                    
                    if tipo_lancamento == 'RECEITA':
                        print(f"Receitas do imóvel antes: {receitas_antes}, depois: {receitas_depois}")
                        print(f"Incremento nas receitas: {receitas_depois - receitas_antes}")
                    else:
                        print(f"Despesas do imóvel antes: {despesas_antes}, depois: {despesas_depois}")
                        print(f"Incremento nas despesas: {despesas_depois - despesas_antes}")
                    # ===== DEBUG =====

                    lancamentos.append({
                        'data': data_parcela,
                        'descricao': f'{despesa.get_tipo_display()} - {despesa.descricao} (Parcela {parcela + 1}/{qtd_parcelas})',
                        'tipo': tipo_lancamento,
                        'get_tipo_display': tipo_display,
                        'valor': valor_parcela,
                        'imovel': imovel,
                    })
                # OUTRA OPÇÃO: Adicionar um comentário para marcar parcelas futuras sem contabilizá-las
                elif data_inicial <= data_parcela <= data_final and data_parcela > hoje:
                    # ===== DEBUG =====
                    print(f"Parcela {parcela+1}/{qtd_parcelas}: Data {data_parcela} - IGNORADA (data futura)")
                    # ===== DEBUG =====
            
            # ===== DEBUG =====
            print("----- FIM DO PROCESSAMENTO DA DESPESA -----\n")
            # ===== DEBUG =====
        
    

        # REPASSES (fora do loop de despesas)
        repasses = Cobranca.objects.filter(
            contrato__proprietario=proprietario,
            data_repasse__range=(data_inicial, data_final)
        ).select_related('contrato__imovel')

        total_repasses = repasses.count()
        
        # ===== DEBUG =====
        print(f"Total de repasses encontrados: {total_repasses}")
        # ===== DEBUG =====

        for repasse in repasses:
            imovel = repasse.contrato.imovel
            valor_liquido = repasse.valor_liquido
            
            # ===== DEBUG =====
            print(f"\n----- PROCESSANDO REPASSE -----")
            print(f"Repasse para imóvel ID: {imovel.id if imovel else 'N/A'}")
            print(f"Valor líquido: {valor_liquido}")
            
            repasses_antes = imoveis_dict[imovel.id]['repasses'] if imovel and imovel.id in imoveis_dict else 0
            # ===== DEBUG =====

            if imovel and imovel.id in imoveis_dict:
                imoveis_dict[imovel.id]['repasses'] += valor_liquido
            
            # ===== DEBUG =====
            repasses_depois = imoveis_dict[imovel.id]['repasses'] if imovel and imovel.id in imoveis_dict else 0
            print(f"Repasses do imóvel antes: {repasses_antes}, depois: {repasses_depois}")
            # ===== DEBUG =====

            lancamentos.append({
                'data': repasse.data_repasse,
                'descricao': f'Repasse para Proprietário',
                'tipo': 'REPASSE',
                'get_tipo_display': 'Repasse',
                'valor': valor_liquido,
                'imovel': imovel,
            })
            
            # ===== DEBUG =====
            print("----- FIM DO PROCESSAMENTO DO REPASSE -----\n")
            # ===== DEBUG =====

        # Atualizar saldo por imóvel
        for imovel_id, imovel_info in imoveis_dict.items():
            imovel_info['saldo'] = imovel_info['receitas'] - imovel_info['despesas'] - imovel_info['repasses']
            
            # ===== DEBUG =====
            print(f"\n----- RESUMO DO IMÓVEL ID: {imovel_id} -----")
            print(f"Endereço: {imovel_info['endereco_completo']}")
            print(f"Total de receitas: {imovel_info['receitas']}")
            print(f"Total de despesas: {imovel_info['despesas']}")
            print(f"Total de repasses: {imovel_info['repasses']}")
            print(f"Saldo: {imovel_info['saldo']}")
            print("----- FIM DO RESUMO DO IMÓVEL -----\n")
            # ===== DEBUG =====

        # Ordenar lançamentos por data
        lancamentos.sort(key=lambda x: x['data'])

        # Calcular saldo acumulado
        saldo = 0
        lancamentos_com_saldo = []

        for lancamento in lancamentos:
            if lancamento['tipo'] == 'RECEITA':
                saldo += lancamento['valor']
            elif lancamento['tipo'] == 'DESPESA':
                saldo -= lancamento['valor']
            elif lancamento['tipo'] == 'REPASSE':
                saldo -= lancamento['valor']

            lancamento_com_saldo = lancamento.copy()
            lancamento_com_saldo['saldo'] = saldo
            lancamentos_com_saldo.append(lancamento_com_saldo)

        # Totais finais
        total_receitas = sum(l['valor'] for l in lancamentos if l['tipo'] == 'RECEITA')
        total_despesas = sum(l['valor'] for l in lancamentos if l['tipo'] == 'DESPESA')
        total_repasses_valor = sum(l['valor'] for l in lancamentos if l['tipo'] == 'REPASSE')
        
        # ===== DEBUG =====
        print("\n----- RESUMO GERAL -----")
        print(f"Total de receitas: {total_receitas}")
        print(f"Total de despesas: {total_despesas}")
        print(f"Total de repasses: {total_repasses_valor}")
        print(f"Saldo final: {total_receitas - total_despesas - total_repasses_valor}")
        print("----- FIM DO RESUMO GERAL -----\n")
        # ===== DEBUG =====

        imoveis = list(imoveis_dict.values())
        context.update({
            'lancamentos': lancamentos_com_saldo,
            'saldo': total_receitas - total_despesas - total_repasses_valor,
            'total_receitas': total_receitas,
            'total_despesas': total_despesas,
            'total_repasses': total_repasses_valor,
            'total_cobrancas_pagas': total_cobrancas_pagas,
            'total_despesas_pagas': total_despesas_pagas,
            'total_repasses_feitos': total_repasses,
            'imoveis': imoveis,
        })
    return render(request, 'imoveis/extrato.html', context)

from datetime import datetime, date

def montar_extrato_do_proprietario(proprietario, data_inicial=None, data_final=None):
    extrato = []

    contratos = Contrato.objects.filter(proprietario=proprietario)

    if data_inicial:
        data_inicial = datetime.strptime(data_inicial, "%Y-%m-%d").date()
    if data_final:
        data_final = datetime.strptime(data_final, "%Y-%m-%d").date()

    for contrato in contratos:
        cobrancas = Cobranca.objects.filter(contrato=contrato)
        if data_inicial:
            cobrancas = cobrancas.filter(data__gte=data_inicial)
        if data_final:
            cobrancas = cobrancas.filter(data__lte=data_final)

        for cobranca in cobrancas:
            data_ref = date(cobranca.ano_referencia, cobranca.mes_referencia, 1)
            despesas = Despesa.objects.filter(contrato=cobranca.contrato)

            for despesa in despesas:
                # Verifica se a parcela está ativa para o mês/ano de referência
                if not despesa.parcela_atual_ativa(data_ref):
                    continue

                valor_parcela = despesa.calcular_valor_parcela()

                if despesa.paga == 'inquilino':
                    extrato.append({
                        'data': data_ref,
                        'descricao': f"Repasse despesa: {despesa.descricao or despesa.get_tipo_display()}",
                        'tipo': 'Crédito',
                        'valor': valor_parcela,
                    })
                elif despesa.paga == 'proprietario':
                    extrato.append({
                        'data': data_ref,
                        'descricao': f"Despesa: {despesa.descricao or despesa.get_tipo_display()}",
                        'tipo': 'Débito',
                        'valor': valor_parcela,
                    })

    extrato.sort(key=lambda x: x["data"])
    return extrato




def gerar_extrato_pdf(request, pk):
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    

    proprietario = get_object_or_404(Cliente, id=proprietario_id, tipo='Proprietario')

    extrato = montar_extrato_do_proprietario(proprietario, data_inicial, data_final)
  # Essa função você já usa no extrato
    pdf = gerar_extrato_repasses_pdf(request, proprietario.nome, extrato)
    
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="extrato_{proprietario.nome}.pdf"'
    return response


from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from datetime import datetime
from decimal import Decimal
from .models import Cliente, Cobranca
from .utils.pdf import gerar_pdf_extrato_repasses  # você ainda vai criar ou adaptar essa função

def extrato_repasses_pdf(request, proprietario_id):
    # Pega as datas do GET
    data_inicial_str = request.GET.get("data_inicial")
    data_final_str = request.GET.get("data_final")

    # Converte para date
    data_inicial = datetime.strptime(data_inicial_str, "%Y-%m-%d").date()
    data_final = datetime.strptime(data_final_str, "%Y-%m-%d").date()

    # Busca o proprietário
    proprietario = get_object_or_404(Cliente, id=proprietario_id, tipo="Proprietario")

    # Filtra cobranças do proprietário no período
    cobrancas = Cobranca.objects.select_related("contrato__imovel").filter(
        contrato__proprietario=proprietario,
        data_repasse__range=(data_inicial, data_final),
        status="paga",
        status_repasse="repassado"
    ).order_by("data_repasse")

    # Gera o PDF
    pdf = gerar_pdf_extrato_repasses(proprietario, data_inicial, data_final, cobrancas)
    return HttpResponse(pdf, content_type="application/pdf")

from django.http import HttpResponse, Http404
from .utils.extrato import gerar_extrato_rendimento

def gerar_pdf(request, contrato_id):
    # Captura o ano dos parâmetros GET
    ano = request.GET.get("ano")

    # Valida se os parâmetros foram fornecidos
    if not ano:
        raise Http404("O parâmetro 'ano' é obrigatório.")

    try:
        # Converte o ano para inteiro
        ano = int(ano)
    except ValueError:
        raise Http404("O parâmetro 'ano' deve ser um número válido.")

    # Busca o contrato pelo ID
    contrato = get_object_or_404(Contrato, id=contrato_id)

    # Gera o PDF
    try:
        pdf_content = gerar_extrato_rendimento(contrato_id, ano)
    except Exception as e:
        raise Http404(f"Erro ao gerar o extrato: {str(e)}")

    # Retorna o PDF como resposta HTTP
    response = HttpResponse(pdf_content, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="extrato_{ano}.pdf"'
    return response

from django.shortcuts import render
from django.contrib import messages
from decimal import Decimal
from dateutil.relativedelta import relativedelta
from .models import Contrato, IndiceInflacao
from .forms import ReajusteContratosForm

def calcular_fator_acumulado(contrato, data_inicio, data_fim):
    indices = IndiceInflacao.objects.filter(
        tipo=contrato.fator_reajuste,
        data_referencia__gte=data_inicio,
        data_referencia__lt=data_fim
    ).order_by('data_referencia')

    if indices.count() < 12:
        return None, None

    fator_acumulado = Decimal('1.00')
    for indice in indices:
        fator_acumulado *= (1 + indice.valor / Decimal('100'))

    valor_projetado = contrato.valor_aluguel * fator_acumulado
    if valor_projetado < contrato.valor_aluguel:
        valor_projetado = contrato.valor_aluguel

    return fator_acumulado, valor_projetado

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from datetime import datetime
from decimal import Decimal
from dateutil.relativedelta import relativedelta
from .models import Contrato, IndiceInflacao

def reajustar_contratos(request):
    form = ReajusteContratosForm(request.POST or None)

    contratos_com_indices = []
    if request.method == 'POST' and form.is_valid():
        data_inicio = form.cleaned_data['data_inicio'].replace(day=1)
        valor_manual = form.cleaned_data['valor_manual']

        for contrato in Contrato.objects.filter(data_inicio__lte=data_inicio):
            # Determina o período correto para o cálculo do reajuste
            if contrato.data_ultimo_reajuste:
                # Se já teve reajuste, usa a data do último como referência
                data_base = contrato.data_ultimo_reajuste
            else:
                # Se nunca teve reajuste, usa a data de início do contrato
                data_base = contrato.data_inicio.replace(day=1)
            
            # O período vai do mês da data_base até 11 meses depois
            # (total de 12 meses considerados, incluindo o mês inicial)
            data_fim = data_base + relativedelta(months=11)

            fator_acumulado, valor_projetado = calcular_fator_acumulado(contrato, data_base, data_fim)

            if fator_acumulado:
                contratos_com_indices.append({
                    'contrato': contrato,
                    'fator_acumulado': fator_acumulado,
                    'valor_projetado': valor_projetado,
                })

        return render(request, 'imoveis/reajustar_contratos.html', {
            'form': form,
            'contratos_com_indices': contratos_com_indices,
            'data_inicio': data_inicio,
            'valor_manual': valor_manual
        })

    else:
        for contrato in Contrato.objects.all():
            if contrato.data_ultimo_reajuste:
                data_base = contrato.data_ultimo_reajuste
            else:
                data_base = contrato.data_inicio.replace(day=1)
                
            # O período vai do mês da data_base até 11 meses depois
            data_fim = data_base + relativedelta(months=11)

            fator_acumulado, valor_projetado = calcular_fator_acumulado(contrato, data_base, data_fim)

            if fator_acumulado:
                contratos_com_indices.append({
                    'contrato': contrato,
                    'fator_acumulado': fator_acumulado,
                    'valor_projetado': valor_projetado,
                })

    return render(request, 'imoveis/reajustar_contratos.html', {
        'form': form,
        'contratos_com_indices': contratos_com_indices
    })

def calcular_fator_acumulado(contrato, data_base, data_fim):
    """
    Calcula o fator acumulado para um determinado período.
    
    Args:
        contrato: Objeto Contrato
        data_base: Data inicial para cálculo
        data_fim: Data final para cálculo (inclusive)
    """
    indices = []
    mes_atual = data_base
    
    # Coleta os índices mês a mês no período especificado (inclusive)
    while mes_atual <= data_fim:
        indice = IndiceInflacao.objects.filter(
            tipo=contrato.fator_reajuste,
            data_referencia__year=mes_atual.year,
            data_referencia__month=mes_atual.month
        ).first()
        
        if indice:
            indices.append(indice)
        
        mes_atual += relativedelta(months=1)
    
    # Se não temos todos os índices necessários, retornamos None
    if len(indices) < 12:
        return None, None
    
    # Calcula o fator acumulado
    fator_acumulado = Decimal('1.00')
    for indice in indices:
        fator_acumulado *= (1 + indice.valor / Decimal('100'))
    
    # Calcula o valor projetado
    if contrato.tipo_pagamento == 'pacote':
        valor_base = contrato.valor_pacote
    else:
        valor_base = contrato.valor_aluguel
    valor_projetado = valor_base * fator_acumulado
    if valor_projetado < valor_base:
        valor_projetado = valor_base
        
    return fator_acumulado, valor_projetado

def reajustar_contrato_individual(request, contrato_id):
    contrato = get_object_or_404(Contrato, id=contrato_id)

    if request.method == 'POST':
        data_inicio_str = request.POST.get('data_inicio')
        valor_manual = request.POST.get('valor_manual')
        valor_manual_tipo = request.POST.get('tipo_valor_manual')  # 'percentual', 'fator' ou 'fixo'

        if not data_inicio_str:
            messages.error(request, "Informe a data de início do reajuste.")
            return redirect('reajustar_contrato_individual', contrato_id=contrato_id)

        data_inicio = datetime.strptime(data_inicio_str, "%Y-%m-%d").date().replace(day=1)

        # Determina o período para o cálculo do reajuste
        if contrato.data_ultimo_reajuste:
            base_reajuste = contrato.data_ultimo_reajuste
        else:
            base_reajuste = contrato.data_inicio.replace(day=1)

        # Coleta dos índices de inflação - 12 meses consecutivos incluindo o mês base
        indices = []
        for i in range(12):
            mes = base_reajuste + relativedelta(months=i)
            indice = IndiceInflacao.objects.filter(
                tipo=contrato.fator_reajuste,
                data_referencia__year=mes.year,
                data_referencia__month=mes.month
            ).first()

            if not indice:
                messages.error(request, f"Índice não disponível para {mes.strftime('%m/%Y')}.")
                return redirect('reajustar_contrato_individual', contrato_id=contrato_id)

            indices.append(indice)

        # Cálculo do fator acumulado padrão com base nos índices
        fator_acumulado = Decimal('1.00')
        for indice in indices:
            fator_acumulado *= (1 + indice.valor / Decimal('100'))

        # Aplica o reajuste automático inicialmente
        if contrato.tipo_pagamento == 'pacote':
            valor_base = contrato.valor_pacote
        else:
            valor_base = contrato.valor_aluguel
        novo_valor = valor_base * fator_acumulado
        if novo_valor < valor_base:
            novo_valor = valor_base

        # Se informado, substitui pelo valor manual
        if valor_manual:
            try:
                valor_decimal = Decimal(valor_manual.replace(",", "."))
                if valor_manual_tipo == 'percentual':
                    novo_valor = contrato.valor_aluguel * (1 + (valor_decimal / Decimal('100')))
                elif valor_manual_tipo == 'fator':
                    novo_valor = contrato.valor_aluguel * valor_decimal
                elif valor_manual_tipo == 'fixo':
                    novo_valor = valor_decimal
                else:
                    messages.error(request, "Tipo de reajuste inválido.")
                    return redirect('reajustar_contrato_individual', contrato_id=contrato_id)

                if novo_valor < contrato.valor_aluguel:
                    novo_valor = contrato.valor_aluguel

            except:
                messages.error(request, "Valor manual inválido.")
                return redirect('reajustar_contrato_individual', contrato_id=contrato_id)

        # Atualiza o contrato com o novo valor
        contrato.valor_aluguel = novo_valor
        contrato.data_ultimo_reajuste = data_inicio
        # Define a próxima data base (próximo reajuste será em 12 meses)
        contrato.data_base = data_inicio + relativedelta(months=12)

        # Histórico de reajuste - usando a data base escolhida para o reajuste
        historico = contrato.historico_aluguel or {}
        # Usa a data de reajuste informada, não a data atual
        data_registro = data_inicio.isoformat()
        historico[data_registro] = float(novo_valor)
        contrato.historico_aluguel = historico

        contrato.save()

        messages.success(request, f"Contrato {contrato.id} reajustado com sucesso.")
        return redirect('reajustar_contratos')

    # GET request: mostra dados para reajuste
    if contrato.data_ultimo_reajuste:
        base_reajuste = contrato.data_ultimo_reajuste
    else:
        base_reajuste = contrato.data_inicio.replace(day=1)

    indices = []
    # Coleta os índices de 12 meses consecutivos
    for i in range(12):
        mes = base_reajuste + relativedelta(months=i)
        indice = IndiceInflacao.objects.filter(
            tipo=contrato.fator_reajuste,
            data_referencia__year=mes.year,
            data_referencia__month=mes.month
        ).first()
        if indice:
            indices.append({
                'mes': mes.strftime('%m/%Y'),
                'valor': indice.valor,
                'indice': indice
            })

    fator_acumulado = Decimal('1.00')
    for item in indices:
        fator_acumulado *= (1 + item['indice'].valor / Decimal('100'))


    if contrato.tipo_pagamento == 'pacote':
        valor_base = contrato.valor_pacote
    else:
        valor_base = contrato.valor_aluguel

    valor_projetado = valor_base * fator_acumulado
    if valor_projetado < valor_base:
        valor_projetado = valor_base

    return render(request, 'imoveis/reajustar_contrato_individual.html', {
        'contrato': contrato,
        'indices': indices,
        'data_inicio': base_reajuste,
        'proxima_data_reajuste': base_reajuste + relativedelta(months=12),
        'valor_manual': request.GET.get('valor_manual', ''),
        'fator_acumulado': fator_acumulado,
        'fator_percentual': (fator_acumulado - Decimal('1.00')) * Decimal('100'),
        'valor_atual': contrato.valor_aluguel,
        'valor_projetado': valor_projetado
    })



from django.shortcuts import render
from datetime import date
from sisimob.models import Cobranca
from sisimob.services.notificacao import gerar_mensagem_cobranca
from sisimob.utils.data import dia_util_anterior
from collections import defaultdict

from collections import defaultdict
from django.shortcuts import render
from datetime import date

def visualizar_mensagens_cobranca(request):
    hoje = date.today()
    lembretes = [(10, 'lembrete_10_enviado'), (3, 'lembrete_3_enviado'), (0, 'lembrete_0_enviado')]

    mensagens = []

    cobrancas = Cobranca.objects.filter(status='pendente')

    for dias_uteis, flag in lembretes:
        for cobranca in cobrancas:
            vencimento = cobranca.data_vencimento
            data_lembrete = dia_util_anterior(vencimento, dias_uteis)
            if data_lembrete != hoje:
                continue

            contrato = cobranca.contrato
            for inquilino in contrato.inquilino.all():
                if not inquilino.celular:
                    continue

                mensagens.append({
                    "id": cobranca.id,
                    "nome": inquilino.nome,
                    "telefone": inquilino.celular,
                    "mensagem": gerar_mensagem_cobranca(cobranca),
                    "dias_uteis": dias_uteis,
                    "vencimento": cobranca.data_vencimento,
                })


    # Agrupar as mensagens pela data do lembrete
    mensagens_agrupadas = defaultdict(list)
    for mensagem in mensagens:
        data_lembrete = mensagem.get('data_lembrete', 'Sem data')  # Valor padrão
        mensagens_agrupadas[data_lembrete].append(mensagem)

    # Organizar as mensagens por data do lembrete (ignorando as que não têm data real)
    mensagens_agrupadas = dict(sorted(mensagens_agrupadas.items(), key=lambda x: x[0] if isinstance(x[0], (str, datetime.date)) else ''))

    return render(request, 'cobrancas/visualizar_mensagens.html', {"mensagens_agrupadas": mensagens_agrupadas})

def enviar_mensagens_cobranca(request):
    if request.method != "POST":
        return redirect('visualizar_mensagens_cobranca')

    hoje = date.today()
    lembretes = [(10, '10_dias'), (3, '3_dias'), (0, 'vencimento')]
    cobrancas = Cobranca.objects.filter(status='pendente')
    total_enviadas = 0

    for dias_uteis, tipo_lembrete in lembretes:
        for cobranca in cobrancas:
            if LembreteEnviado.objects.filter(cobranca=cobranca, tipo=tipo_lembrete).exists():
                continue

            vencimento = cobranca.data_vencimento
            data_lembrete = dia_util_anterior(vencimento, dias_uteis)
            if data_lembrete != hoje:
                continue

            contrato = cobranca.contrato
            for inquilino in contrato.inquilino.all():
                if not inquilino.celular:
                    continue

                mensagem = gerar_mensagem_cobranca(cobranca)
                numero = inquilino.celular
                resposta = enviar_mensagem(numero, mensagem)

                if resposta.get("status") == "success":
                    LembreteEnviado.objects.create(cobranca=cobranca, tipo=tipo_lembrete)
                    total_enviadas += 1

    if total_enviadas > 0:
        messages.success(request, f"{total_enviadas} mensagens enviadas com sucesso!")
    else:
        messages.warning(request, "Nenhuma mensagem foi enviada.")

    return redirect('visualizar_mensagens_cobranca')


from datetime import datetime, date



from datetime import date, timedelta
from decimal import Decimal
from dateutil.relativedelta import relativedelta
import locale
from calendar import month_name
import logging
from django.shortcuts import render
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from .models import Contrato, Despesa, Cobranca
from sisimob.utils.cobrancas_asaas import gerar_cobranca

# Configure logging
logger = logging.getLogger(__name__)

# Configure locale for currency formatting
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
    except:
        # Fallback if locale configuration fails
        pass

def obter_valor_historico(historico, data_referencia):
    """
    Obtém o valor do aluguel para uma data de referência específica
    baseado no histórico de valores
    """
    if not historico:
        return None
        
    # Converte as datas string para objetos date
    historico_ordenado = []
    for data_str, valor in historico.items():
        try:
            partes = data_str.split('-')
            if len(partes) == 3:
                data = date(int(partes[0]), int(partes[1]), int(partes[2]))
                historico_ordenado.append((data, Decimal(str(valor))))
        except Exception as e:
            logger.error(f"Erro ao processar data do histórico: {data_str}, erro: {str(e)}")
            
    # Ordena por data
    historico_ordenado.sort(key=lambda x: x[0])
    
    # Encontra o valor mais recente antes da data de referência
    valor_atual = None
    for data, valor in historico_ordenado:
        if data <= data_referencia:
            valor_atual = valor
        else:
            break
            
    return valor_atual

def gerar_cobrancas_view(request):
    if request.method == "POST":
        try:
            # Log the POST data for debugging
            logger.info(f"POST data received: {request.POST}")
            
            mes_referencia = int(request.POST.get("mes_referencia"))
            ano_referencia = int(request.POST.get("ano_referencia"))
            data_referencia = date(ano_referencia, mes_referencia, 1)
            processar_asaas = request.POST.get("processar_asaas") == "true"
            contrato_id = request.POST.get("contrato_id")
            
            logger.info(f"Parameters: mes={mes_referencia}, ano={ano_referencia}, processar_asaas={processar_asaas}, contrato_id={contrato_id}")
            
            # Para refletir a cobrança de janeiro referente a dezembro, ajustamos para o mês anterior
            data_referencia_cobranca = date(ano_referencia, mes_referencia, 1) - timedelta(days=1)
            mes_anterior = data_referencia_cobranca.month
            ano_anterior = data_referencia_cobranca.year
            
            # Debug filter parameters
            logger.info(f"Filtering contratos with: ativo=True, data_inicio<={data_referencia}, data_fim>={data_referencia}")
            
            # Filtro adicional por ID de contrato se fornecido
            contratos_query = Contrato.objects.filter(
                ativo=True,
                data_inicio__lte=data_referencia
            ).filter(
                Q(data_fim__isnull=True) | Q(data_fim__gte=data_referencia) | Q(data_fim__lt=data_referencia)
            )
            
            if contrato_id:
                contratos_query = contratos_query.filter(id=contrato_id)
            
            contratos = contratos_query.all()
            
            logger.info(f"Found {contratos.count()} active contratos")
            
            # Debug: Log basic info about each contrato
            for i, contrato in enumerate(contratos):
                logger.info(f"Contrato {i+1}: ID={contrato.id}")
                inquilinos = [inq.nome for inq in contrato.inquilino.all()]
                proprietarios = [prop.nome for prop in contrato.proprietario.all()]
                logger.info(f"Inquilinos: {inquilinos}, Proprietarios: {proprietarios}")
            
            cobrancas_preview = []
            cobrancas_asaas_results = []
            
            for i, contrato in enumerate(contratos):
                logger.info(f"Processing contrato {i+1}/{contratos.count()}: ID={contrato.id}")
                
                # Inicialize historico com um dicionário vazio se não existir
                historico = {}
                if hasattr(contrato, 'historico_aluguel') and contrato.historico_aluguel:
                    historico = contrato.historico_aluguel
                    logger.info(f"Contrato has historico_aluguel: {historico}")
                
                # Tenta obter o valor histórico ou usa o valor padrão
                try:
                    valor_fixo = obter_valor_historico(historico, data_referencia)
                    if valor_fixo is None:
                        valor_fixo = contrato.valor_aluguel or contrato.valor_pacote or Decimal('0')
                        logger.info(f"Using default value: {valor_fixo}")
                    else:
                        logger.info(f"Using historical value: {valor_fixo}")
                except Exception as e:
                    logger.error(f"Erro ao obter valor histórico para contrato {contrato.id}: {str(e)}")
                    valor_fixo = contrato.valor_aluguel or contrato.valor_pacote or Decimal('0')
                    logger.info(f"Error getting historical value, using default: {valor_fixo}")
                
                # Garante que valor_fixo seja um Decimal
                if not isinstance(valor_fixo, Decimal):
                    valor_fixo = Decimal(str(valor_fixo))
                
                # Busca despesas ativas para o contrato
                logger.info(f"Searching for despesas with contrato={contrato.id}, data_inicio<={data_referencia}")
                despesas = Despesa.objects.filter(
                    contrato=contrato,
                    data_inicio__lte=data_referencia
                )
                logger.info(f"Found {despesas.count()} despesas")
                
                despesas_ativas = []
                for despesa in despesas:
                    if despesa.is_recorrente:
                        despesas_ativas.append(despesa)
                        logger.info(f"Including recurrent despesa: {despesa.id}, {despesa.descricao}")
                    elif despesa.numero_parcelas is None:
                        despesas_ativas.append(despesa)
                        logger.info(f"Including despesa without parcelas: {despesa.id}, {despesa.descricao}")
                    else:
                        data_fim_despesa = despesa.data_inicio + relativedelta(months=despesa.numero_parcelas - 1)
                        if data_fim_despesa >= data_referencia:
                            despesas_ativas.append(despesa)
                            logger.info(f"Including active installment despesa: {despesa.id}, {despesa.descricao}")
                        else:
                            logger.info(f"Excluding expired installment despesa: {despesa.id}, {despesa.descricao}")
                
                logger.info(f"Total active despesas: {len(despesas_ativas)}")
                
                despesas_repassadas = Decimal('0')
                despesas_deduzidas = Decimal('0')
                
                descricao_itens = []
                
                # Adiciona item de aluguel
                try:
                    mes_nome = month_name[mes_anterior]
                    if not isinstance(mes_nome, str):
                        mes_nome = mes_nome.capitalize()
                    else:
                        mes_nome = mes_nome.capitalize()
                except Exception as e:
                    logger.error(f"Error getting month name: {str(e)}")
                    # Fallback para caso o month_name falhe
                    mes_nome = f"Mês {mes_anterior}"
                
                try:
                    valor_formatado = locale.currency(valor_fixo, grouping=True)
                except Exception as e:
                    logger.error(f"Error formatting currency: {str(e)}")
                    # Fallback se a formatação de moeda falhar
                    valor_formatado = f"R$ {valor_fixo:.2f}"
                
                descricao_itens.append(f"Aluguel ({mes_nome}/{ano_anterior}) - {valor_formatado}")
                
                # Processa despesas
                for despesa in despesas_ativas:
    
                    try:
                        valor_parcela = Decimal(str(despesa.calcular_valor_parcela()))
                        logger.info(f"Despesa {despesa.id} value: {valor_parcela}, paga por: {despesa.paga}")
                    except Exception as e:
                        logger.error(f"Erro ao calcular valor da parcela para despesa {despesa.id}: {str(e)}")
                        valor_parcela = Decimal('0')
                    
                    try:
                        valor_formatado = locale.currency(valor_parcela, grouping=True)
                    except:
                        valor_formatado = f"R$ {valor_parcela:.2f}"
                    
                    # Verifique se a despesa deve ser paga pelo proprietário
                    is_despesa_proprietario = despesa.paga == 'proprietario'
                    is_despesa_imobiliaria = despesa.paga == 'imobiliaria'
                    
                    # Se for despesa do proprietário OU tipo='deduzida', então deduz do valor total
                    if is_despesa_proprietario:
                        despesas_deduzidas += valor_parcela
                        descricao_itens.append(f"{despesa.descricao} (proprietário) - {valor_formatado}")
                        logger.info(f"Added deducted expense: {despesa.descricao}, value: {valor_parcela}, paga por: {despesa.paga}")
                    elif is_despesa_imobiliaria:
                        despesas_deduzidas += valor_parcela
                        descricao_itens.append(f"{despesa.descricao} (imobiliaria) - {valor_formatado}")
                        logger.info(f"Added deducted expense: {despesa.descricao}, value: {valor_parcela}, paga por: {despesa.paga}")
                    else:
                        # Despesas pagas pelo inquilino ou imobiliária são repassadas
                        despesas_repassadas += valor_parcela
                        if despesa.descricao.lower() == "iptu" or despesa.tipo == 'iptu':
                            mes_inicial_iptu = despesa.data_inicio.month
                            ano_inicial_iptu = despesa.data_inicio.year
                            numero_parcela = (ano_referencia - ano_inicial_iptu) * 12 + (mes_referencia - mes_inicial_iptu) + 1
                            descricao_itens.append(f"IPTU ({numero_parcela}/{despesa.numero_parcelas}) - {valor_formatado}")
                            logger.info(f"Added IPTU expense: parcela {numero_parcela}/{despesa.numero_parcelas}, value: {valor_parcela}")
                        elif despesa.is_recorrente:
                            try:
                                mes_nome = month_name[mes_anterior]
                                if not isinstance(mes_nome, str):
                                    mes_nome = mes_nome.capitalize()
                                else:
                                    mes_nome = mes_nome.capitalize()
                            except:
                                mes_nome = f"Mês {mes_anterior}"
                            
                            # Adiciona quem paga nas despesas recorrentes (exceto proprietário que já é tratado acima)
                            paga_display = f"({despesa.get_paga_display()})" if despesa.paga != 'inquilino' else ""
                            descricao_itens.append(f"{despesa.descricao} {paga_display} ({mes_nome}/{ano_anterior}) - {valor_formatado}")
                            logger.info(f"Added recurrent expense: {despesa.descricao}, value: {valor_parcela}, paga por: {despesa.paga}")
                        else:
                            # Adiciona quem paga nas despesas não recorrentes (exceto proprietário que já é tratado acima)
                            paga_display = f"({despesa.get_paga_display()})" if despesa.paga != 'inquilino' else ""
                            descricao_itens.append(f"{despesa.descricao} {paga_display} - {valor_formatado}")
                            logger.info(f"Added regular expense: {despesa.descricao}, value: {valor_parcela}, paga por: {despesa.paga}")
                
                # Calcula valor total
                valor_total = valor_fixo + despesas_repassadas - despesas_deduzidas
                logger.info(f"Total value: {valor_total} = {valor_fixo} + {despesas_repassadas} - {despesas_deduzidas}")
                
                # Determina data de vencimento
                dia_vencimento = contrato.dia_pagamento
                try:
                    data_vencimento = data_referencia.replace(day=dia_vencimento)
                    logger.info(f"Due date set to: {data_vencimento}")
                except ValueError as e:
                    logger.error(f"Error setting due date: {str(e)}")
                    # Trata casos onde o dia é maior que o último dia do mês
                    proximo_mes = data_referencia.replace(day=28) + timedelta(days=4)
                    ultimo_dia_mes = (proximo_mes - timedelta(days=proximo_mes.day)).day
                    data_vencimento = data_referencia.replace(day=ultimo_dia_mes)
                    logger.info(f"Due date adjusted to end of month: {data_vencimento}")
                
                # Junta os itens em uma descrição
                descricao = ", ".join(descricao_itens)
                logger.info(f"Description: {descricao[:50]}...")
                
                # Cria objeto de cobrança para preview
                cobranca_data = {
                    'contrato': contrato,
                    'valor': valor_total,
                    'data_vencimento': data_vencimento,
                    'descricao': descricao,
                    'despesas_repassadas': despesas_repassadas,
                    'despesas_deduzidas': despesas_deduzidas,
                    'mes_referencia': mes_referencia,
                    'ano_referencia': ano_referencia
                }
                
                cobrancas_preview.append(cobranca_data)
                logger.info(f"Added charge to preview list")
                
                # Processa no Asaas se necessário
                if processar_asaas:
                    logger.info("Processing in Asaas...")
                    
                    # Verificar se há inquilinos associados
                    if not contrato.inquilino.exists():
                        logger.error(f"Contrato {contrato.id} não tem inquilinos associados")
                        cobranca_data['asaas_status'] = "Erro"
                        cobranca_data['asaas_erro'] = "Contrato sem inquilinos associados"
                        cobrancas_asaas_results.append(cobranca_data)
                        continue
                    
                    # Obter inquilinos com ID Asaas cadastrado
                    inquilinos_validos = contrato.inquilino.filter(asaas_id__isnull=False).exclude(asaas_id='')
                    
                    if not inquilinos_validos.exists():
                        logger.error(f"Contrato {contrato.id} não tem inquilinos com ID Asaas válido")
                        cobranca_data['asaas_status'] = "Erro"
                        cobranca_data['asaas_erro'] = "Nenhum inquilino com ID Asaas válido"
                        cobrancas_asaas_results.append(cobranca_data)
                        continue
                    
                    # Usar o primeiro inquilino válido para a cobrança
                    inquilino = inquilinos_validos.first()
                    
                    # Verificar se já existe cobrança para este contrato/mês/ano
                    cobranca_existente = Cobranca.objects.filter(
                        contrato=contrato,
                        mes_referencia=mes_referencia,
                        ano_referencia=ano_referencia
                    ).first()
                    
                    if cobranca_existente:
                        logger.warning(f"Charge already exists for contrato {contrato.id}, {mes_referencia}/{ano_referencia}: ID={cobranca_existente.id}")
                        cobranca_data['asaas_status'] = "Erro"
                        cobranca_data['asaas_erro'] = "Cobrança já existe para este período"
                        cobrancas_asaas_results.append(cobranca_data)
                        continue
                    
                    try:
                        # Formata a data de vencimento para o formato do Asaas (YYYY-MM-DD)
                        data_vencimento_str = data_vencimento.strftime('%Y-%m-%d')
                        logger.info(f"Asaas due date: {data_vencimento_str}")
                        
                        # Chama a função de geração de cobrança no Asaas usando os dados do inquilino
                        logger.info(f"Calling Asaas API with: id={inquilino.asaas_id}, value={float(valor_total)}")
                        resultado_asaas = gerar_cobranca(
                            asaas_id=inquilino.asaas_id,
                            valor=float(valor_total),
                            vencimento=data_vencimento_str,
                            nome=inquilino.nome,  # Usar o nome do inquilino
                            descricao=descricao[:255]  # Limita a descrição a 255 caracteres
                        )
                        
                        logger.info(f"Asaas API response: {resultado_asaas}")
                        
                        # Processa a resposta e salva a cobrança
                        nova_cobranca, sucesso, erro_msg = processar_resposta_asaas(
                            resultado_asaas=resultado_asaas,
                            contrato=contrato,
                            inquilino=inquilino,
                            valor_total=valor_total,
                            data_vencimento=data_vencimento,
                            descricao=descricao,
                            mes_referencia=mes_referencia,
                            ano_referencia=ano_referencia
                        )
                        
                        # Atualiza os dados para a resposta
                        cobranca_data['asaas_result'] = resultado_asaas
                        
                        if sucesso:
                            cobranca_data['asaas_id'] = nova_cobranca.asaas_id
                            cobranca_data['asaas_status'] = "Sucesso"
                            logger.info(f"Successfully saved charge with Asaas ID: {nova_cobranca.asaas_id}")
                        else:
                            cobranca_data['asaas_status'] = "Erro"
                            cobranca_data['asaas_erro'] = erro_msg
                            logger.error(f"Error processing Asaas response: {erro_msg}")

                    except Exception as e:
                        logger.error(f"Erro ao gerar cobrança no Asaas: {str(e)}")
                        # Salva a cobrança com erro
                        nova_cobranca = Cobranca(
                            contrato=contrato,
                            valor=valor_total,
                            data_vencimento=data_vencimento,
                            descricao=descricao,
                            mes_referencia=mes_referencia,
                            ano_referencia=ano_referencia,
                            status="ERROR"
                        )
                        nova_cobranca.save()
                        
                        cobranca_data['asaas_status'] = "Erro"
                        cobranca_data['asaas_erro'] = f"Exceção: {str(e)}"
                    
                    cobrancas_asaas_results.append(cobranca_data)
                    logger.info(f"Added charge to Asaas results list")
            
            # Log summary
            logger.info(f"Preview charges: {len(cobrancas_preview)}, Asaas charges: {len(cobrancas_asaas_results)}")
            
            # Decide qual template renderizar com base no processamento do Asaas
            if processar_asaas:
                sucesso_count = sum(1 for c in cobrancas_asaas_results if c.get('asaas_status') == "Sucesso")
                erro_count = sum(1 for c in cobrancas_asaas_results if c.get('asaas_status') == "Erro")
                
                logger.info(f"Charges summary - Success: {sucesso_count}, Error: {erro_count}")
                
                messages.success(request, f"Geradas {len(cobrancas_asaas_results)} cobranças no Asaas para {mes_referencia}/{ano_referencia}. Sucesso: {sucesso_count}, Erro: {erro_count}")
                context = {
                    'cobrancas_processadas': cobrancas_asaas_results,
                    'mes_referencia': mes_referencia,
                    'ano_referencia': ano_referencia,
                    'sucesso': sucesso_count,
                    'erro': erro_count
                }
                return render(request, 'imoveis/cobrancas_processadas.html', context)
            else:
                # Mostra apenas o preview das cobranças
                context = {
                    'cobrancas_preview': cobrancas_preview,
                    'mes_referencia': mes_referencia,
                    'ano_referencia': ano_referencia
                }
                logger.info(f"Rendering preview with {len(cobrancas_preview)} charges")
                return render(request, 'imoveis/preview_cobrancas.html', context)
                
        except Exception as e:
            logger.error(f"Erro geral na geração de cobranças: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            messages.error(request, f"Erro ao processar cobranças: {str(e)}")
            return HttpResponseRedirect(reverse('cadastro_cobrancas'))

    # Requisição GET
    logger.info("GET request for cadastro_cobrancas page")
    hoje = date.today()
    meses = [{"numero": i, "nome": date(hoje.year, i, 1).strftime("%B")} for i in range(1, 13)]

    mes_selecionado = request.GET.get("mes", hoje.month)
    ano_selecionado = request.GET.get("ano", hoje.year)
    
    # Obter todos os contratos ativos para o dropdown
    contratos = Contrato.objects.filter(ativo=True)

    context = {
        "meses": meses,
        "mes_atual": int(mes_selecionado),
        "ano_atual": int(ano_selecionado),
        "contratos": contratos,
    }

    return render(request, "imoveis/cadastro_cobrancas.html", context)



def confirmar_cobrancas_view(request):

    cobrancas_data = request.session.get('cobrancas_preview', [])
    cobrancas_geradas = 0

    if not cobrancas_data:
        messages.warning(request, "Nenhuma cobrança encontrada para confirmação.")
        return redirect('cadastro_cobrancas')

    for cobranca_data in cobrancas_data:
        contrato_id = cobranca_data.get('contrato_id')
        contrato = get_object_or_404(Contrato, id=contrato_id)

        # Verifica se já existe cobrança para esse período
        if Cobranca.objects.filter(
            contrato=contrato,
            mes_referencia=cobranca_data['mes_referencia'],
            ano_referencia=cobranca_data['ano_referencia']
        ).exists():
            messages.warning(
                request,
                f"Cobrança já existe para o contrato ID {contrato.id} no período {cobranca_data['mes_referencia']}/{cobranca_data['ano_referencia']}."
            )
            continue

        data_cobranca = datetime(
            year=int(cobranca_data['ano_referencia']),
            month=int(cobranca_data['mes_referencia']),
            day=1
        )

        valor_base_reajustado = obter_valor_historico(
            contrato.historico_reajustes_json,
            data_cobranca,
            valor_base=float(contrato.valor_base_aluguel)
        )

        inquilinos_validos = contrato.inquilino.filter(asaas_id__isnull=False).exclude(asaas_id='')
        if not inquilinos_validos.exists():
            messages.warning(request, f"Contrato {contrato.id} sem inquilinos com ID Asaas.")
            continue

        inquilino = inquilinos_validos.first()

        try:
            resposta = gerar_cobranca(
                asaas_id=inquilino.asaas_id,
                valor=float(valor_base_reajustado),
                vencimento=cobranca_data['data_vencimento'].strftime('%Y-%m-%d'),
                nome=inquilino.nome,
                descricao=cobranca_data['descricao']
            )

            if resposta and isinstance(resposta, dict) and "id" in resposta:
                pix_data = resposta.get("pixTransaction") or resposta.get("pix", {})

                Cobranca.objects.create(
                    contrato=contrato,
                    valor=valor_base_reajustado,
                    data_vencimento=cobranca_data['data_vencimento'],
                    mes_referencia=cobranca_data['mes_referencia'],
                    ano_referencia=cobranca_data['ano_referencia'],
                    descricao=cobranca_data['descricao'],
                    inquilino=inquilino,

                    # Campos do Asaas
                    asaas_id=resposta.get("id"),
                    asaas_payment_id=resposta.get("id"),  # ou outro campo se necessário
                    asaas_boleto_url=resposta.get("bankSlipUrl"),
                    asaas_pix_url=pix_data.get("qrCodeUrl"),
                    asaas_pix_copia_cola=pix_data.get("payload"),
                    asaas_codigo_barras=resposta.get("identificationField"),
                    asaas_invoice_url=resposta.get("invoiceUrl"),
                    asaas_invoice_number=resposta.get("invoiceNumber"),
                    asaas_status=resposta.get("status", "PENDING"),
                    asaas_status_asaas=resposta.get("status"),
                    asaas_url_fatura=resposta.get("invoiceUrl"),
                    asaas_pix_qr_code_base64=pix_data.get("base64Image"),
                )
                cobrancas_geradas += 1
            else:
                error_msg = resposta.get("erro", "Resposta inválida da API do Asaas")
                messages.error(request, f"Falha ao integrar cobrança do contrato {contrato.id}: {error_msg}")
        except Exception as e:
            messages.error(
                request,
                f"Erro ao integrar cobrança do contrato {contrato.id} com o Asaas: {str(e)}"
            )

    if cobrancas_geradas > 0:
        messages.success(request, f"Cobranças geradas com sucesso! Total: {cobrancas_geradas}")
    else:
        messages.warning(request, "Nenhuma cobrança foi gerada.")

    return redirect('cadastro_cobrancas')

def processar_resposta_asaas(resultado_asaas, contrato, inquilino, valor_total, data_vencimento, descricao, mes_referencia, ano_referencia):

    """
    Processa a resposta da API do Asaas e salva a cobrança no banco de dados
    """
    logger.info(f"Processando resposta do Asaas: {resultado_asaas}")
    
    # Verifica se a resposta é válida e contém um ID
    if resultado_asaas and isinstance(resultado_asaas, dict) and "id" in resultado_asaas:
        # Extrai dados de PIX (que podem estar em diferentes locais dependendo da resposta)
        pix_data = resultado_asaas.get("pixTransaction", {}) or {}
        
        # Se não houver dados de PIX na resposta inicial, pode ser necessário fazer uma solicitação adicional
        # para obter os dados completos do PIX se a cobrança for do tipo BOLETO_PIX
        if not pix_data and resultado_asaas.get("billingType") in ["BOLETO", "UNDEFINED"] and resultado_asaas.get("id"):
            try:
                # Faz uma solicitação adicional para obter os dados do QR code PIX
                payment_id = resultado_asaas["id"]
                pix_url = f"https://www.asaas.com/api/v3/payments/{payment_id}/pixQrCode"
                pix_headers = {
                    'access_token': settings.ASAAS_API_KEY,
                    'Content-Type': 'application/json'
                }
                pix_response = requests.get(pix_url, headers=pix_headers)
                if pix_response.status_code == 200:
                    pix_data = pix_response.json()
                    logger.info(f"Dados PIX obtidos: {pix_data}")
            except Exception as e:
                logger.error(f"Erro ao obter QR code PIX: {str(e)}")
        
        # Cria uma nova cobrança com todos os campos necessários
        nova_cobranca = Cobranca(
            contrato=contrato,
            valor=valor_total,
            data_vencimento=data_vencimento,
            descricao=descricao,
            mes_referencia=mes_referencia,
            ano_referencia=ano_referencia,
            inquilino=inquilino,
            
            # Campos do Asaas
            asaas_id=resultado_asaas.get("id"),
            asaas_payment_id=resultado_asaas.get("id"),
            asaas_boleto_url=resultado_asaas.get("bankSlipUrl"),
            asaas_pix_url=pix_data.get("qrCodeUrl") or pix_data.get("encodedImage"),
            asaas_pix_copia_cola=pix_data.get("payload") or pix_data.get("copy"),
            asaas_pix_qr_code_base64=pix_data.get("base64Image") or pix_data.get("encodedImage"),
            asaas_codigo_barras=resultado_asaas.get("identificationField") or resultado_asaas.get("nossoNumero"),
            asaas_invoice_url=resultado_asaas.get("invoiceUrl"),
            asaas_invoice_number=resultado_asaas.get("invoiceNumber"),
            asaas_status=resultado_asaas.get("status", "PENDING"),
            asaas_status_asaas=resultado_asaas.get("status"),
            asaas_url_fatura=resultado_asaas.get("invoiceUrl"),
        )
        
        # Salva a cobrança
        nova_cobranca.save()
        logger.info(f"Cobrança salva com sucesso. ID: {nova_cobranca.id}, Asaas ID: {nova_cobranca.asaas_id}")
        
        return nova_cobranca, True, None
    else:
        # Adiciona informação de erro
        erro_msg = "Erro desconhecido na integração com Asaas"
        if resultado_asaas and isinstance(resultado_asaas, dict):
            erro_msg = resultado_asaas.get('erro', erro_msg)
        
        # Salva a cobrança com erro
        nova_cobranca = Cobranca(
            contrato=contrato,
            valor=valor_total,
            data_vencimento=data_vencimento,
            descricao=descricao,
            mes_referencia=mes_referencia,
            ano_referencia=ano_referencia,
            inquilino=inquilino,
            status="ERROR"
        )
        nova_cobranca.save()
        
        return nova_cobranca, False, erro_msg
    


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum, F, Value, Case, When, DecimalField, CharField
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.http import JsonResponse
from decimal import Decimal

from .forms import CobrancaFiltroForm, PagamentoForm, RepasseForm
from sisimob.models import Cobranca, MovimentoConta, Cliente



def painel_financeiro(request):
    """
    View principal para gestão financeira centralizada
    """
    
    # Inicializa formulário de filtro com os dados da request ou vazio
    filtro_form = CobrancaFiltroForm(request.GET or None)
    
    # Inicia com todas as cobranças
    cobrancas = Cobranca.objects.all().select_related(
        'contrato', 
        'contrato__imovel', 
        'inquilino'
    ).prefetch_related(
        'contrato__proprietario'
    ).order_by('data_vencimento', 'status')
    
    # Aplica filtros se o formulário for válido
    if filtro_form.is_valid():
        data = filtro_form.cleaned_data
        
        # Filtro por status
        if data.get('status'):
            cobrancas = cobrancas.filter(status=data['status'])
            
        # Filtro por status de repasse
        if data.get('status_repasse'):
            cobrancas = cobrancas.filter(status_repasse=data['status_repasse'])
            
        # Filtro por período
        if data.get('data_inicio') and data.get('data_fim'):
            cobrancas = cobrancas.filter(
                data_vencimento__range=[data['data_inicio'], data['data_fim']]
            )
        elif data.get('data_inicio'):
            cobrancas = cobrancas.filter(data_vencimento__gte=data['data_inicio'])
        elif data.get('data_fim'):
            cobrancas = cobrancas.filter(data_vencimento__lte=data['data_fim'])
            
        # Filtro por proprietário
        if data.get('proprietario'):
            cobrancas = cobrancas.filter(contrato__proprietario=data['proprietario'])
            
        # Filtro por inquilino
        if data.get('inquilino'):
            cobrancas = cobrancas.filter(inquilino=data['inquilino'])
            
        # Filtro por imóvel/contrato
        if data.get('contrato'):
            cobrancas = cobrancas.filter(contrato=data['contrato'])
    
    # Formulários para ações em lote
    pagamento_form = PagamentoForm()
    repasse_form = RepasseForm()
    
    # Resumo dos valores
    resumo = {
        'total_receber': cobrancas.filter(status='pendente').aggregate(
            valor=Coalesce(Sum('valor'), Decimal('0'))
        )['valor'],
        'total_recebido': cobrancas.filter(status='paga').aggregate(
            valor=Coalesce(Sum('valor'), Decimal('0'))
        )['valor'],
        'total_repassar': cobrancas.filter(
            status='paga', 
            status_repasse='pendente'
        ).aggregate(valor=Coalesce(Sum('valor'), Decimal('0')))['valor'],
        'total_atrasado': cobrancas.filter(
            status='atrasada'
        ).aggregate(valor=Coalesce(Sum('valor'), Decimal('0')))['valor'],
    }
    
    contexto = {
        'cobrancas': cobrancas,
        'filtro_form': filtro_form,
        'pagamento_form': pagamento_form,
        'repasse_form': repasse_form,
        'resumo': resumo,
        'hoje': timezone.now().date(),
    }
    
    return render(request, 'financeiro/painel_financeiro.html', contexto)



def registrar_pagamento(request, cobranca_id):
    """
    Registra o pagamento de uma cobrança específica
    """
    cobranca = get_object_or_404(Cobranca, id=cobranca_id)
    
    if request.method == 'POST':
        form = PagamentoForm(request.POST)
        
        if form.is_valid():
            # Atualiza a cobrança
            cobranca.status = 'paga'
            cobranca.data_pagamento = form.cleaned_data['data_pagamento']
            cobranca.save()
            
            # Registra o movimento na conta do proprietário
            for proprietario in cobranca.contrato.proprietario.all():
                MovimentoConta.objects.create(
                    proprietario=proprietario,
                    contrato=cobranca.contrato,
                    tipo='credito',
                    descricao=f"Pagamento de aluguel - {cobranca.mes_referencia}/{cobranca.ano_referencia}",
                    valor=cobranca.valor,
                    data_referencia=cobranca.data_vencimento
                )
            
            messages.success(
                request, 
                f"Pagamento da cobrança #{cobranca_id} registrado com sucesso!"
            )
        else:
            messages.error(request, "Erro ao registrar pagamento. Verifique os dados.")
    
    return redirect('painel_financeiro')



def registrar_repasse(request, cobranca_id):
    """
    Registra o repasse de uma cobrança específica para o proprietário
    """
    cobranca = get_object_or_404(Cobranca, id=cobranca_id)
    
    # Valida se o pagamento foi recebido antes de repassar
    if cobranca.status != 'paga':
        messages.error(
            request, 
            "Não é possível repassar uma cobrança que não foi paga."
        )
        return redirect('painel_financeiro')
    
    if request.method == 'POST':
        form = RepasseForm(request.POST)
        
        if form.is_valid():
            # Atualiza a cobrança
            cobranca.status_repasse = 'repassado'
            cobranca.data_repasse = form.cleaned_data['data_repasse']
            cobranca.save()
            
            # Valor descontando a taxa de administração
            valor_liquido = cobranca.valor_liquido
            
            # Registra o movimento na conta do proprietário
            for proprietario in cobranca.contrato.proprietario.all():
                MovimentoConta.objects.create(
                    proprietario=proprietario,
                    contrato=cobranca.contrato,
                    tipo='repasse',
                    descricao=f"Repasse de aluguel - {cobranca.mes_referencia}/{cobranca.ano_referencia}",
                    valor=valor_liquido,
                    data_referencia=cobranca.data_repasse
                )
            
            messages.success(
                request, 
                f"Repasse da cobrança #{cobranca_id} registrado com sucesso!"
            )
        else:
            messages.error(request, "Erro ao registrar repasse. Verifique os dados.")
    
    return redirect('painel_financeiro')


def cancelar_cobranca(request, cobranca_id):
    """
    Cancela uma cobrança específica
    """
    cobranca = get_object_or_404(Cobranca, id=cobranca_id)
    
    if request.method == 'POST':
        cobranca.status = 'cancelada'
        cobranca.status_repasse = 'cancelado'
        cobranca.save()
        
        messages.success(
            request, 
            f"Cobrança #{cobranca_id} cancelada com sucesso!"
        )
    
    return redirect('painel_financeiro')



def acao_em_lote(request):
    """
    Processa ações em lote para múltiplas cobranças
    """
    if request.method == 'POST':
        acao = request.POST.get('acao')
        ids = request.POST.getlist('cobrancas_selecionadas')
        
        if not ids:
            messages.warning(request, "Nenhuma cobrança selecionada.")
            return redirect('painel_financeiro')
        
        cobrancas = Cobranca.objects.filter(id__in=ids)
        
        if acao == 'marcar_pago':
            # Formulário de pagamento em lote
            form = PagamentoForm(request.POST)
            if form.is_valid():
                data_pagamento = form.cleaned_data['data_pagamento']
                
                for cobranca in cobrancas:
                    if cobranca.status != 'paga':
                        cobranca.status = 'paga'
                        cobranca.data_pagamento = data_pagamento
                        cobranca.save()
                        
                        # Registra o movimento para cada proprietário
                        for proprietario in cobranca.contrato.proprietario.all():
                            MovimentoConta.objects.create(
                                proprietario=proprietario,
                                contrato=cobranca.contrato,
                                tipo='credito',
                                descricao=f"Pagamento de aluguel - {cobranca.mes_referencia}/{cobranca.ano_referencia}",
                                valor=cobranca.valor,
                                data_referencia=cobranca.data_vencimento
                            )
                
                messages.success(request, f"{cobrancas.count()} cobranças marcadas como pagas.")
            else:
                messages.error(request, "Erro ao processar pagamentos em lote.")
                
        elif acao == 'fazer_repasse':
            # Formulário de repasse em lote
            form = RepasseForm(request.POST)
            if form.is_valid():
                data_repasse = form.cleaned_data['data_repasse']
                
                for cobranca in cobrancas:
                    if cobranca.status == 'paga' and cobranca.status_repasse == 'pendente':
                        cobranca.status_repasse = 'repassado'
                        cobranca.data_repasse = data_repasse
                        cobranca.save()
                        
                        valor_liquido = cobranca.valor_liquido
                        
                        # Registra o movimento para cada proprietário
                        for proprietario in cobranca.contrato.proprietario.all():
                            MovimentoConta.objects.create(
                                proprietario=proprietario,
                                contrato=cobranca.contrato,
                                tipo='repasse',
                                descricao=f"Repasse de aluguel - {cobranca.mes_referencia}/{cobranca.ano_referencia}",
                                valor=valor_liquido,
                                data_referencia=data_repasse
                            )
                
                messages.success(request, f"{cobrancas.count()} repasses efetuados com sucesso.")
            else:
                messages.error(request, "Erro ao processar repasses em lote.")
                
        elif acao == 'cancelar':
            count = 0
            for cobranca in cobrancas:
                if cobranca.status != 'cancelada':
                    cobranca.status = 'cancelada'
                    cobranca.status_repasse = 'cancelado'
                    cobranca.save()
                    count += 1
            
            messages.success(request, f"{count} cobranças canceladas com sucesso.")
    
    return redirect('painel_financeiro')



def detalhes_cobranca(request, cobranca_id):
    """
    Retorna os detalhes de uma cobrança específica em formato JSON para uso em modal
    """
    cobranca = get_object_or_404(Cobranca, id=cobranca_id)
    
    dados = {
        'id': cobranca.id,
        'contrato_id': cobranca.contrato.id,
        'endereco_imovel': str(cobranca.contrato.imovel),
        'inquilino': ', '.join([str(inq) for inq in cobranca.contrato.inquilino.all()]),
        'proprietario': ', '.join([str(prop) for prop in cobranca.contrato.proprietario.all()]),
        'valor': float(cobranca.valor),
        'valor_administracao': float(cobranca.valor_administracao),
        'valor_liquido': float(cobranca.valor_liquido),
        'mes_referencia': cobranca.mes_referencia,
        'ano_referencia': cobranca.ano_referencia,
        'data_vencimento': cobranca.data_vencimento.strftime('%d/%m/%Y'),
        'status': cobranca.get_status_display(),
        'status_asaas': cobranca.asaas_status or 'Não disponível',
    }
    
    # Inclui dados de pagamento se já foi pago
    if cobranca.status == 'paga':
        dados.update({
            'data_pagamento': cobranca.data_pagamento.strftime('%d/%m/%Y'),
            'status_repasse': cobranca.get_status_repasse_display(),
        })
        
        # Se já foi repassado, inclui a data
        if cobranca.status_repasse == 'repassado':
            dados['data_repasse'] = cobranca.data_repasse.strftime('%d/%m/%Y')
    
    return JsonResponse(dados)