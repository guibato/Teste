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
    codigo = models.CharField(max_length=20, unique=True)
    icone = models.CharField(max_length=50, null=True, blank=True)
    cor = models.CharField(max_length=20, null=True, blank=True)
    is_recorrente_padrao = models.BooleanField(default=False)
    is_base_calculo_admin_padrao = models.BooleanField(default=False)
    ordem_exibicao = models.PositiveSmallIntegerField(default=99)
    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Tipo de Despesa"
        verbose_name_plural = "Tipos de Despesas"
        ordering = ['ordem_exibicao', 'nome']

    def __str__(self):
        return self.nome


class Despesa(models.Model):
    PAGA_CHOICES = [
        ('proprietario', 'Proprietário'),
        ('inquilino', 'Inquilino'),
        ('imobiliaria', 'Imobiliária'),
    ]
    PERIODICIDADE_CHOICES = list((key, key.capitalize()) for key in MESES_POR_PERIODICIDADE.keys())

    contrato = models.ForeignKey('sisimob.Contrato', on_delete=models.CASCADE, related_name='despesas_financeiro')
    tipo = models.ForeignKey(TipoDespesa, on_delete=models.PROTECT, related_name='despesas')
    descricao = models.CharField(max_length=255, null=True, blank=True)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2)
    paga_por = models.CharField(max_length=20, choices=PAGA_CHOICES)
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
        ]

    def __str__(self):
        tipo_nome = self.tipo.nome if self.tipo_id else "Tipo indefinido"
        return f"{tipo_nome} - {self.descricao or self.get_descricao_padrao()}"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.numero_parcelas <= 0:
            raise ValidationError({'numero_parcelas': 'Número de parcelas deve ser maior que zero.'})

    def get_descricao_padrao(self):
        if self.cobranca_referencia:
            return f"{self.tipo.nome} - {self.cobranca_referencia}"
        return f"{self.tipo.nome} - {self.data_inicio.strftime('%m/%Y')}"

    def calcular_valor_parcela(self):
        return self.valor_total / self.numero_parcelas if self.numero_parcelas else Decimal('0.00')

    def calcular_valor_repassado(self):
        return (self.calcular_valor_parcela() * self.percentual_repassado / Decimal('100')).quantize(Decimal('0.01'))

    def parcelas_pagas(self, data_referencia=None):
        if not data_referencia:
            data_referencia = date.today()
        meses_passados = self._calcular_meses_entre_datas(self.data_inicio, data_referencia)
        return min(meses_passados, self.numero_parcelas)

    def parcela_ativa_em_data(self, data_referencia=None):
        if not self.data_inicio or not self.numero_parcelas or not self.is_ativa:
            return False
        if not data_referencia:
            data_referencia = date.today()
        data_inicio = date(self.data_inicio.year, self.data_inicio.month, 1)
        data_referencia = date(data_referencia.year, data_referencia.month, 1)
        meses_totais = self._calcular_total_meses()
        data_fim = self._adicionar_meses(data_inicio, meses_totais)
        return data_inicio <= data_referencia < data_fim

    def _calcular_total_meses(self):
        return self.numero_parcelas * MESES_POR_PERIODICIDADE.get(self.periodicidade, 1)

    def _calcular_meses_entre_datas(self, data_inicio, data_fim):
        meses_totais = (data_fim.year - data_inicio.year) * 12 + (data_fim.month - data_inicio.month)
        return meses_totais // MESES_POR_PERIODICIDADE.get(self.periodicidade, 1)

    def _adicionar_meses(self, data, num_meses):
        return date(
            data.year + ((data.month - 1 + num_meses) // 12),
            ((data.month - 1 + num_meses) % 12) + 1,
            1
        )

    def save(self, *args, **kwargs):
        if not self.data_fim_prevista and self.data_inicio and self.numero_parcelas:
            meses_totais = self._calcular_total_meses()
            self.data_fim_prevista = self._adicionar_meses(self.data_inicio, meses_totais)
        if self.tipo_id and self.pk is None:
            try:
                tipo = TipoDespesa.objects.get(pk=self.tipo_id)
                self.is_recorrente = getattr(self, 'is_recorrente', tipo.is_recorrente_padrao)
                self.is_base_calculo_administracao = getattr(
                    self, 'is_base_calculo_administracao', tipo.is_base_calculo_admin_padrao
                )
            except TipoDespesa.DoesNotExist:
                pass
        super().save(*args, **kwargs)
