# Built-in
import os
import io
import json
import sys
import threading
import traceback
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from moneyed import Money, CurrencyDoesNotExist
from collections import OrderedDict


# Django
from django.apps import apps
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import F, Q, Sum
from django.http import HttpResponse, JsonResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView
from django.db.models.functions import TruncMonth

# Terceiros
import pandas as pd
from PIL import Image
from djmoney.money import Money
from dateutil.relativedelta import relativedelta
from reportlab.lib.pagesizes import letter, portrait
from reportlab.lib.units import cm, mm
from reportlab.lib.colors import black, gray, lightgrey, HexColor
from reportlab.platypus import Table, TableStyle, SimpleDocTemplate, Paragraph, Spacer, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT, TA_JUSTIFY
from reportlab.pdfgen import canvas

# Apps locais - models
from .models import (
    Cliente, Imovel, Contrato, Cobranca, Despesa,
    IndiceInflacao, MovimentoConta, LancamentoContaCorrente, Reajuste, LembreteEnviado
)

# Apps locais - forms
from .forms import (
    ClienteForm, ImovelForm, ContratoForm,
    GerarCobrancasForm, CobrancaForm, DespesaForm
)

# Apps locais - utils e serviços
from .utils import atualizar_indices_inflacao
from .utils.cobrancas_asaas import gerar_cobranca
from .utils.integracao_asaas import cadastrar_cliente_no_asaas
from .utils.extrato import gerar_extrato_rendimento
from .utils.pdf import gerar_pdf_extrato_repasses
from .gerar_extrato_repasses_pdf import gerar_extrato_repasses_pdf
from .rent_calculations import calcular_aluguel_projetado
from .services.zapi import enviar_mensagem
from sisimob.utils import calcular_fator_acumulado_com_historico, calcular_valor_reajustado
from sisimob.utils.reajuste import calcular_reajuste
from sisimob.services.notificacao import gerar_mensagem_cobranca


def safe_money(valor, currency='BRL'):
    try:
        # Verificar se o valor é nulo ou inválido
        if valor in [None, '', 'null', '--']:
            return Money(0, currency)
        
        # Garantir que o valor seja do tipo adequado antes de converter para Decimal
        if isinstance(valor, (int, float)):
            valor = str(valor)

        return Money(Decimal(str(valor).replace(',', '.')), currency)
    except (ValueError, TypeError, InvalidOperation):
        return Money(0, currency)


