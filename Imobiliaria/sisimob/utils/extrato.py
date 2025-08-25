import os
from django.http import HttpRequest
from django.conf import settings
import django
from reportlab.lib.pagesizes import portrait, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
import io
from datetime import date
from django.db.models import Sum
from cadastro.models import Contrato, Cobranca

# Configura o Django antes de usar qualquer funcionalidade
if not settings.configured:
    settings.configure(
        DEBUG=True,
        SECRET_KEY='dummy-secret-key',
        ROOT_URLCONF=__name__,
        DEFAULT_CHARSET='utf-8',  # Adiciona esta configuração
    )
    django.setup()

def gerar_extrato_rendimento(contrato_id, ano):
    # Buscar o contrato pelo ID
    try:
        print(f"Contrato ID recebido: {contrato_id}")
        contrato = Contrato.objects.get(id=contrato_id)
        print(f"Contrato recuperado: {contrato.id} - Proprietário: {contrato.proprietario.nome}")
    except Contrato.DoesNotExist:
        raise ValueError(f"Contrato com ID {contrato_id} não encontrado.")

    # Filtrar as cobranças do contrato para o ano especificado
    cobrancas = Cobranca.objects.filter(
        contrato=contrato,
        ano_referencia=ano
    ).order_by('mes_referencia')
    print(f"Cobranças encontradas para o contrato {contrato.id}: {[c.mes_referencia for c in cobrancas]}")

    # Calcular o total de aluguel e taxa de administração
    total_aluguel = cobrancas.aggregate(total=Sum('valor'))['total'] or 0
    taxa_administracao = contrato.valor_taxa_administracao()
    print(f"Taxa de administração calculada: {taxa_administracao}")

    # Configuração do PDF
    response = io.BytesIO()
    doc = SimpleDocTemplate(response, pagesize=portrait(letter), 
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
        alignment=1,  # Center
        spaceAfter=0.2*cm
    )
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Heading2'],
        fontSize=12,
        alignment=1,  # Center
        spaceAfter=0.5*cm,
        textColor=HexColor('#000000')
    )
    normal_style = ParagraphStyle(
        'Normal',
        parent=styles['Normal'],
        fontSize=10,
        alignment=0,  # Left
        spaceAfter=0.2*cm,
        leftIndent=0
    )

    # Título
    elements.append(Paragraph("<b>COMPROVANTE ANUAL DE RENDIMENTOS DE ALUGUÉIS</b>", title_style))
    elements.append(Paragraph(f"<b>Ano-calendário: {ano}</b>", subtitle_style))
    elements.append(Spacer(1, 0.3 * cm))

    # Dados do Imóvel
    endereco = contrato.imovel.endereco_completo()
    imovel_data = [
        [f"<b>Número do contrato:</b> {contrato.id}", f"<b>Início do contrato:</b> {contrato.data_inicio.strftime('%d/%m/%Y')}", f"<b>Tipo do imóvel:</b> Urbano"],
        [f"<b>Endereço do imóvel:</b> {endereco}"],
        [f"<b>UF:</b> {contrato.imovel.estado}", f"<b>Município:</b> {contrato.imovel.cidade}", f"<b>CEP:</b> {contrato.imovel.cep}"]
    ]
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

    # Administradora
    elements.append(Paragraph("<b>CNPJ da Administradora do imóvel (Imobiliária):</b> 55.507.744/0001-99", normal_style))
    elements.append(Paragraph("<b>Nome:</b> Palestra Imóveis", normal_style))
    elements.append(Paragraph("<b>Endereço:</b> Rua Serra de Bragança, 1814, Vila Gomes Cardim, São Paulo-SP, CEP 03318-000", normal_style))
    elements.append(Spacer(1, 0.5 * cm))

    # Locador e Locatário
    elements.append(Paragraph("<b>Locador(a):</b> " + contrato.proprietario.nome + " - CPF: " + contrato.proprietario.CPF, normal_style))
    elements.append(Paragraph("<b>Locatário(a):</b> " + contrato.inquilino.nome + " - CPF: " + contrato.inquilino.CPF, normal_style))
    elements.append(Spacer(1, 0.5 * cm))
    print(f"Imóvel: {contrato.imovel.endereco_completo()}")
    print(f"Proprietário: {contrato.proprietario.nome} - CPF: {contrato.proprietario.CPF}")
    print(f"Inquilino: {contrato.inquilino.nome} - CPF: {contrato.inquilino.CPF}")
    # Tabela de Rendimentos
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
        valores_por_mes[mes][1] = taxa_administracao
        valores_por_mes[mes][2] = 0  # Imposto retido (não implementado)

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
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (-1, -1), HexColor('#f2f2f2')),
    ])
    valores_table.setStyle(valores_style)
    elements.append(valores_table)
    elements.append(Spacer(1, 0.5 * cm))

    # Atenção
    atencao_style = ParagraphStyle(
        'Atencao',
        parent=styles['Normal'],
        fontSize=9,
        alignment=0,  # Justify
        spaceAfter=0.2*cm
    )
    elements.append(Paragraph("<b>Atenção:</b>", atencao_style))
    elements.append(Paragraph("Para a inclusão na Declaração do Imposto de Renda da Pessoa Física - DIRPF dos rendimentos informados neste documento, certifique-se de que os mesmos não constam de outro comprovante emitido pela fonte pagadora.", atencao_style))

    # Construir o PDF
    doc.build(elements)
    pdf = response.getvalue()
    return pdf