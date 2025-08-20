# financeiro/models/despesa.py
from django.db import models
from django.utils import timezone
from decimal import Decimal
from datetime import date
from django.core.validators import MinValueValidator, MaxValueValidator

# Constante reutilizável
MESES_POR_PERIODICIDADE = {
    'mensal': 1, 'bimestral': 2, 'trimestral': 3,
    'semestral': 6, 'anual': 12, 'unica': 1
}

class TipoDespesa(models.Model):
    nome = models.CharField(max_length=50, unique=True)
    descricao = models.TextField(null=True, blank=True)
    ativo = models.BooleanField(default=True)
    incidencia_taxa_admin_padrao = models.BooleanField(
        default=False,
        help_text="Por padrão, despesas deste tipo têm incidência de taxa administrativa?"
    )
    categoria = models.CharField(
        max_length=30,
        choices=[
            ('operacional', 'Operacional'),
            ('manutencao', 'Manutenção'),
            ('melhorias', 'Melhorias'),
            ('impostos', 'Impostos/Taxas'),
            ('servicos', 'Serviços'),
            ('outros', 'Outros')
        ],
        default='outros'
    )


    class Meta:
        verbose_name = "Tipo de Despesa"
        verbose_name_plural = "Tipos de Despesas"
        ordering = ['categoria', 'nome']

    def __str__(self):
        return f"{self.nome} ({self.get_categoria_display()})"