def format_currency_br(value):
    if isinstance(value, Money):
        value = value.amount
    if value is None:
        value = Decimal('0.00')
    return f"R$ {value:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")

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
    hoje = now().date()
    mes = hoje.month
    ano = hoje.year
    seis_meses_atras = hoje - timedelta(days=180)

    total_clientes = Cliente.objects.count()
    total_imoveis = Imovel.objects.count()
    total_contratos_ativos = Contrato.objects.filter(ativo=True).count()
    total_pendencias = Cobranca.objects.filter(
        data_vencimento__lt=hoje,
        status__in=['pendente', 'atrasada']
    ).count()

    # Indicadores financeiros
    receita_prevista = Cobranca.objects.filter(
        data_vencimento__month=mes,
        data_vencimento__year=ano
    ).aggregate(total=Sum('valor'))['total'] or 0

    receita_recebida = Cobranca.objects.filter(
        data_pagamento__month=mes,
        data_pagamento__year=ano,
        status='paga'
    ).aggregate(total=Sum('valor'))['total'] or 0

    cobrancas_em_aberto = Cobranca.objects.filter(
        status__in=['pendente', 'atrasada']
    ).aggregate(total=Sum('valor'))['total'] or 0

    repasses_pendentes = Cobranca.objects.filter(
        status='paga',
        status_repasse='pendente'
    ).aggregate(total=Sum('valor'))['total'] or 0

    repasses_realizados = Cobranca.objects.filter(
        data_repasse__month=mes,
        data_repasse__year=ano,
        status_repasse='repassado'
    ).aggregate(total=Sum('valor'))['total'] or 0

    receitas_mensais = (
        Cobranca.objects.filter(data_pagamento__gte=seis_meses_atras, status='paga')
        .annotate(mes=TruncMonth('data_pagamento'))
        .values('mes')
        .annotate(total=Sum('valor'))
        .order_by('mes')
    )

    labels = []
    valores = []

    for item in receitas_mensais:
        labels.append(item['mes'].strftime('%b/%Y'))
        valores.append(float(item['total'] or 0))





    context = {
        'total_clientes': total_clientes,
        'total_imoveis': total_imoveis,
        'total_contratos_ativos': total_contratos_ativos,
        'total_pendencias': total_pendencias,
        'receita_prevista': receita_prevista,
        'receita_recebida': receita_recebida,
        'cobrancas_em_aberto': cobrancas_em_aberto,
        'repasses_pendentes': repasses_pendentes,
        'repasses_realizados': repasses_realizados,
        'grafico_labels': labels,
        'grafico_valores': valores,
    }

    return render(request, 'imoveis/home.html', context)

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
            
            print(f"🔧 Tentando cadastrar cliente {cliente.nome_exibicao} no Asaas")
            
            try:
                # Chamada para o Asaas
                resposta = cadastrar_cliente_no_asaas(cliente)
                print(f"🔧 Resposta do Asaas: {resposta}")
                
                if resposta:  # Verifica se o ID do Asaas foi retornado
                    print(f"✅ SUCESSO: Cliente {cliente.nome_exibicao} cadastrado no Asaas! ID: {resposta}")
                    
                    # Atualiza o cliente com o asaas_id
                    cliente.asaas_id = resposta
                    cliente.save()
                    print(f"💾 Dados do cliente atualizados no banco de dados")
                    
                    messages.success(request, "Cliente cadastrado com sucesso!")
                else:
                    print(f"❌ ERRO: Falha ao cadastrar cliente {cliente.nome_exibicao} no Asaas")
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
        try:
            # Cria uma cópia do POST para modificar
            post_data = request.POST.copy()
            
            # Lista de todos os campos monetários
            money_fields = [
                'valor_aluguel', 'valor_pacote', 'valor_taxa_administracao_fixo',
                'valor_caucao', 'valor_segfi', 'valor_cap'
            ]
            
            # Força definir os campos de moeda como BRL
            for field in money_fields:
                currency_field = f'{field}_currency'
                post_data[currency_field] = 'BRL'
                
                # Se o campo de valor estiver vazio, define como 0
                amount_field = field
                if amount_field in post_data and not post_data[amount_field]:
                    post_data[amount_field] = '0'
            
            # Cria o formulário com os dados modificados
            form = ContratoForm(post_data, request.FILES)
            
            # Tenta validar o formulário
            if form.is_valid():
                # Antes de salvar, garante que todos os campos Money têm moeda BRL
                contrato = form.save(commit=False)
                for field in money_fields:
                    valor = getattr(contrato, field)
                    if valor is None:
                        setattr(contrato, field, Money(0, 'BRL'))
                    elif not hasattr(valor, 'currency') or not valor.currency:
                        try:
                            valor_decimal = Decimal(str(valor)) if valor else Decimal('0')
                            setattr(contrato, field, Money(valor_decimal, 'BRL'))
                        except:
                            setattr(contrato, field, Money(0, 'BRL'))
                
                # Agora salva com segurança
                contrato.save()
                messages.success(request, "Contrato cadastrado com sucesso!")
                return redirect('listar_contratos')
            else:
                # Se o formulário tiver erros
                for field in form.errors:
                    print(f"Erro no campo {field}: {form.errors[field]}")
                messages.error(request, "Por favor, corrija os erros no formulário.")
                return render(request, 'imoveis/cadastro_contrato.html', {'form': form})
                
        except CurrencyDoesNotExist as e:
            # Captura o erro específico de moeda
            print(f"Erro de moeda: {e}")
            messages.error(request, "Erro na moeda. Tente novamente.")
            form = ContratoForm()
            return render(request, 'imoveis/cadastro_contrato.html', {'form': form})
            
        except Exception as e:
            # Captura qualquer outro erro
            print(f"Erro: {e}")
            messages.error(request, f"Ocorreu um erro: {e}")
            form = ContratoForm()
            return render(request, 'imoveis/cadastro_contrato.html', {'form': form})
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

