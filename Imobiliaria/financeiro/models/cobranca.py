# financeiro/models/cobranca.py
from django.db import models
from django.utils import timezone
from decimal import Decimal
from django.apps import apps
import datetime
from sisimob.utils.cobrancas_asaas import gerar_cobranca

class Cobranca(models.Model):
    """
    Modelo para cobrança de aluguel e outras despesas.
    Redesenhado para maior clareza, flexibilidade e robustez.
    """
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('paga', 'Recebida'),
        ('atrasada', 'Atrasada'),
        ('cancelada', 'Cancelada'),
    ]

    # Relacionamentos
    contrato = models.ForeignKey('sisimob.Contrato', on_delete=models.CASCADE, related_name='cobrancas_financeiro')
    inquilino = models.ForeignKey('sisimob.Cliente', on_delete=models.PROTECT, related_name='cobrancas_recebidas')

    # Dados de referência
    mes_referencia = models.PositiveSmallIntegerField()
    ano_referencia = models.PositiveSmallIntegerField()
    descricao = models.TextField(blank=True, null=True)

    # Valores
    valor_aluguel = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'),
        help_text="Valor base do aluguel"
    )
    valor_total = models.DecimalField(
        max_digits=10, decimal_places=2,
        help_text="Valor total da cobrança (aluguel + despesas)"
    )

    # Datas
    data_vencimento = models.DateField()
    data_emissao = models.DateField(auto_now_add=True)
    data_pagamento = models.DateField(null=True, blank=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    # Status
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pendente')

    # Integração Asaas
    asaas_id = models.CharField(max_length=100, blank=True, null=True, help_text="ID da cobrança no Asaas")
    boleto_url = models.URLField(blank=True, null=True)
    pix_copia_cola = models.TextField(blank=True, null=True)
    pix_qrcode = models.TextField(blank=True, null=True)
    pix_url = models.URLField(blank=True, null=True)
    codigo_barras = models.CharField(max_length=150, blank=True, null=True)
    fatura_url = models.URLField(blank=True, null=True)
    gateway_status = models.CharField(max_length=30, blank=True, null=True)

    # Controle de lembretes
    lembrete_10_enviado = models.BooleanField(default=False)
    lembrete_3_enviado = models.BooleanField(default=False)
    lembrete_0_enviado = models.BooleanField(default=False)

    # Campos adicionais úteis
    observacoes = models.TextField(blank=True, null=True, help_text="Observações internas")
    integrada_asaas = models.BooleanField(default=False, help_text="Indica se foi integrada com Asaas")
    
    class Meta:
        verbose_name = "Cobrança"
        verbose_name_plural = "Cobranças"
        ordering = ['-ano_referencia', '-mes_referencia', '-data_vencimento']
        unique_together = [('contrato', 'mes_referencia', 'ano_referencia')]
        indexes = [
            models.Index(fields=['contrato', 'status']),
            models.Index(fields=['mes_referencia', 'ano_referencia']),
            models.Index(fields=['data_vencimento']),
            models.Index(fields=['status', 'data_vencimento']),
            models.Index(fields=['integrada_asaas']),
        ]

    def save(self, *args, **kwargs):
        # Atualizar status baseado na data de vencimento
        if self.status == 'pendente' and self.data_vencimento < timezone.now().date():
            self.status = 'atrasada'
        
        # Definir inquilino automaticamente se não informado
        if not self.inquilino_id and self.contrato:
            if hasattr(self.contrato, 'inquilino'):
                self.inquilino = self.contrato.inquilino
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Cobrança {self.mes_referencia}/{self.ano_referencia} - {self.contrato}"

    @property
    def esta_atrasada(self):
        return self.status in ['pendente', 'atrasada'] and self.data_vencimento < timezone.now().date()

    @property
    def dias_atraso(self):
        if self.esta_atrasada:
            return (timezone.now().date() - self.data_vencimento).days
        return 0

    @property
    def data_referencia_texto(self):
        meses = {
            1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
            5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
            9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
        }
        return f"{meses.get(self.mes_referencia, f'Mês {self.mes_referencia}')} de {self.ano_referencia}"

    def calcular_valor_administracao(self):
        """Calcula valor da taxa de administração"""
        if not hasattr(self.contrato, 'tipo_taxa'):
            return Decimal('0.00')
        if self.contrato.tipo_taxa == 'percentual':
            percentual = self.contrato.valor_taxa_administracao_percentual or Decimal('0.00')
            return (self.valor_aluguel * percentual / Decimal('100')).quantize(Decimal('0.01'))
        elif self.contrato.tipo_taxa == 'fixo':
            return self.contrato.valor_taxa_administracao_fixo or Decimal('0.00')
        return Decimal('0.00')

    def get_despesas_cobranca(self):
        """Retorna despesas ativas para esta cobrança"""
        Despesa = apps.get_model('financeiro', 'Despesa')
        data_referencia = datetime.date(self.ano_referencia, self.mes_referencia, 1)
        despesas = Despesa.objects.filter(
            contrato=self.contrato,
            is_ativa=True,
            paga_por='inquilino'
        )
        return [
            despesa for despesa in despesas 
            if despesa.parcela_ativa_em_data(data_referencia)
        ]

    def calcular_valor_total(self):
        """Calcula valor total incluindo despesas"""
        despesas = self.get_despesas_cobranca()
        valor_despesas = sum(d.calcular_valor_parcela() for d in despesas)
        return self.valor_aluguel + valor_despesas

    def atualizar_valor_total(self):
        """Atualiza o valor total da cobrança"""
        self.valor_total = self.calcular_valor_total()
        self.save(update_fields=['valor_total'])

    def pode_ser_integrada(self):
        """Verifica se a cobrança pode ser integrada ao Asaas"""
        erros = []
        
        if not self.data_vencimento:
            erros.append("Data de vencimento não informada")
        if self.valor_total <= 0:
            erros.append("Valor total deve ser maior que zero")
        if not self.descricao:
            erros.append("Descrição é obrigatória")
        if not self.inquilino:
            erros.append("Inquilino não informado")
        if self.integrada_asaas:
            erros.append("Cobrança já foi integrada")
            
        return len(erros) == 0, erros

    def gerar_cobranca_gateway(self):
        """Integra cobrança com o gateway de pagamento (Asaas)"""
        pode_integrar, erros = self.pode_ser_integrada()
        
        if not pode_integrar:
            return {'status': 'error', 'erros': erros}
            
        if not self.asaas_id:
            resposta = gerar_cobranca(self)
            if resposta and isinstance(resposta, dict):
                self.asaas_id = resposta.get('id')
                self.boleto_url = resposta.get('bankSlipUrl')
                self.pix_copia_cola = resposta.get('pixCopiaeCola')
                self.pix_qrcode = resposta.get('pixQrCodeBase64')
                self.pix_url = resposta.get('pixUrl')
                self.codigo_barras = resposta.get('barCode')
                self.fatura_url = resposta.get('invoiceUrl')
                self.gateway_status = resposta.get('status')
                self.integrada_asaas = True
                
                self.save(update_fields=[
                    'asaas_id', 'boleto_url', 'pix_copia_cola',
                    'pix_qrcode', 'pix_url', 'codigo_barras',
                    'fatura_url', 'gateway_status', 'integrada_asaas'
                ])
                return {'status': 'success', 'data': resposta}
            else:
                return {'status': 'error', 'erros': ['Erro na integração com Asaas']}
        
        return {'status': 'error', 'erros': ['Cobrança já possui ID do Asaas']}

    def marcar_como_paga(self, data_pagamento=None):
        """Marca cobrança como paga e cria repasse"""
        if self.status == 'paga':
            return
            
        if not data_pagamento:
            data_pagamento = timezone.now().date()
            
        self.status = 'paga'
        self.data_pagamento = data_pagamento
        self.save(update_fields=['status', 'data_pagamento'])

        # Criar repasse automaticamente
        Repasse = apps.get_model('financeiro', 'Repasse')
        Repasse.objects.get_or_create(
            cobranca=self,
            defaults={
                'valor': self.calcular_valor_repasse(),
                'status': 'pendente'
            }
        )

    def calcular_valor_repasse(self):
        """Calcula valor do repasse para o proprietário"""
        taxa_adm = self.calcular_valor_administracao()
        
        # Buscar despesas pagas pelo proprietário
        Despesa = apps.get_model('financeiro', 'Despesa')
        data_referencia = datetime.date(self.ano_referencia, self.mes_referencia, 1)
        despesas_proprietario = Despesa.objects.filter(
            contrato=self.contrato,
            is_ativa=True,  # Mudei de 'status='ativa'' para is_ativa=True
            paga_por='proprietario'
        )
        
        valor_despesas_proprietario = sum(
            d.calcular_valor_parcela()
            for d in despesas_proprietario
            if d.parcela_ativa_em_data(data_referencia)
        )
        
        return self.valor_total - taxa_adm - valor_despesas_proprietario

    def is_quitada(self):
        """Verifica se a cobrança está quitada"""
        return self.status == 'paga' and self.data_pagamento is not None

    def get_detalhes_financeiros(self):
        """Retorna detalhamento financeiro da cobrança"""
        despesas = self.get_despesas_cobranca()
        valor_despesas = sum(d.calcular_valor_parcela() for d in despesas)
        
        return {
            "valor_aluguel": self.valor_aluguel,
            "valor_despesas": valor_despesas,
            "valor_total": self.valor_total,
            "taxa_administracao": self.calcular_valor_administracao(),
            "valor_repasse": self.calcular_valor_repasse(),
            "despesas_detalhadas": [
                {
                    'nome': d.nome,
                    'valor': d.calcular_valor_parcela(),
                    'tipo': d.tipo
                } for d in despesas
            ]
        }

    def get_descricao_formatada(self):
        """Retorna descrição formatada para WhatsApp"""
        if not self.descricao:
            return ""
            
        linhas = self.descricao.strip().split('\n') if self.descricao else []
        return '\n'.join([linha.strip() for linha in linhas if linha.strip()])

    def gerar_descricao_automatica(self):
        """Gera descrição automática baseada nas despesas"""
        detalhes = self.get_detalhes_financeiros()
        
        descricao_partes = [
            f"Aluguel referente a {self.data_referencia_texto}",
            f"Valor do aluguel: R$ {self.valor_aluguel:,.2f}".replace('.', ',').replace(',', '.', 1)
        ]
        
        if detalhes['despesas_detalhadas']:
            descricao_partes.append("\nDespesas incluídas:")
            for despesa in detalhes['despesas_detalhadas']:
                valor_formatado = f"R$ {despesa['valor']:,.2f}".replace('.', ',').replace(',', '.', 1)
                descricao_partes.append(f"• {despesa['nome']}: {valor_formatado}")
        
        valor_total_formatado = f"R$ {self.valor_total:,.2f}".replace('.', ',').replace(',', '.', 1)
        descricao_partes.append(f"\nValor total: {valor_total_formatado}")
        
        return '\n'.join(descricao_partes)