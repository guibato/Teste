from django.shortcuts import render, get_object_or_404, redirect, reverse
from django.contrib import messages
from django.contrib.auth import logout
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .forms import ClienteForm, ImovelForm, ContratoForm, GerarCobrancasForm, CobrancaForm, DespesaForm  # Importe DespesaForm aqui
from .models import Cliente, Imovel, Contrato, Cobranca, Despesa, IndiceInflacao
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


class ContratoListView(ListView):
    model = Contrato
    paginate_by = 10  # Número de itens por página
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
            form.save()
            messages.success(request, "Cliente cadastrado com sucesso!")
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
    paginate_by = 10
    context_object_name = 'page_obj'

    def get_queryset(self):
        queryset = Contrato.objects.select_related('proprietario', 'inquilino', 'imovel').all()
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

    return redirect('dashboard', contrato_id=cobranca.contrato.id)

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
from datetime import date
from dateutil.relativedelta import relativedelta
from django.shortcuts import render, redirect
from django.contrib import messages
from sisimob.models import Contrato, Despesa, Cobranca
from sisimob.utils.cobrancas_asaas import gerar_cobranca  # Certifique-se de que esta importação está correta

# Configuração para forçar saída imediata para logs
sys.stdout.flush()

def gerar_cobrancas_view(request):
    if request.method == "POST":
        mes_referencia = int(request.POST.get("mes_referencia"))
        ano_referencia = int(request.POST.get("ano_referencia"))
        data_referencia = date(ano_referencia, mes_referencia, 1)

        contratos = Contrato.objects.all()
        cobrancas_geradas = 0

        for contrato in contratos:
            valor_fixo = contrato.valor_aluguel or contrato.valor_pacote or 0  

            # Esta é a consulta aprimorada que corrige o problema do IPTU
            despesas = Despesa.objects.filter(
                contrato=contrato,
                data_inicio__year=ano_referencia,
                data_inicio__month=mes_referencia  # Considera despesas iniciadas no mês de referência
            ) | Despesa.objects.filter(
                contrato=contrato,
                data_inicio__lte=data_referencia  # Também pega despesas que começaram antes do mês
            )

            # Filtrar despesas ativas e separar por tipo
            despesas_ativas = []
            despesas_repassadas = 0
            despesas_deduzidas = 0

            for despesa in despesas:
                if despesa.numero_parcelas is None:  # Se for recorrente, sempre válida
                    despesas_ativas.append(despesa)
                else:
                    # Calcular o último mês da despesa
                    data_fim_despesa = despesa.data_inicio + relativedelta(months=despesa.numero_parcelas - 1)
                    
                    # Verificar se a despesa ainda está válida no mês de referência
                    if data_fim_despesa >= data_referencia:
                        despesas_ativas.append(despesa)

            # Calcular valores de despesas repassadas e deduzidas
            for despesa in despesas_ativas:
                valor_parcela = despesa.calcular_valor_parcela()
                if hasattr(despesa, 'tipo') and despesa.tipo == 'deduzida':
                    despesas_deduzidas += valor_parcela
                else:
                    # Se não tiver tipo ou for 'repassada'
                    despesas_repassadas += valor_parcela

            valor_base_administracao = contrato.valor_aluguel or contrato.valor_pacote or 0  
            valor_total_cobranca = valor_base_administracao + despesas_repassadas - despesas_deduzidas

            # Definir data de vencimento
            dia_vencimento = contrato.dia_pagamento
            try:
                data_vencimento = data_referencia.replace(day=dia_vencimento)
            except ValueError:
                ultimo_dia_mes = (data_referencia.replace(month=data_referencia.month + 1, day=1) - timedelta(days=1)).day
                data_vencimento = data_referencia.replace(day=ultimo_dia_mes)

            # Evitar duplicação de cobrança
            if not Cobranca.objects.filter(
                contrato=contrato,
                mes_referencia=mes_referencia,
                ano_referencia=ano_referencia
            ).exists():
                # Cria a cobrança com os campos que existem no modelo
                cobranca = Cobranca.objects.create(
                    contrato=contrato,
                    valor=valor_total_cobranca,
                    data_vencimento=data_vencimento,
                    mes_referencia=mes_referencia,
                    ano_referencia=ano_referencia,
                )
                
                # Adiciona os valores como atributos temporários (não salvos no banco)
                # Isso permite que o template acesse esses valores na sessão atual
                cobranca.despesas_repassadas = despesas_repassadas
                cobranca.despesas_deduzidas = despesas_deduzidas
                
                print(f"🔧 Tentando gerar cobrança no Asaas para {contrato.inquilino.nome} (ID: {contrato.inquilino.asaas_id})")
                
                if contrato.inquilino and contrato.inquilino.asaas_id:
                    try:
                        # Chamada para o Asaas
                        resposta = gerar_cobranca(
                            asaas_id=contrato.inquilino.asaas_id,
                            valor=float(valor_total_cobranca),
                            vencimento=data_vencimento.strftime('%Y-%m-%d'),
                            nome=contrato.inquilino.nome
                        )
                        print(f"🔧 Resposta do Asaas: {resposta}")
                        
                        if resposta and "id" in resposta:
                            print(f"✅ SUCESSO: Cobrança enviada ao Asaas! ID: {resposta['id']}")
                            
                            # Atualiza os dados da cobrança
                            cobranca.asaas_payment_id = resposta["id"]
                            cobranca.asaas_boleto_url = resposta.get("bankSlipUrl")
                            cobranca.asaas_pix_copia_cola = resposta.get("pix", {}).get("payload")
                            cobranca.asaas_pix_url = resposta.get("pix", {}).get("qrCodeUrl")
                            cobranca.asaas_codigo_barras = resposta.get("identificationField")
                            cobranca.save()
                            print(f"💾 Dados da cobrança atualizados no banco de dados")
                        else:
                            print(f"❌ ERRO: Falha ao enviar para Asaas: {resposta}")
                            messages.error(request, f"Falha ao enviar cobrança para Asaas: {resposta}")
                    except Exception as e:
                        print(f"❌ ERRO na integração com Asaas: {str(e)}")
                        traceback.print_exc()
                        messages.error(request, f"Erro ao integrar com o Asaas: {str(e)}")
                else:
                    print(f"⚠️ Inquilino sem Asaas ID: {contrato.inquilino}")
                    messages.warning(request, f"Inquilino {contrato.inquilino.nome} sem ID do Asaas.")
                
                cobrancas_geradas += 1

        # Mensagem de sucesso
        messages.success(request, f"Cobranças geradas com sucesso! Total: {cobrancas_geradas}")
        
        # Redirecionar para a mesma página, mantendo os parâmetros de mês e ano
        return redirect(f"/gerar-cobrancas/?mes={mes_referencia}&ano={ano_referencia}")

    # Para requisições GET
    hoje = date.today()
    meses = [{"numero": i, "nome": date(hoje.year, i, 1).strftime("%B")} for i in range(1, 13)]
    
    # Pegar parâmetros da URL para manter a seleção após redirecionamento
    mes_selecionado = request.GET.get("mes", hoje.month)
    ano_selecionado = request.GET.get("ano", hoje.year)
    
    # Filtrar cobranças pelo mês e ano selecionados, se existirem
    cobrancas = Cobranca.objects.all()
    if mes_selecionado and ano_selecionado:
        try:
            mes_selecionado = int(mes_selecionado)
            ano_selecionado = int(ano_selecionado)
            cobrancas = cobrancas.filter(
                mes_referencia=mes_selecionado,
                ano_referencia=ano_selecionado
            )
        except ValueError:
            # Em caso de valores inválidos, não filtra
            pass
    
    context = {
        "meses": meses,
        "mes_atual": int(mes_selecionado),
        "ano_atual": int(ano_selecionado),
        "cobrancas": cobrancas.order_by("-data_vencimento"),
    }
    return render(request, "imoveis/cadastro_cobrancas.html", context)

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

    return redirect('dashboard', contrato_id=contrato_id)  # Redireciona corretamente


