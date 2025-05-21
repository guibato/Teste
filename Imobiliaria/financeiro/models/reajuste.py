# financeiro/models/reajuste.py
from django.db import models
from decimal import Decimal
from datetime import date

class ReajusteAluguel(models.Model):
    contrato = models.ForeignKey('sisimob.Contrato', on_delete=models.CASCADE, related_name='reajustes')
    valor_anterior = models.DecimalField(max_digits=10, decimal_places=2)
    valor_reajustado = models.DecimalField(max_digits=10, decimal_places=2)
    fator_aplicado = models.DecimalField(max_digits=5, decimal_places=2, help_text="Percentual aplicado, ex: 6.78")
    indice_utilizado = models.CharField(max_length=20, choices=[
        ('IPCA', 'IPCA'), ('IGPM', 'IGP-M'), ('INPC', 'INPC'), ('MANUAL', 'Manual')
    ], default='MANUAL')
    data_reajuste = models.DateField(help_text="Data em que o novo valor passa a valer")
    observacao = models.TextField(null=True, blank=True)

    data_cadastro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Reajuste de Aluguel"
        verbose_name_plural = "Reajustes de Aluguel"
        ordering = ['-data_reajuste']

    def __str__(self):
        return f"{self.contrato} - {self.valor_anterior} → {self.valor_reajustado} ({self.data_reajuste})"

    @classmethod
    def obter_ultimo_reajuste(cls, contrato: 'Contrato', referencia: date = None):
        """
        Retorna o último reajuste válido para um contrato até uma determinada data (default: hoje).
        """
        if referencia is None:
            referencia = date.today()

        return cls.objects.filter(
            contrato=contrato,
            data_reajuste__lte=referencia
        ).order_by('-data_reajuste').first()
