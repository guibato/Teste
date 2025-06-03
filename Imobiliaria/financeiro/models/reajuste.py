from django.db import models
from decimal import Decimal
from datetime import date, timedelta
from datetime import datetime
from dateutil.relativedelta import relativedelta
from financeiro.models.indice import IndiceInflacao


class ReajusteAluguel(models.Model):
    contrato = models.ForeignKey('sisimob.Contrato', on_delete=models.CASCADE, related_name='reajustes')
    valor_anterior = models.DecimalField(max_digits=10, decimal_places=2)
    valor_reajustado = models.DecimalField(max_digits=10, decimal_places=2)
    fator_aplicado = models.DecimalField(
        max_digits=5, decimal_places=2, 
        help_text="Percentual aplicado, ex: 6.78 para 6,78%"
    )
    indice_utilizado = models.CharField(
        max_length=20, 
        choices=[('IPCA', 'IPCA'), ('IGPM', 'IGP-M'), ('INPC', 'INPC'), ('MANUAL', 'Manual')],
        default='MANUAL'
    )
    data_reajuste = models.DateField(help_text="Data a partir da qual o novo valor entra em vigor")
    observacao = models.TextField(null=True, blank=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Reajuste de Aluguel"
        verbose_name_plural = "Reajustes de Aluguel"
        ordering = ['-data_reajuste']
        unique_together = ('contrato', 'data_reajuste')

    def __str__(self):
        return f"{self.contrato} | {self.data_reajuste.strftime('%m/%Y')} → R$ {self.valor_reajustado}"

    @classmethod
    def obter_ultimo_reajuste(cls, contrato: 'Contrato', referencia: date = None):
        """
        Retorna o último reajuste aprovado para o contrato até a data de referência.
        """
        if referencia is None:
            referencia = date.today()

        return cls.objects.filter(
            contrato=contrato,
            data_reajuste__lte=referencia
        ).order_by('-data_reajuste').first()

    @staticmethod
    def calcular_reajuste(valor_anterior: Decimal, percentual: Decimal) -> Decimal:
        """
        Aplica um percentual sobre o valor anterior.
        """
        fator = Decimal('1') + (percentual / 100)
        return (valor_anterior * fator).quantize(Decimal('0.01'))
    
    @classmethod
    def sugerir_reajuste(cls, contrato):
        # Último reajuste aplicado (se houver)
        ultimo_reajuste = contrato.reajustes.order_by('-data_reajuste').first()

        if ultimo_reajuste:
            data_inicio = ultimo_reajuste.data_reajuste
            valor_anterior = ultimo_reajuste.valor_reajustado
        else:
            data_inicio = contrato.data_inicio
            valor_anterior = contrato.valor_base

        # Próximo ciclo (12 meses depois)
        data_reajuste = data_inicio + relativedelta(months=12)

        # Buscar os 12 índices a partir de data_inicio
        indices = IndiceInflacao.objects.filter(
            tipo=contrato.fator_reajuste,
            data_referencia__gte=data_inicio.replace(day=1),
            data_referencia__lt=data_reajuste.replace(day=1)
        ).order_by('data_referencia')

        if indices.count() < 12:
            return None  # Ainda não há 12 índices

        # Calcular o fator acumulado
        fator = Decimal('1.00')
        for indice in indices:
            fator *= (1 + (Decimal(indice.valor) / 100))

        fator_aplicado = (fator - 1) * 100
        valor_sugerido = (valor_anterior * fator).quantize(Decimal("0.01"))

        return {
            "valor_anterior": valor_anterior,
            "valor_sugerido": valor_sugerido,
            "fator_aplicado": fator_aplicado.quantize(Decimal("0.01")),
            "indice_utilizado": contrato.fator_reajuste,
            "data_reajuste": data_reajuste,
        }
