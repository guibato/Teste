from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from django.http import HttpResponse
import io
import io
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from django.http import FileResponse
from reportlab.lib.pagesizes import A4, portrait, letter
from reportlab.lib.units import cm
import io
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib import colors
from reportlab.lib.pagesizes import portrait
from reportlab.lib.colors import HexColor
from django.http import HttpResponse
import datetime







def gerar_extrato_repasses_pdf(proprietario, data_inicio=None, data_fim=None):

    if data_inicio:
        data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
    if data_fim:
        data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()

    lancamentos = lancamentos.filter(data__range=(data_inicio, data_fim))

    response = io.BytesIO()
    doc = SimpleDocTemplate(response, pagesize=portrait(letter),
                            leftMargin=1.5*cm, rightMargin=1.5*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    elements = []
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=14, alignment=1, spaceAfter=0.3*cm)
    normal_style = ParagraphStyle('Normal', parent=styles['Normal'], fontSize=10)

    def format_currency(value):
        return f'R$ {value:,.2f}'.replace('.', 'X').replace(',', '.').replace('X', ',')

    # Cabeçalho
    elements.append(Paragraph(f"<b>Extrato de Repasses</b>", title_style))
    elements.append(Paragraph(f"Proprietário: {proprietario_nome}", normal_style))
    elements.append(Spacer(1, 0.3 * cm))

    # Tabela
    header = ["Data", "Descrição", "Tipo", "Valor"]
    data = [header]
    saldo = 0

    for lancamento in extrato:
        valor = lancamento['valor']
        tipo = lancamento['tipo']  # 'crédito' ou 'débito'
        if tipo == 'crédito':
            saldo += valor
        else:
            saldo -= valor

        data.append([
            lancamento['data'].strftime('%d/%m/%Y'),
            lancamento['descricao'],
            tipo.capitalize(),
            format_currency(valor)
        ])

    # Linha final: Saldo acumulado
    data.append(["", "", "Saldo Final", format_currency(saldo)])

    table = Table(data, colWidths=[3.5*cm, 8*cm, 3*cm, 3*cm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#f2f2f2')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (-1, -1), HexColor('#f2f2f2')),
    ]))

    elements.append(table)
    doc.build(elements)
    return response.getvalue()
