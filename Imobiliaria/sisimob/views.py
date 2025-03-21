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
from datetime import datetime
from django.apps import apps
from . import rent_calculations
from .rent_calculations import calcular_aluguel_projetado
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from django.http import HttpResponse
import io
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from django.conf import settings
import os
from PIL import Image
from django.urls import reverse

def autocomplete_field(request, model_name, field_name):
    query = request.GET.get('q', '')
    Model = apps.get_model('sisimob', model_name)
    suggestions = Model.objects.filter(
        **{f"{field_name}__icontains": query}  # Ex.: "profissao__icontains": query
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
    # Consulta MongoEngine
    clientes = Cliente.objects.all()  # Retorna todos os clientes
    
    # Paginação
    paginator = Paginator(list(clientes), 10)  # Converta para lista
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Renderiza o template
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
        'plural_name': f"{model_name}s",  # Ex.: 'clientes', 'imoveis'
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

from django.shortcuts import render, get_object_or_404
from .models import Contrato, Cobranca
from decimal import Decimal

def dashboard(request, contrato_id):
    contrato = get_object_or_404(Contrato, id=contrato_id)
    # Calcula o Aluguel Projetado
    aluguel_projetado = contrato.calcular_aluguel_projetado()
    print(f"Aluguel Projetado: {aluguel_projetado}")  # Log para depuração
    
    # Verifica os valores dos campos do contrato
    print(f"Valor Aluguel: {contrato.valor_aluguel}")
    print(f"Valor Condomínio: {contrato.valor_condominio}")
    print(f"Valor IPTU: {contrato.valor_iptu}")
    print(f"Valor Outros: {contrato.valor_outros}")
    print(f"Taxa de Administração: {contrato.valor_taxa_administracao()}")
    
    # Filtra as cobranças com base nos parâmetros da URL (ano e status)
    ano_filtro = request.GET.get('ano')
    status_filtro = request.GET.get('status')
    cobrancas = contrato.cobrancas.all().order_by('ano_referencia', 'mes_referencia')
    if ano_filtro:
        cobrancas = cobrancas.filter(ano_referencia=ano_filtro)
    if status_filtro:
        cobrancas = cobrancas.filter(status=status_filtro)
    
    # Calcula o total
    total = contrato.valor_aluguel + contrato.valor_condominio + contrato.valor_iptu + contrato.valor_outros
    print(f"Total Calculado: {total}")  # Log para depuração
    
    context = {
        'contrato': contrato,
        'aluguel_projetado': aluguel_projetado,
        'cobrancas': cobrancas,
        'total': total,  # Adiciona o total ao contexto
    }
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
    contrato = get_object_or_404(Contrato, id=contrato_id)
    return render(request, 'editar_contrato.html', {'contrato': contrato})  

def cadastro_cobrancas(request):
    # Obtém os contratos ativos
    contratos = Contrato.objects.filter(ativo=True)

    # Dados para o formulário
    meses = [
        {'numero': i, 'nome': datetime(2023, i, 1).strftime('%B')} for i in range(1, 13)
    ]
    ano_atual = datetime.now().year

    if request.method == 'POST':
        mes_referencia = int(request.POST.get('mes_referencia'))
        ano_referencia = int(request.POST.get('ano_referencia'))

        # Verifica se as cobranças já existem
        cobrancas_existentes = Cobranca.objects.filter(
            mes_referencia=mes_referencia,
            ano_referencia=ano_referencia
        )

        if cobrancas_existentes.exists():
            messages.warning(request, "As cobranças para este período já foram geradas. Elas serão atualizadas.")
        else:
            messages.success(request, "Cobranças geradas com sucesso!")

        # Gera ou atualiza as cobranças
        for contrato in contratos:
            dia_pagamento = contrato.dia_pagamento
            data_vencimento = f"{ano_referencia}-{mes_referencia:02d}-{dia_pagamento:02d}"
            valor = contrato.calcular_valor_total()

            Cobranca.objects.update_or_create(
                contrato=contrato,
                mes_referencia=mes_referencia,
                ano_referencia=ano_referencia,
                defaults={
                    'data_vencimento': data_vencimento,
                    'valor': valor,
                    'status': 'pendente'
                }
            )

        # Redireciona para listar as cobranças geradas
        return redirect(reverse('cadastro_cobrancas') + f'?mes={mes_referencia}&ano={ano_referencia}')

    # Filtra as cobranças pelo mês e ano selecionados
    mes_selecionado = request.GET.get('mes')
    ano_selecionado = request.GET.get('ano')

    if mes_selecionado and ano_selecionado:
        cobrancas = Cobranca.objects.filter(
            mes_referencia=int(mes_selecionado),
            ano_referencia=int(ano_selecionado)
        )
    else:
        cobrancas = []

    context = {
        'meses': meses,
        'ano_atual': ano_atual,
        'cobrancas': cobrancas,
    }

    return render(request, 'imoveis/cadastro_cobrancas.html', context)

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

def registrar_pagamento(request, cobranca_id):
    cobranca = get_object_or_404(Cobranca, id=cobranca_id)
    if request.method == 'POST':
        cobranca.status = 'paga'
        cobranca.data_pagamento = timezone.now().date()
        cobranca.save()
        # Lógica para repasse (ex.: após pagamento, marcar como "pendente" para repasse)
        cobranca.status_repasse = 'pendente'
        cobranca.save()
        messages.success(request, 'Pagamento registrado!')
        return redirect('contrato_detail', contrato_id=cobranca.contrato.id)
    
def registrar_repasse(request, cobranca_id):
    cobranca = get_object_or_404(Cobranca, id=cobranca_id)
    if request.method == 'POST':
        cobranca.status_repasse = 'repassado'
        cobranca.data_repasse = timezone.now().date()
        cobranca.save()
        messages.success(request, 'Repasse ao proprietário concluído!')
        return redirect('contrato_detail', contrato_id=cobranca.contrato.id)
    
def cobranca_update(request, pk):
    cobranca = get_object_or_404(Cobranca, pk=pk)
    if request.method == 'POST':
        form = CobrancaForm(request.POST, instance=cobranca)
        if form.is_valid():
            form.save()
            return redirect('dashboard')  # Redirecione para a página desejada
    else:
        form = CobrancaForm(instance=cobranca)
    return render(request, 'contratos/cobranca_form.html', {'form': form})

def calcular_repasse(cobranca):
    contrato = cobranca.contrato
    valor_bruto = cobranca.valor

    # Calcula a taxa de administração
    if contrato.tipo_taxa == 'percentual':
        taxa = valor_bruto * (contrato.valor_taxa_administracao_percentual / 100)
    else:
        taxa = contrato.valor_taxa_administracao_fixo or 0

    # Valor líquido para o proprietário
    valor_liquido = valor_bruto - taxa
    return valor_liquido

def pagar_cobranca(request, pk):
    cobranca = get_object_or_404(Cobranca, pk=pk)
    
    if cobranca.status == 'paga':
        messages.warning(request, "Esta cobrança já foi paga.")
    else:
        cobranca.status = 'paga'
        cobranca.data_pagamento = timezone.now().date()  # Define a data de pagamento
        cobranca.save()
        messages.success(request, "Cobrança marcada como paga com sucesso!")
    
    return redirect('detalhes_contrato', contrato_id=cobranca.contrato.id)

def repassar_valor(request, pk):
    cobranca = get_object_or_404(Cobranca, pk=pk)
    
    if cobranca.status_repasse == 'repassado':
        messages.warning(request, "Este valor já foi repassado.")
    else:
        cobranca.status_repasse = 'repassado'
        cobranca.save()
        messages.success(request, "Valor repassado com sucesso!")
    
    return redirect('detalhes_contrato', contrato_id=cobranca.contrato.id)

def detalhes_contrato(request, contrato_id):
    contrato = get_object_or_404(Contrato, id=contrato_id)
    cobrancas = Cobranca.objects.filter(contrato=contrato)
    return render(request, 'imoveis/detalhes_contrato.html', {
        'contrato': contrato,
        'cobrancas': cobrancas,
    })


def gerar_recibo_pagamento(request, pk):

    cobranca = get_object_or_404(Cobranca, pk=pk)
    
    # Configuração do PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="recibo_pagamento_{cobranca.id}.pdf"'
    
    # Cria o PDF usando ReportLab
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Função auxiliar para adicionar texto formatado
    def draw_text(text, x, y, font_size=12, align='left'):
        p.setFont("Helvetica", font_size)
        if align == 'center':
            p.drawCentredString(x, y, text)
        else:
            p.drawString(x, y, text)
    
    # Cabeçalho do Recibo - Logo
    try:
        from PIL import Image
        logo_path = r"C:\Users\guilh\OneDrive\Pessoal\Documentos\GitHub\Teste\Imobiliaria\sisimob\static\images\logo2.png"
        if os.path.exists(logo_path):
            # Obter dimensões originais da imagem
            img = Image.open(logo_path)
            img_width, img_height = img.size
            
            # Definir a largura máxima desejada
            max_logo_width = 100  # Largura máxima em pontos
            
            # Calcular altura proporcional
            aspect_ratio = img_height / img_width
            logo_width = max_logo_width
            logo_height = logo_width * aspect_ratio
            
            # Calcular posição para centralizar horizontalmente
            x_position = (width - logo_width) / 2
            y_position = height - logo_height - 1 * cm  # 1cm de margem superior
            
            # Desenhar a imagem com proporção mantida
            p.drawImage(
                logo_path,
                x_position,
                y_position,
                width=logo_width,
                height=logo_height,
                preserveAspectRatio=True,  # Garantir que a proporção seja preservada
                mask='auto'  # Configurar máscara para transparência
            )
            
            # Ajustar a posição do título para começar logo abaixo do logo
            title_position = y_position - 1 * cm
    except Exception as e:
        print(f"Erro ao carregar logo: {e}")
        # Se falhar ao carregar logo, posicionar título no topo
        title_position = height - 3 * cm
    
    # Título do Recibo
    draw_text("Recibo de Pagamento", width / 2, title_position, font_size=16, align='center')
    draw_text(f"Cobrança #{cobranca.id}", width / 2, title_position - 1 * cm, font_size=12, align='center')
    
    # Detalhes do Contrato
    content_start = title_position - 2.5 * cm
    
    draw_text("Contrato:", 50, content_start, font_size=12)
    draw_text(f"{cobranca.contrato.imovel.endereco}", 200, content_start, font_size=12)
    
    draw_text("Valor Pago:", 50, content_start - 1 * cm, font_size=12)
    draw_text(f"R$ {cobranca.valor:.2f}", 200, content_start - 1 * cm, font_size=12)
    
    draw_text("Data de Pagamento:", 50, content_start - 2 * cm, font_size=12)
    draw_text(f"{cobranca.data_pagamento.strftime('%d/%m/%Y') if cobranca.data_pagamento else 'N/A'}", 200, content_start - 2 * cm, font_size=12)
    
    draw_text("Status:", 50, content_start - 3 * cm, font_size=12)
    draw_text("Pago", 200, content_start - 3 * cm, font_size=12)
    
    # Rodapé
    draw_text("Este recibo foi gerado automaticamente pelo sistema.", 50, 50, font_size=10)
    
    # Finaliza o PDF
    p.showPage()
    p.save()
    
    # Retorna o PDF como resposta
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
            cobranca.data_pagamento = data_pagamento
            cobranca.status = 'paga'  # Define o status como "Paga"

        # Atualiza a data de repasse
        if data_repasse:
            cobranca.data_repasse = data_repasse
            cobranca.status_repasse = 'repassado'  # Define o status como "Repasse Realizado"

        cobranca.save()
        messages.success(request, "As datas foram atualizadas com sucesso!")

    return redirect(reverse('dashboard', args=[cobranca.contrato.id]))

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from reportlab.lib.pagesizes import letter, portrait
from reportlab.lib.units import cm, mm
from reportlab.lib.colors import black, gray, lightgrey, HexColor
from reportlab.platypus import Table, TableStyle, SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT, TA_JUSTIFY
from reportlab.pdfgen import canvas
from .models import Contrato, Cobranca
from datetime import date
from decimal import Decimal
import io
import os

def gerar_extrato_rendimento(request, contrato_id):
    contrato = get_object_or_404(Contrato, id=contrato_id)
    cobrancas = contrato.cobrancas.filter(status='paga').order_by('ano_referencia', 'mes_referencia')
    
    # Configuração do PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="extrato_rendimento_contrato_{contrato.id}.pdf"'
    
    # Cria o PDF usando ReportLab
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=portrait(letter), 
                         leftMargin=1.5*cm, rightMargin=1.5*cm,
                         topMargin=1.5*cm, bottomMargin=1.5*cm)
    elements = []
    
    # Função auxiliar para formatar valores monetários
    def format_currency(value):
        if value == 0:
            return "R$ 0,00"
        return f'R$ {value:,.2f}'.replace('.', 'X').replace(',', '.').replace('X', ',')
    
    # Estilos de texto
    styles = getSampleStyleSheet()
    
    # Estilo para título principal
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=14,
        alignment=TA_CENTER,
        spaceAfter=0.2*cm
    )
    
    # Estilo para subtítulo
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Heading2'],
        fontSize=12,
        alignment=TA_CENTER,
        spaceAfter=0.5*cm,
        textColor=HexColor('#000000')
    )
    
    # Estilo para texto normal
    normal_style = ParagraphStyle(
    'Normal',
    parent=styles['Normal'],
    fontSize=10,
    alignment=TA_LEFT,
    spaceAfter=0.2*cm,
    leftIndent=0  # Remove left indent
    )
    
    # Estilo para cabeçalho de seção
    section_style = ParagraphStyle(
        'Section',
        parent=styles['Heading3'],
        fontSize=11,
        alignment=TA_LEFT,
        spaceAfter=0.2*cm,
        textColor=HexColor('#000000')
    )
    
    
    logo_path = r"C:\Users\guilh\OneDrive\Pessoal\Documentos\GitHub\Teste\Imobiliaria\sisimob\static\images\logo2.png"
    logo = Image(logo_path, width=5*cm, height=2*cm, kind='proportional')
    elements.append(logo)

    
    elements.append(Spacer(1, 0.3 * cm))
    
    # Adicionar cabeçalho
    elements.append(Paragraph("<b>COMPROVANTE ANUAL DE RENDIMENTOS DE ALUGUÉIS</b>", title_style))
    ano_atual = date.today().year
    elements.append(Paragraph(f"<b>Ano-calendário: {ano_atual-1}</b>", subtitle_style))
    elements.append(Spacer(1, 0.3 * cm))

    # Dados do imóvel
    
    endereco = f"{contrato.imovel.endereco}"
    if hasattr(contrato.imovel, 'numero') and contrato.imovel.numero:
        endereco += f", {contrato.imovel.numero}"
    if hasattr(contrato.imovel, 'complemento') and contrato.imovel.complemento:
        endereco += f" - {contrato.imovel.complemento}"
    if hasattr(contrato.imovel, 'bairro') and contrato.imovel.bairro:
        endereco += f" - {contrato.imovel.bairro}"

    imovel_data = [
        [f"<b>Número do contrato:</b> {contrato.id}", f"<b>Início do contrato:</b> {contrato.data_inicio.strftime('%d/%m/%Y')}", f"<b>Tipo do imóvel:</b> Urbano"],
    ]

    # Add address row with colspan
    endereco_row = [[f"<b>Endereço do imóvel:</b> {endereco}"]]
    imovel_data.extend(endereco_row)

    # Add location data row
    imovel_data.append([f"<b>UF:</b> {contrato.imovel.estado}", f"<b>Município:</b> {contrato.imovel.cidade}", f"<b>CEP:</b> {contrato.imovel.cep}"])

    # Create table with appropriate widths
    imovel_table = Table(
        [[Paragraph(cell, normal_style) for cell in row] for row in imovel_data], 
        colWidths=[6*cm, 6*cm, 6*cm]
    )

    # Set table style with proper spans
    imovel_table.setStyle(TableStyle([
    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ('LEFTPADDING', (0, 0), (-1, -1), 0),  # Remove left padding
    ('TOPPADDING', (0, 0), (-1, -1), 1),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
    ('SPAN', (0, 1), (2, 1)),  # This spans all columns for the address row
    ]))
    
    elements.append(imovel_table)
    elements.append(Spacer(1, 0.5 * cm))


    
    # Informações da imobiliária
    elements.append(Paragraph("<b>CNPJ da Administradora do imóvel (Imobiliária):</b> 55.507.744/0001-99", normal_style))
    elements.append(Paragraph("<b>Nome:</b> Palestra Imóveis", normal_style))
    elements.append(Paragraph("<b>Endereço:</b> Rua Serra de Bragança, 1814, Vila Gomes Cardim, São Paulo-SP, CEP 03318-000", normal_style))
    elements.append(Spacer(1, 0.5 * cm))
    
    
    
    
    
    # Informações do locador e locatário
    elements.append(Paragraph("<b>Locador:</b> " + contrato.proprietario.nome + " - CPF: ", normal_style))
    elements.append(Paragraph("<b>Locatário:</b> " + contrato.inquilino.nome + " - CPF: ", normal_style))
    elements.append(Spacer(1, 0.5 * cm))
    
    # Tabela de valores mensais com coluna de meses
    meses = {
        1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 
        5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto', 
        9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
    }
    
    # Inicializar cabeçalho da tabela
    header = ["Mês", "Rendimento Bruto", "Valor Comissão", "Imposto Retido"]
    data = [header]
    
    # Inicializar valores
    valores_por_mes = {mes: [0, 0, 0] for mes in range(1, 13)}
    
    # Preencher com os valores das cobranças
    for cobranca in cobrancas:
        mes = cobranca.mes_referencia
        valores_por_mes[mes][0] = cobranca.valor  # Valor do aluguel
        valores_por_mes[mes][1] = contrato.valor_taxa_administracao()  # Taxa de administração
        valores_por_mes[mes][2] = 0  # Imposto retido (não usado no exemplo, mas mantido para o layout)
    
    # Adicionar linha por mês
    total_aluguel = 0
    total_taxa = 0
    total_imposto = 0
    
    # Modify the mês/ano row generation to remove the year
    for mes_num in range(1, 13):
        mes_nome = f"{meses[mes_num]}"  # Removed /{ano_atual-1}
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
    
    # Adicionar linha de totais
    data.append([
        "TOTAL", 
        format_currency(total_aluguel), 
        format_currency(total_taxa), 
        format_currency(total_imposto)
    ])
    
    # Criar tabela de valores
    valores_table = Table(data, colWidths=[4*cm, 5*cm, 5*cm, 4*cm])
    
    # Estilo da tabela
    valores_style = TableStyle([
    # Cabeçalho
    ('BACKGROUND', (0, 0), (-1, 0), HexColor('#f2f2f2')),
    ('TEXTCOLOR', (0, 0), (-1, 0), black),
    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (-1, 0), 10),
    
    # Bordas
    ('GRID', (0, 0), (-1, -1), 0.5, black),
    ('BOX', (0, 0), (-1, -1), 1, black),
    
    # Center all cells
    ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
    
    # Destacar a linha de totais
    ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
    ('BACKGROUND', (0, -1), (-1, -1), HexColor('#f2f2f2')),
    ])
    
    valores_table.setStyle(valores_style)
    elements.append(valores_table)
    elements.append(Spacer(1, 0.5 * cm))
    
    # Nota de atenção (como no modelo)
    atencao_style = ParagraphStyle(
        'Atencao',
        parent=styles['Normal'],
        fontSize=9,
        alignment=TA_JUSTIFY,
        spaceAfter=0.2*cm
    )
    
    elements.append(Paragraph("<b>Atenção:</b>", atencao_style))
    elements.append(Paragraph("Para a inclusão na Declaração do Imposto de Renda da Pessoa Física - DIRPF dos rendimentos informados neste documento, certifique-se de que os mesmos não constam de outro comprovante emitido pela fonte pagadora.", atencao_style))
    
    # Gera o PDF
    doc.build(elements)
    
    # Retorna o PDF como resposta
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    return response