class Despesa(models.Model):
    PAGA_CHOICES = [
        ('proprietario', 'Proprietário'),
        ('inquilino', 'Inquilino'),
        ('imobiliaria', 'Imobiliária'),
    ]
    PERIODICIDADE_CHOICES = list((key, key.capitalize()) for key in MESES_POR_PERIODICIDADE.keys())
    INCIDENCIA_TAXA_CHOICES = [
        ('sim', 'Sim - Tem incidência de taxa administrativa'),
        ('nao', 'Não - Isenta de taxa administrativa'),
        ('parcial', 'Parcial - Apenas parte tem incidência'),
    ]
    contrato = models.ForeignKey('sisimob.Contrato', on_delete=models.CASCADE, related_name='despesas_financeiro')
    tipo = models.ForeignKey(TipoDespesa, on_delete=models.PROTECT, related_name='despesas')
    descricao = models.CharField(max_length=255, null=True, blank=True)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2)
    paga_por = models.CharField(max_length=20, choices=PAGA_CHOICES)
    incidencia_taxa_admin = models.CharField(
        max_length=10,
        choices=INCIDENCIA_TAXA_CHOICES,
        default='nao',
        help_text="Define se esta despesa tem incidência de taxa administrativa"
    )
    percentual_com_incidencia = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Para incidência parcial: % do valor que tem incidência (0-100%)"
    )
    taxa_admin_especifica = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Taxa específica para esta despesa (deixe vazio para usar padrão do contrato)"
    )
    numero_parcelas = models.PositiveIntegerField(default=1)
    periodicidade = models.CharField(max_length=20, choices=PERIODICIDADE_CHOICES, default='mensal')
    data_inicio = models.DateField()
    data_fim_prevista = models.DateField(null=True, blank=True)
    data_encerramento = models.DateField(null=True, blank=True)
    cobranca_referencia = models.CharField(max_length=20, null=True, blank=True)
    percentual_repassado = models.DecimalField(
        max_digits=5, decimal_places=2, default=100,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    is_base_calculo_administracao = models.BooleanField(default=False)
    is_recorrente = models.BooleanField(default=False)
    is_ativa = models.BooleanField(default=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    comprovante = models.FileField(upload_to='despesas/comprovantes/', null=True, blank=True)
    observacoes = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name = "Despesa"
        verbose_name_plural = "Despesas"
        ordering = ['-data_inicio', 'tipo']
        indexes = [
            models.Index(fields=['contrato', 'data_inicio']),
            models.Index(fields=['is_ativa', 'tipo']),
            models.Index(fields=['incidencia_taxa_admin', 'paga_por']),
        ]

    def __str__(self):
        tipo_nome = self.tipo.nome if self.tipo_id else "Tipo indefinido"
        incidencia_icon = "💰" if self.tem_incidencia_taxa() else "🆓"
        return f"{incidencia_icon} {tipo_nome} - {self.descricao or self.get_descricao_padrao()}"

    def tem_incidencia_taxa(self):
        """Verifica se tem alguma incidência de taxa administrativa"""
        return self.incidencia_taxa_admin in ['sim', 'parcial']
    
    def get_valor_com_incidencia(self):
        """Retorna o valor que tem incidência de taxa"""
        if self.incidencia_taxa_admin == 'sim':
            return self.valor_total
        elif self.incidencia_taxa_admin == 'parcial':
            return self.valor_total * (self.percentual_com_incidencia / 100)
        else:
            return Decimal('0.00')
    
    def get_valor_sem_incidencia(self):
        """Retorna o valor que NÃO tem incidência de taxa"""
        return self.valor_total - self.get_valor_com_incidencia()
    
    def get_taxa_admin_aplicavel(self, taxa_padrao_contrato=None):
        """Retorna a taxa de administração a ser aplicada nesta despesa"""
        if self.taxa_admin_especifica:
            return self.taxa_admin_especifica
        return taxa_padrao_contrato or Decimal('8.00')
    
    def calcular_composicao_financeira(self, taxa_padrao_contrato=None):
        """
        Calcula a composição financeira completa desta despesa
        """
        taxa_admin = self.get_taxa_admin_aplicavel(taxa_padrao_contrato)
        valor_com_incidencia = self.get_valor_com_incidencia()
        valor_sem_incidencia = self.get_valor_sem_incidencia()
        
        # Calcular taxa administrativa
        valor_taxa_admin = valor_com_incidencia * (taxa_admin / 100)
        
        # Calcular valores líquidos
        valor_liquido_com_incidencia = valor_com_incidencia - valor_taxa_admin
        
        # Impacto no repasse conforme quem paga
        if self.paga_por == 'inquilino':
            # Inquilino paga, proprietário recebe líquido
            impacto_repasse = valor_liquido_com_incidencia + valor_sem_incidencia
        elif self.paga_por == 'proprietario':
            # Proprietário paga, desconta do repasse
            impacto_repasse = -(valor_liquido_com_incidencia + valor_sem_incidencia)
        else:  # imobiliaria
            # Imobiliária paga, não afeta repasse
            impacto_repasse = Decimal('0.00')
        
        return {
            'valor_total': self.valor_total,
            'valor_com_incidencia': valor_com_incidencia,
            'valor_sem_incidencia': valor_sem_incidencia,
            'taxa_admin_percentual': taxa_admin,
            'valor_taxa_admin': valor_taxa_admin,
            'valor_liquido_com_incidencia': valor_liquido_com_incidencia,
            'impacto_repasse': impacto_repasse,
            'pago_por': self.paga_por,
            'descricao_completa': self.get_descricao_completa(),
            'detalhamento': self._gerar_detalhamento_financeiro(
                valor_com_incidencia, valor_sem_incidencia, valor_taxa_admin, impacto_repasse
            )
        }
    
    def _gerar_detalhamento_financeiro(self, com_incidencia, sem_incidencia, taxa, impacto):
        """Gera detalhamento textual da composição financeira"""
        detalhes = []
        
        if com_incidencia > 0:
            detalhes.append(f"Valor c/ taxa: R$ {com_incidencia:.2f} → Taxa: R$ {taxa:.2f} → Líquido: R$ {com_incidencia - taxa:.2f}")
        
        if sem_incidencia > 0:
            detalhes.append(f"Valor s/ taxa: R$ {sem_incidencia:.2f} (integral)")
        
        detalhes.append(f"Impacto repasse: R$ {impacto:.2f} ({'positivo' if impacto >= 0 else 'negativo'})")
        
        return " | ".join(detalhes)
    
    def get_descricao_completa(self):
        """Descrição com informações de taxa"""
        base = self.descricao or self.get_descricao_padrao()
        
        if self.incidencia_taxa_admin == 'sim':
            return f"{base} (c/ taxa admin)"
        elif self.incidencia_taxa_admin == 'parcial':
            return f"{base} (taxa parcial {self.percentual_com_incidencia}%)"
        else:
            return f"{base} (s/ taxa admin)"

    # Métodos existentes mantidos
    def get_descricao_padrao(self):
        if self.cobranca_referencia:
            return f"{self.tipo.nome} - {self.cobranca_referencia}"
        return f"{self.tipo.nome} - {self.data_inicio.strftime('%m/%Y')}"

    def calcular_valor_parcela(self):
        return self.valor_total / self.numero_parcelas if self.numero_parcelas else Decimal('0.00')

    def parcela_ativa_em_data(self, data_referencia=None):
        if not self.data_inicio or not self.numero_parcelas or not self.is_ativa:
            return False
        if not data_referencia:
            data_referencia = date.today()
        
        # Lógica de verificação se parcela está ativa
        data_inicio = date(self.data_inicio.year, self.data_inicio.month, 1)
        data_referencia = date(data_referencia.year, data_referencia.month, 1)
        meses_totais = self._calcular_total_meses()
        data_fim = self._adicionar_meses(data_inicio, meses_totais)
        return data_inicio <= data_referencia < data_fim

    def _calcular_total_meses(self):
        MESES_POR_PERIODICIDADE = {
            'mensal': 1, 'bimestral': 2, 'trimestral': 3,
            'semestral': 6, 'anual': 12, 'unica': 1
        }
        return self.numero_parcelas * MESES_POR_PERIODICIDADE.get(self.periodicidade, 1)

    def _adicionar_meses(self, data, num_meses):
        return date(
            data.year + ((data.month - 1 + num_meses) // 12),
            ((data.month - 1 + num_meses) % 12) + 1,
            1
        )

    def save(self, *args, **kwargs):
        """Save com validações e automações"""
        
        # Sincronizar campo deprecado para compatibilidade
        if self.incidencia_taxa_admin == 'sim':
            self.is_base_calculo_administracao = True
        else:
            self.is_base_calculo_administracao = False
        
        # Calcular data_fim_prevista se não informada
        if not self.data_fim_prevista and self.data_inicio and self.numero_parcelas:
            meses_totais = self._calcular_total_meses()
            self.data_fim_prevista = self._adicionar_meses(self.data_inicio, meses_totais)
        
        # Validações
        if self.incidencia_taxa_admin == 'parcial' and self.percentual_com_incidencia <= 0:
            raise ValidationError("Para incidência parcial, percentual deve ser maior que 0")
        
        super().save(*args, **kwargs)

    def clean(self):
        """Validações customizadas"""
        from django.core.exceptions import ValidationError
        
        if self.numero_parcelas <= 0:
            raise ValidationError({'numero_parcelas': 'Número de parcelas deve ser maior que zero.'})
        
        if self.incidencia_taxa_admin == 'parcial':
            if not self.percentual_com_incidencia or self.percentual_com_incidencia <= 0:
                raise ValidationError({
                    'percentual_com_incidencia': 'Para incidência parcial, informe o percentual.'
                })
        
        if self.taxa_admin_especifica and self.taxa_admin_especifica < 0:
            raise ValidationError({
                'taxa_admin_especifica': 'Taxa de administração não pode ser negativa.'
            })