# financeiro/models/indice.py
from django.db import models
from decimal import Decimal
from datetime import date
from dateutil.relativedelta import relativedelta

CEM = Decimal('100.0')

class IndiceInflacao(models.Model):
    TIPO_CHOICES = [
        ('IPCA', 'IPC-A'),
        ('IGPM', 'IGP-M'),
        ('INPC', 'INPC'),
        ('OUTRO', 'Outro Índice'),
    ]

    tipo = models.CharField(max_length=50, choices=TIPO_CHOICES, verbose_name="Nome do Índice")
    valor = models.DecimalField(max_digits=10, decimal_places=4, verbose_name="Valor do Índice")
    data_referencia = models.DateField(verbose_name="Data de Referência")
    acumulado_12_meses = models.DecimalField(
        max_digits=10, decimal_places=4, verbose_name="Acumulado 12 meses", null=True, blank=True
    )
    fonte = models.CharField(max_length=100, null=True, blank=True, verbose_name="Fonte da Informação")
    data_cadastro = models.DateTimeField(auto_now_add=True, verbose_name="Data de Cadastro")

    class Meta:
        verbose_name = "Índice de Inflação"
        verbose_name_plural = "Índices de Inflação"
        ordering = ['-data_referencia']
        unique_together = ['tipo', 'data_referencia']
        indexes = [
            models.Index(fields=['tipo', 'data_referencia']),
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.data_referencia.strftime('%m/%Y')} - {self.valor:.4f}%"

    def save(self, *args, **kwargs):
        if not self.acumulado_12_meses:
            data_inicio = self.data_referencia - relativedelta(months=12)
            indices = IndiceInflacao.objects.filter(
                tipo=self.tipo,
                data_referencia__gte=data_inicio,
                data_referencia__lt=self.data_referencia
            ).order_by('data_referencia')

            if indices.exists():
                acumulado = Decimal('1.0')
                for indice in indices:
                    acumulado *= (Decimal('1.0') + (indice.valor / CEM))
                self.acumulado_12_meses = ((acumulado - Decimal('1.0')) * CEM).quantize(Decimal('0.0001'))
            else:
                self.acumulado_12_meses = Decimal('0.0000')

        super().save(*args, **kwargs)

    @classmethod
    def calcular_valor_reajustado(cls, valor_base, tipo_indice, data_inicio, data_fim=None):
        if data_fim is None:
            data_fim = date.today()

        data_inicio = date(data_inicio.year, data_inicio.month, 1)
        data_fim = date(data_fim.year, data_fim.month, 1)

        indices = cls.objects.filter(
            tipo=tipo_indice,
            data_referencia__gte=data_inicio,
            data_referencia__lt=data_fim
        ).order_by('data_referencia')

        valor_reajustado = Decimal(str(valor_base))
        for indice in indices:
            valor_reajustado *= (Decimal('1.0') + (indice.valor / CEM))

        return valor_reajustado.quantize(Decimal('0.01'))

    @classmethod
    def ultimo_acumulado(cls, tipo_indice):
        return cls.objects.filter(tipo=tipo_indice).order_by('-data_referencia').first()
