# models/indice.py
from django.db import models
from decimal import Decimal


class IndiceInflacao(models.Model):
    """
    Modelo para armazenar índices de inflação (IPCA, IGP-M, etc.)
    Utilizados para cálculos de reajustes de contratos.
    """
    TIPO_CHOICES = [
        ('IPCA', 'IPC-A'),
        ('IGPM', 'IGP-M'),
        ('INPC', 'INPC'),
        ('OUTRO', 'Outro Índice'),
    ]
    
    tipo = models.CharField(
        max_length=50, 
        choices=TIPO_CHOICES,
        verbose_name="Nome do Índice"
    )
    valor = models.DecimalField(
        max_digits=10, 
        decimal_places=4, 
        verbose_name="Valor do Índice"
    )
    data_referencia = models.DateField(
        verbose_name="Data de Referência"
    )
    acumulado_12_meses = models.DecimalField(
        max_digits=10, 
        decimal_places=4, 
        verbose_name="Acumulado 12 meses",
        null=True, 
        blank=True
    )
    fonte = models.CharField(
        max_length=100, 
        null=True, 
        blank=True,
        verbose_name="Fonte da Informação"
    )
    data_cadastro = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data de Cadastro"
    )

    class Meta:
        verbose_name = "Índice de Inflação"
        verbose_name_plural = "Índices de Inflação"
        ordering = ['-data_referencia']
        unique_together = ['tipo', 'data_referencia']
        indexes = [
            models.Index(fields=['tipo', 'data_referencia']),
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.data_referencia.strftime('%m/%Y')} - {self.valor}%"

    def save(self, *args, **kwargs):
        """
        Sobrescreve o método save para calcular o acumulado dos últimos 12 meses
        caso não seja informado manualmente.
        """
        if not self.acumulado_12_meses:
            # Calcula o acumulado dos últimos 12 meses
            from dateutil.relativedelta import relativedelta
            data_inicio = self.data_referencia - relativedelta(months=12)
            
            indices = IndiceInflacao.objects.filter(
                tipo=self.tipo,
                data_referencia__gte=data_inicio,
                data_referencia__lt=self.data_referencia
            ).order_by('data_referencia')
            
            # Cálculo do acumulado
            acumulado = Decimal('1.0')
            for indice in indices:
                acumulado *= (Decimal('1.0') + (indice.valor / Decimal('100.0')))
            
            # Transforma em percentual e subtrai 1
            self.acumulado_12_meses = ((acumulado - Decimal('1.0')) * Decimal('100.0')).quantize(Decimal('0.0001'))
            
        super().save(*args, **kwargs)

    @classmethod
    def calcular_valor_reajustado(cls, valor_base, tipo_indice, data_inicio, data_fim=None):
        """
        Calcula o valor reajustado com base no índice escolhido e no período.
        
        Args:
            valor_base: Valor inicial para reajuste
            tipo_indice: Tipo do índice (IPCA, IGPM, etc)
            data_inicio: Data inicial do período
            data_fim: Data final do período (se None, usa data atual)
            
        Returns:
            Decimal: valor reajustado
        """
        from datetime import date
        from dateutil.relativedelta import relativedelta
        
        if data_fim is None:
            data_fim = date.today()
            
        # Ajusta para primeiro dia do mês
        data_inicio = date(data_inicio.year, data_inicio.month, 1)
        data_fim = date(data_fim.year, data_fim.month, 1)
        
        # Obtém índices do período
        indices = cls.objects.filter(
            tipo=tipo_indice,
            data_referencia__gte=data_inicio,
            data_referencia__lt=data_fim
        ).order_by('data_referencia')
        
        # Calcula o reajuste
        valor_reajustado = Decimal(str(valor_base))
        for indice in indices:
            valor_reajustado *= (Decimal('1.0') + (indice.valor / Decimal('100.0')))
            
        return valor_reajustado.quantize(Decimal('0.01'))