def dashboard(request, id):
    contrato = get_object_or_404(Contrato, id=id)
    aluguel_projetado = contrato.calcular_aluguel_projetado()
    print(f"Aluguel projetado: {aluguel_projetado}, Tipo: {type(aluguel_projetado)}")

    ano_filtro = request.GET.get('ano')
    status_filtro = request.GET.get('status')
    # Cobrancas base
    cobrancas = contrato.cobrancas.all().order_by('ano_referencia', 'mes_referencia')
    if ano_filtro:
        cobrancas = cobrancas.filter(ano_referencia=int(ano_filtro))
    if status_filtro:
        cobrancas = cobrancas.filter(status=status_filtro)

    total = contrato.calcular_valor_total()
    print(f"Total: {total}, Tipo: {type(total)}")
    historico_aluguel = contrato.historico_aluguel or {}
    despesas = contrato.despesas.all().order_by('data_inicio')
    despesa_form = DespesaForm()

    # Receitas totais pagas
    total_receitas = contrato.cobrancas.filter(status='paga').aggregate(
        total=Sum('valor')
    )['total'] or Money(0, 'BRL')
    print(f"Total Receitas: {total_receitas}, Tipo: {type(total_receitas)}")

    # Despesas totais pagas
    total_despesas = Money(0, 'BRL')
    for cobranca in cobrancas:
        if cobranca.status == 'paga':
            valor_liquido = cobranca.valor - cobranca.valor_administracao
            print(f"Valor Líquido Cobrança: {valor_liquido}, Tipo: {type(valor_liquido)}")
            total_despesas += valor_liquido
    print(f"Total Despesas: {total_despesas}, Tipo: {type(total_despesas)}")

    saldo = total_receitas - total_despesas
    print(f"Saldo: {saldo}, Tipo: {type(saldo)}")

    # Corrigir taxa nula
    if contrato.tipo_taxa == Contrato.valor_taxa_administracao_percentual and not contrato.valor_taxa_administracao_percentual:
        contrato.valor_taxa_administracao_percentual = Decimal('0.00')
        contrato.save()
    elif contrato.tipo_taxa == Contrato.valor_taxa_administracao_fixo and not contrato.valor_taxa_administracao_fixo:
        contrato.valor_taxa_administracao_fixo = Money(0, 'BRL')
        contrato.save()

    anos_disponiveis = contrato.cobrancas.dates('data_vencimento', 'year').distinct()
    context = {
        'contrato': contrato,
        'aluguel_projetado': format_currency_br(aluguel_projetado),
        'cobrancas': cobrancas,
        'total': format_currency_br(total),
        'historico_aluguel': historico_aluguel,
        'despesas': despesas,
        'despesa_form': despesa_form,
        'periodo': f"{date.today().year}",
        'ano_selecionado': ano_filtro,
        'status_selecionado': status_filtro,
        'anos_disponiveis': anos_disponiveis,
        # Valores formatados
        'total_receitas': format_currency_br(total_receitas),
        'total_despesas': format_currency_br(total_despesas),
        'saldo': format_currency_br(saldo),
        'contrato_valor_caucao': format_currency_br(contrato.valor_caucao or Money(0, 'BRL')),
        'contrato_valor_aluguel': format_currency_br(contrato.valor_aluguel or Money(0, 'BRL')),
        'contrato_valor_taxa_administracao_fixo': format_currency_br(contrato.valor_taxa_administracao_fixo or Money(0, 'BRL')),
        'contrato_valor_taxa_administracao_percentual': contrato.valor_taxa_administracao_percentual or Decimal('0.00'),
    }
    # Saldo numérico (float) e sinal
    context['saldo_numerico'] = float(saldo.amount)
    context['saldo_positivo'] = saldo.amount >= 0
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
            return redirect('listar_contratos')
    else:
        form = ContratoForm(instance=contrato)
    return render(request, 'imoveis/editar_contrato.html', {
        'form': form,
        'titulo': 'Editar Contrato',
        'botao_acao': 'Atualizar'
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

sys.stdout.flush()
def gerar_cobrancas_view(request):
    if request.method == "POST":
        mes_referencia = int(request.POST.get("mes_referencia"))
        ano_referencia = int(request.POST.get("ano_referencia"))
        data_referencia = date(ano_referencia, mes_referencia, 1)

        contratos = Contrato.objects.all()
        cobrancas_geradas = 0

        for contrato in contratos:
            # Usa .amount para obter o valor decimal do objeto Money
            valor_fixo_amount = (contrato.valor_aluguel.amount if contrato.valor_aluguel else 0) or \
                               (contrato.valor_pacote.amount if contrato.valor_pacote else 0) or 0  

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
            despesas_repassadas = Decimal('0.00')
            despesas_deduzidas = Decimal('0.00')

            for despesa in despesas:
                if despesa.numero_parcelas is None:  # Se for recorrente, sempre válida
                    despesas_ativas.append(despesa)
                else:
                    # Calcular o último mês da despesa
                    data_fim_despesa = despesa.data_inicio + relativedelta(months=despesa.numero_parcelas - 1)
                    
                    # Verificar se a despesa ainda está válida no mês de referência
                    if data_fim_despesa >= data_referencia:
                        despesas_ativas.append(despesa)

            despesas_repassadas = Decimal('0.00')
            despesas_deduzidas = Decimal('0.00')

            for despesa in despesas_ativas:
                # Calcular o valor da parcela
                valor_parcela_amount = despesa.calcular_valor_parcela().amount
                
                # Verifica quem paga a despesa para determinar se é repassada ou deduzida
                if despesa.paga == 'inquilino':
                    # Despesas pagas pelo inquilino são adicionadas à cobrança
                    despesas_repassadas += valor_parcela_amount
                elif despesa.paga in ['proprietario', 'imobiliaria']:
                    # Despesas pagas pelo proprietário ou imobiliária são deduzidas da cobrança
                    despesas_deduzidas += valor_parcela_amount


            # Usa .amount para obter o valor decimal do objeto Money
            valor_base_administracao_amount = (contrato.valor_aluguel.amount if contrato.valor_aluguel else 0) or \
                                             (contrato.valor_pacote.amount if contrato.valor_pacote else 0) or 0
            
            # Calcular valor total como Decimal
            valor_total_cobranca_amount = valor_base_administracao_amount + despesas_repassadas - despesas_deduzidas
            
            # Criar um objeto Money com a moeda padrão (geralmente BRL para o Brasil)
            from djmoney.money import Money
            valor_total_cobranca = Money(valor_total_cobranca_amount, 'BRL')

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
                # Montar a descrição detalhada da cobrança
                descricao_itens = [f"Aluguel ({mes_referencia}/{ano_referencia}) - R$ {valor_base_administracao_amount:.2f}"]

            for despesa in despesas_ativas:
                valor_parcela = despesa.calcular_valor_parcela()
                
                # Formata o texto da parcela para IPTU, se aplicável
                if despesa.tipo == 'iptu':
                    meses_passados = (ano_referencia - despesa.data_inicio.year) * 12 + (mes_referencia - despesa.data_inicio.month) + 1
                    numero_parcela = min(meses_passados, despesa.numero_parcelas)
                    descricao_despesa = f"IPTU ({numero_parcela}/{despesa.numero_parcelas})"
                else:
                    descricao_despesa = despesa.descricao or despesa.get_tipo_display()
                
                # Adiciona sinal de + ou - dependendo de quem paga
                if despesa.paga == 'inquilino':
                    descricao_itens.append(f"+ {descricao_despesa} - R$ {valor_parcela.amount:.2f}")
                else:
                    descricao_itens.append(f"- {descricao_despesa} - R$ {valor_parcela.amount:.2f}")
                            
                descricao = ", ".join(descricao_itens)
                
                # Cria a cobrança com os campos que existem no modelo
                cobranca = Cobranca.objects.create(
                    contrato=contrato,
                    valor=valor_total_cobranca,  # Agora é um objeto Money
                    data_vencimento=data_vencimento,
                    mes_referencia=mes_referencia,
                    ano_referencia=ano_referencia,
                    descricao=descricao  # Adiciona a descrição detalhada
                )
                
                # Adiciona os valores como atributos temporários (não salvos no banco)
                # Isso permite que o template acesse esses valores na sessão atual
                # Convertemos para Money para manter a consistência
                cobranca.despesas_repassadas = Money(despesas_repassadas, 'BRL')
                cobranca.despesas_deduzidas = Money(despesas_deduzidas, 'BRL')
                
                print(f"🔧 Tentando gerar cobrança no Asaas para {contrato.inquilino.nome} (ID: {contrato.inquilino.asaas_id})")
                
                if contrato.inquilino and contrato.inquilino.asaas_id:
                    try:
                        # Chamada para o Asaas - precisa converter Money para float
                        resposta = gerar_cobranca(
                            asaas_id=contrato.inquilino.asaas_id,
                            valor=float(valor_total_cobranca.amount),  # Converte para float
                            vencimento=data_vencimento.strftime('%Y-%m-%d'),
                            nome=contrato.inquilino.nome,
                            descricao=descricao  # Passa a descrição detalhada
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


def extrato(request):
    proprietarios = Cliente.objects.filter(tipo='Proprietario').order_by('nome')
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
        proprietario = proprietarios.get(id=proprietario_id)
        contratos = Contrato.objects.filter(proprietario=proprietario)

        imoveis_dict = {}

        for contrato in contratos:
            imovel = contrato.imovel
            if imovel.id not in imoveis_dict:
                situacao = getattr(imovel, 'situacao', None) or getattr(imovel, 'status', 'desconhecido')
                status_display = getattr(imovel, 'get_situacao_display', lambda: getattr(imovel, 'get_status_display', lambda: 'Desconhecido'))()
                imoveis_dict[imovel.id] = {
                    'id': imovel.id,
                    'endereco': getattr(imovel, 'endereco', ''),
                    'status': situacao,
                    'get_status_display': status_display,
                    'receitas': Money(0, 'BRL'),
                    'despesas': Money(0, 'BRL'),
                    'repasses': Money(0, 'BRL'),
                    'saldo': Money(0, 'BRL'),
                }

        lancamentos = []

        cobrancas = Cobranca.objects.filter(
            contrato__proprietario=proprietario,
            data_pagamento__range=(data_inicial, data_final),
            status='paga'
        ).select_related('contrato__imovel', 'contrato')

        total_cobrancas_pagas = cobrancas.count()

        for cobranca in cobrancas:
            imovel = cobranca.contrato.imovel
            data = cobranca.data_pagamento
            mes_ano = f"{cobranca.mes_referencia:02d}/{cobranca.ano_referencia}"
            contrato = cobranca.contrato

            valor_aluguel_contrato = safe_money(contrato.valor_aluguel.amount if contrato.valor_aluguel else 0)
            valor_admin = safe_money(cobranca.valor_administracao.amount if cobranca.valor_administracao else 0)
            valor_cobranca_total = safe_money(cobranca.valor.amount if cobranca.valor else 0)
            valor_encargos = valor_cobranca_total - valor_aluguel_contrato

            if imovel.id in imoveis_dict:
                imoveis_dict[imovel.id]['receitas'] += valor_aluguel_contrato
                imoveis_dict[imovel.id]['despesas'] += valor_admin

            lancamentos.append({
                'data': data,
                'descricao': f'Aluguel {mes_ano}',
                'tipo': 'RECEITA',
                'get_tipo_display': 'Receita',
                'valor': valor_aluguel_contrato,
                'imovel': imovel,
            })

            lancamentos.append({
                'data': data,
                'descricao': f'Taxa de Administração {mes_ano}',
                'tipo': 'DESPESA',
                'get_tipo_display': 'Despesa',
                'valor': valor_admin,
                'imovel': imovel,
            })

        despesas = Despesa.objects.filter(
            contrato__proprietario=proprietario,
            data_inicio__lte=data_final,
        ).select_related('contrato__imovel')

        total_despesas_pagas = despesas.count()

        for despesa in despesas:
            imovel = despesa.contrato.imovel
            qtd_parcelas = despesa.numero_parcelas or 1
            valor_parcela = safe_money(despesa.valor_total.amount if despesa.valor_total else 0) / qtd_parcelas

            for parcela in range(qtd_parcelas):
                data_parcela = despesa.data_inicio + timezone.timedelta(days=parcela * 30)
                if data_inicial <= data_parcela <= data_final:
                    responsavel = getattr(despesa, 'paga', 'proprietario')
                    tipo_lancamento = 'RECEITA' if responsavel == 'inquilino' else 'DESPESA'
                    tipo_display = 'Receita' if tipo_lancamento == 'RECEITA' else 'Despesa'

                    if imovel.id in imoveis_dict:
                        if tipo_lancamento == 'RECEITA':
                            imoveis_dict[imovel.id]['receitas'] += valor_parcela
                        else:
                            imoveis_dict[imovel.id]['despesas'] += valor_parcela

                    lancamentos.append({
                        'data': data_parcela,
                        'descricao': f'{despesa.get_tipo_display()} - {despesa.descricao} (Parcela {parcela + 1}/{qtd_parcelas})',
                        'tipo': tipo_lancamento,
                        'get_tipo_display': tipo_display,
                        'valor': valor_parcela,
                        'imovel': imovel,
                    })

        repasses = Cobranca.objects.filter(
            contrato__proprietario=proprietario,
            data_repasse__range=(data_inicial, data_final)
        ).select_related('contrato__imovel')

        total_repasses = repasses.count()

        for repasse in repasses:
            imovel = repasse.contrato.imovel
            valor_liquido = safe_money(repasse.valor_liquido.amount if repasse.valor_liquido else 0)

            if imovel and imovel.id in imoveis_dict:
                imoveis_dict[imovel.id]['repasses'] += valor_liquido

            lancamentos.append({
                'data': repasse.data_repasse,
                'descricao': f'Repasse para Proprietário',
                'tipo': 'REPASSE',
                'get_tipo_display': 'Repasse',
                'valor': valor_liquido,
                'imovel': imovel,
            })

        for imovel_id, imovel_info in imoveis_dict.items():
            imovel_info['saldo'] = imovel_info['receitas'] - imovel_info['despesas'] - imovel_info['repasses']

        lancamentos.sort(key=lambda x: x['data'])

        saldo = Money(0, 'BRL')
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

        total_receitas = sum((l['valor'] for l in lancamentos if l['tipo'] == 'RECEITA'), Money(0, 'BRL'))
        total_despesas = sum((l['valor'] for l in lancamentos if l['tipo'] == 'DESPESA'), Money(0, 'BRL'))
        total_repasses_valor = sum((l['valor'] for l in lancamentos if l['tipo'] == 'REPASSE'), Money(0, 'BRL'))

        imoveis = list(imoveis_dict.values())

        context.update({
            'lancamentos': lancamentos_com_saldo,
            'saldo': saldo,
            'total_receitas': total_receitas,
            'total_despesas': total_despesas,
            'total_repasses': total_repasses_valor,
            'total_cobrancas_pagas': total_cobrancas_pagas,
            'total_despesas_pagas': total_despesas_pagas,
            'total_repasses_feitos': total_repasses,
            'imoveis': imoveis,
        })

    return render(request, 'imoveis/extrato.html', context)

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

        # Lógica de despesas associadas ao contrato
        despesas = Despesa.objects.filter(contrato=cobranca.contrato)

        for despesa in despesas:
            if despesa.parcela_atual_ativa(data_ref):
                valor_parcela = despesa.calcular_valor_parcela()

                if despesa.paga == 'inquilino':
                    # Receita para o proprietário
                    extrato.append({
                        'data': data_ref,
                        'descricao': f"Repasse despesa: {despesa.descricao or despesa.get_tipo_display()}",
                        'tipo': 'Crédito',
                        'valor': valor_parcela,
                    })
                elif despesa.paga == 'proprietario':
                    # Despesa do proprietário
                    extrato.append({
                        'data': data_ref,
                        'descricao': f"Despesa: {despesa.descricao or despesa.get_tipo_display()}",
                        'tipo': 'Débito',
                        'valor': valor_parcela,
                    })
                elif despesa.paga == 'inquilino':
                    extrato.append({
                        "data": cobranca.data,
                        "descricao": f"Despesa: {despesa.descricao or despesa.get_tipo_display()}",
                        "tipo": "Crédito",
                        "valor": valor_parcela,
                    })

    # Ordenar por data
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

@csrf_exempt
def webhook_zapi(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        print('Mensagem recebida:', data)
        # Aqui você pode processar a mensagem recebida
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'error': 'Método não permitido'}, status=405)

def notificar_usuario(usuario):
    numero = usuario.telefone  # no formato 55DDXXXXXXXXX
    mensagem = f"Olá {usuario.nome}, sua cobrança foi gerada com sucesso!"
    resposta = enviar_mensagem(numero, mensagem)
    print(resposta)

def teste_envio(request):
    numero = '5511995972506'  # exemplo: 5511999999999
    mensagem = 'Olá! Teste de envio via Django e Z-API.'
    resposta = enviar_mensagem(numero, mensagem)
    return JsonResponse(resposta)

def visualizar_lembretes(request):
    hoje = date.today()
    dias_aviso = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30]  # Dias de aviso antes do vencimento

    # Busca todas as cobranças com contrato associado
    cobrancas = Cobranca.objects.filter(contrato__isnull=False)

    mensagens = []
    for cobranca in cobrancas:
        # Calcula quantos dias faltam para o vencimento
        dias_faltando = (cobranca.data_vencimento - hoje).days

        # Verifica se o número de dias restantes está na lista de dias de aviso
        if dias_faltando in dias_aviso:
            # Verifica se já foi enviado um lembrete para essa cobrança nesse período
            enviado = LembreteEnviado.objects.filter(
                cobranca=cobranca,
                dias_antecipacao=dias_faltando
            ).exists()

            if not enviado:
                try:
                    # Gera a mensagem personalizada
                    mensagem = gerar_mensagem_cobranca(cobranca)
                    inquilino = cobranca.contrato.inquilino

                    # Adiciona a mensagem à lista
                    mensagens.append({
                        'id': cobranca.id,
                        'nome': inquilino.nome if inquilino else 'Cliente',
                        'telefone': inquilino.telefone if inquilino else '',
                        'mensagem': mensagem,
                        'dias': dias_faltando
                    })
                except Exception as e:
                    # Em caso de erro, adiciona uma mensagem de erro
                    mensagens.append({
                        'id': cobranca.id,
                        'nome': 'Erro',
                        'telefone': '',
                        'mensagem': f"Erro ao gerar mensagem: {str(e)}",
                        'dias': dias_faltando
                    })

    # Renderiza o template com as mensagens
    return render(request, 'imoveis/visualizar_lembretes.html', {'mensagens': mensagens})

def enviar_mensagem_manual(request):
    telefone = request.POST.get('telefone')
    mensagem = request.POST.get('mensagem')
    cobranca_id = request.POST.get('cobranca_id')
    dias = request.POST.get('dias')

    print(f"Recebido: telefone={telefone}, mensagem={mensagem}, cobranca_id={cobranca_id}, dias={dias}")

    if telefone and mensagem and cobranca_id and dias is not None:
        try:
            cobranca_id = int(cobranca_id)
            cobranca = get_object_or_404(Cobranca, id=cobranca_id)

            print(f"Enviando mensagem para {telefone}: {mensagem}")

            resposta = enviar_mensagem(telefone, mensagem)
            print(f"Resposta da API: {resposta}")

            LembreteEnviado.objects.create(
                cobranca=cobranca,
                dias_antecipacao=int(dias)
            )

            messages.success(request, f"Mensagem enviada com sucesso para {telefone}.")
        except ValueError:
            messages.error(request, "ID de cobrança inválido.")
        except Exception as e:
            print(f"Erro ao enviar mensagem: {str(e)}")
            messages.error(request, f"Erro ao enviar mensagem: {str(e)}")
    else:
        messages.error(request, "Dados incompletos.")

    return redirect('visualizar_lembretes')

def listar_reajustes(request):
    hoje = timezone.now().date()
    contratos = Contrato.objects.filter(ativo=True)
    reajustaveis = []

    for contrato in contratos:
        historico = contrato.historico_aluguel or {}
        datas = sorted([timezone.datetime.strptime(k, "%Y-%m-%d").date() for k in historico.keys()])
        if not datas:
            continue

        ultima_data = datas[-1]
        if hoje < ultima_data + relativedelta(months=12):
            continue

        valor_anterior = Money(Decimal(historico[str(ultima_data)]), contrato.valor_aluguel.currency)
        indices = IndiceInflacao.objects.filter(
            tipo=contrato.fator_reajuste,
            data_referencia__gt=ultima_data,
            data_referencia__lte=hoje
        ).order_by('data_referencia')

        fator = Decimal("1.00")
        detalhes = []
        for i in indices:
            fator *= (1 + i.valor / 100)
            detalhes.append({
                "mes": i.data_referencia.strftime("%b/%Y"),
                "indice": i.valor
            })

        novo_valor = Money((valor_anterior * fator).quantize(Decimal("0.01")), contrato.valor_aluguel.currency)

        reajustaveis.append({
            "contrato": contrato,
            "ultima_data": ultima_data,
            "valor_anterior": valor_anterior,
            "fator": fator,
            "detalhes": detalhes,
            "novo_valor": novo_valor,
            "proxima_data": ultima_data + relativedelta(months=12)
        })

    return render(request, "imoveis/reajustes/lista.html", {"reajustaveis": reajustaveis})

def aplicar_reajuste(request, contrato_id, data_reajuste):
    contrato = get_object_or_404(Contrato, id=contrato_id)
    data_reajuste = timezone.datetime.strptime(data_reajuste, "%Y-%m-%d").date()
    historico = contrato.historico_aluguel or {}

    valor_anterior = Decimal(historico[str(data_reajuste - relativedelta(months=12))])
    indices = IndiceInflacao.objects.filter(
        tipo=contrato.fator_reajuste,
        data_referencia__gt=data_reajuste - relativedelta(months=12),
        data_referencia__lte=data_reajuste
    ).order_by("data_referencia")

    fator = Decimal("1.00")
    for i in indices:
        fator *= (1 + i.valor / 100)

    novo_valor = (valor_anterior * fator).quantize(Decimal("0.01"))
    historico[str(data_reajuste)] = str(novo_valor.quantize(Decimal('0.01')))
    contrato.valor_aluguel = Money(novo_valor, contrato.valor_aluguel.currency)
    contrato.historico_aluguel = historico
    contrato.save()

    messages.success(request, f"Reajuste aplicado: R$ {valor_anterior} → R$ {novo_valor}")
    return redirect("listar_reajustes")

def listar_reajustes(request):
    contratos = Contrato.objects.all()
    contratos_com_reajuste = []

    for contrato in contratos:
        resultado = calcular_reajuste(contrato)
        if resultado:
            contratos_com_reajuste.append({
                'contrato': contrato,
                'fator': resultado['fator'],
                'novo_valor': resultado['valor'],
                'data_base': resultado['data_base'],
                'historico': resultado['historico']
            })

    return render(request, 'imoveis/reajustes/lista.html', {'contratos_com_reajuste': contratos_com_reajuste})

def aprovar_reajuste(request, contrato_id):
    if request.method != 'POST':
        messages.error(request, "Método não permitido.")
        return redirect('listar_reajustes')
    
    contrato = get_object_or_404(Contrato, id=contrato_id)
    resultado = calcular_reajuste(contrato)

    if not resultado:
        messages.error(request, "Não há reajuste pendente para este contrato.")
        return redirect('listar_reajustes')

    # Pega o valor calculado pelo sistema
    valor_calculado = resultado['valor']
    
    # Tratamento mais robusto para o valor aceito
    try:
        valor_aceito_str = request.POST.get('valor_aceito', '').strip()
        
        # Remova qualquer caractere que não seja dígito, ponto ou vírgula
        import re
        valor_aceito_str = re.sub(r'[^\d.,]', '', valor_aceito_str)
        
        # Substitui vírgula por ponto (padrão para operações numéricas em Python)
        valor_aceito_str = valor_aceito_str.replace(',', '.')
        
        # Verifica se há algum valor para converter
        if not valor_aceito_str:
            raise ValueError("Valor em branco")
            
        # Converte para float primeiro e depois para Decimal para evitar erros de sintaxe
        valor_aceito = Decimal(str(float(valor_aceito_str)))
        
    except Exception as e:
        # Registrar o erro para debugging
        import traceback
        print(f"Erro ao converter valor: '{valor_aceito_str}'. Exceção: {e}\n{traceback.format_exc()}")
        messages.error(request, "Valor aceito inválido. Use apenas números (exemplo: 1000.50 ou 1000,50).")
        return redirect('listar_reajustes')

    # Resto do código permanece o mesmo...
    # Validação do campo 'currency'
    if not isinstance(contrato.valor_aluguel, Money):
        messages.error(request, "O campo 'valor_aluguel' deve ser uma instância de Money.")
        return redirect('listar_reajustes')

    # Cria o objeto Money para o valor aceito
    valor_aceito_money = Money(valor_aceito, contrato.valor_aluguel.currency)
    
    # Cria o registro de reajuste
    Reajuste.objects.create(
        contrato=contrato,
        data_reajuste=resultado['data_base'] + relativedelta(months=+12),
        fator_calculado=resultado['fator'],
        valor_calculado=valor_calculado.amount,
        fator_aprovado=valor_aceito / contrato.valor_aluguel.amount,
        valor_aprovado=valor_aceito,
        aprovado=True
    )

    # Atualiza o valor do aluguel para o valor aceito
    contrato.valor_aluguel = valor_aceito_money
    contrato.save()

    # Exibe mensagem de sucesso com detalhes
    if valor_aceito == valor_calculado.amount:
        messages.success(request, f"Reajuste aprovado com sucesso. Novo valor: R$ {valor_aceito}")
    else:
        percentual_diferenca = ((valor_aceito / valor_calculado.amount) - 1) * 100
        messages.success(request, 
                      f"Reajuste personalizado aprovado. Valor calculado: R$ {valor_calculado.amount}, " 
                      f"Valor aceito: R$ {valor_aceito} " 
                      f"({percentual_diferenca:.2f}% em relação ao calculado)")
    
    return redirect('listar_reajustes')