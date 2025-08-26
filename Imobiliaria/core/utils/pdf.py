from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from reportlab.lib.utils import ImageReader
from io import BytesIO
from django.http import FileResponse
from datetime import date
from decimal import Decimal
from django.utils.text import Truncator
import os

def gerar_pdf_extrato_repasses(proprietario, data_inicial, data_final, cobrancas):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=landscape(A4))
    largura, altura = landscape(A4)

    topo_atual = altura - 3 * cm

    # Logo
    caminho_logo = os.path.join("staticfiles", "images", "logo.png")
    if os.path.exists(caminho_logo):
        logo = ImageReader(caminho_logo)
        largura_logo = 6 * cm
        altura_logo_img = 2 * cm
        pos_x = (largura - largura_logo) / 2
        p.drawImage(logo, pos_x, topo_atual, width=largura_logo, height=altura_logo_img, preserveAspectRatio=True)
        topo_atual -= altura_logo_img - 2 * cm

    # Título
    p.setFont("Helvetica-Bold", 14)
    p.drawCentredString(largura / 2, topo_atual, "EXTRATO DETALHADO DE REPASSES")
    topo_atual -= 1 * cm

    # Informações do proprietário e período
    p.setFont("Helvetica", 10)
    p.drawString(2 * cm, topo_atual, f"Proprietário: {proprietario.nome}")
    topo_atual -= 0.6 * cm
    p.drawString(2 * cm, topo_atual, f"Período: {data_inicial.strftime('%d/%m/%Y')} a {data_final.strftime('%d/%m/%Y')}")
    topo_atual -= 1 * cm

    # Cabeçalho da tabela
    dados_tabela = [["Data", "Imóvel", "Descrição", "Tipo", "Valor (R$)", "Saldo (R$)"]]
    saldo = Decimal("0.00")

    for cobranca in cobrancas:
        contrato = cobranca.contrato
        imovel = contrato.imovel
        endereco = Truncator(str(imovel)).chars(50) if imovel else "-"
        data_venc = cobranca.data_vencimento.strftime("%d/%m/%Y")
        referencia = f"{cobranca.mes_referencia}/{cobranca.ano_referencia}"
        data_ref = date(cobranca.ano_referencia, cobranca.mes_referencia, 1)

        # Receita de aluguel
        valor_aluguel = contrato.valor_aluguel or Decimal("0.00")
        saldo += valor_aluguel
        dados_tabela.append([
            data_venc, endereco, f"Aluguel {referencia}", "Receita",
            f"R$ {valor_aluguel:,.2f}".replace(".", "#").replace(",", ".").replace("#", ","),
            f"R$ {saldo:,.2f}".replace(".", "#").replace(",", ".").replace("#", ",")
        ])

        # Despesas (receita se pagas pelo inquilino, despesa se pelo proprietário)
        for despesa in contrato.despesas.all():
            if not despesa.parcela_atual_ativa(data_ref):
                continue

            valor_despesa = despesa.calcular_valor_parcela() or Decimal("0.00")
            descricao = f"{despesa.get_tipo_display()} - {despesa.descricao or ''}"

            if despesa.paga == 'inquilino':
                saldo += valor_despesa
                dados_tabela.append([
                    data_venc, endereco, descricao, "Receita",
                    f"R$ {valor_despesa:,.2f}".replace(".", "#").replace(",", ".").replace("#", ","),
                    f"R$ {saldo:,.2f}".replace(".", "#").replace(",", ".").replace("#", ",")
                ])
            elif despesa.paga == 'proprietario':
                saldo -= valor_despesa
                dados_tabela.append([
                    data_venc, endereco, descricao, "Despesa",
                    f"R$ {valor_despesa:,.2f}".replace(".", "#").replace(",", ".").replace("#", ","),
                    f"R$ {saldo:,.2f}".replace(".", "#").replace(",", ".").replace("#", ",")
                ])

        # Taxa de administração (despesa)
        valor_taxa = cobranca.valor_administracao or Decimal("0.00")
        saldo -= valor_taxa
        dados_tabela.append([
            data_venc, endereco, f"Taxa de Administração {referencia}", "Despesa",
            f"R$ {valor_taxa:,.2f}".replace(".", "#").replace(",", ".").replace("#", ","),
            f"R$ {saldo:,.2f}".replace(".", "#").replace(",", ".").replace("#", ",")
        ])

        # Repasse (despesa)
        valor_repasse = cobranca.valor_liquido or Decimal("0.00")
        data_repasse = cobranca.data_repasse.strftime("%d/%m/%Y") if cobranca.data_repasse else data_venc
        saldo -= valor_repasse
        dados_tabela.append([
            data_repasse, endereco, "Repasse para Proprietário", "Repasse",
            f"R$ {valor_repasse:,.2f}".replace(".", "#").replace(",", ".").replace("#", ","),
            f"R$ {saldo:,.2f}".replace(".", "#").replace(",", ".").replace("#", ",")
        ])

    # Montar tabela PDF
    tabela = Table(dados_tabela, colWidths=[3.2*cm, 6*cm, 8*cm, 2.5*cm, 3.5*cm, 3.5*cm])
    estilo = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
    ])
    tabela.setStyle(estilo)

    tabela.wrapOn(p, largura, altura)
    tabela_height = len(dados_tabela) * 0.6 * cm
    tabela.drawOn(p, 2 * cm, topo_atual - tabela_height)

    p.showPage()
    p.save()

    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename="extrato_repasses.pdf")
