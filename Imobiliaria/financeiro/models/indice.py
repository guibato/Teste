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

    def calcular_acumulado_12_meses(self):
        """
        Calcula o acumulado dos últimos 12 meses INCLUINDO o mês atual.
        Fórmula: ((1 + m1/100) * (1 + m2/100) * ... * (1 + m12/100) - 1) * 100
        """
        # Data de início: 11 meses antes do mês atual
        data_inicio = self.data_referencia - relativedelta(months=11)
        
        # Busca os últimos 12 meses (incluindo o atual)
        indices = IndiceInflacao.objects.filter(
            tipo=self.tipo,
            data_referencia__gte=data_inicio,
            data_referencia__lte=self.data_referencia  # ✅ Inclui o mês atual
        ).order_by('data_referencia')

        if indices.count() < 12:
            # Se não tiver 12 meses completos, retorna None
            return None

        # Calcula o acumulado usando juros compostos
        acumulado = Decimal('1.0')
        for indice in indices:
            acumulado *= (Decimal('1.0') + (indice.valor / CEM))
        
        # Converte para percentual e arredonda
        resultado = ((acumulado - Decimal('1.0')) * CEM).quantize(Decimal('0.0001'))
        return resultado

    def save(self, *args, **kwargs):
        """Salva o índice e calcula o acumulado 12 meses"""
        # Salva primeiro para garantir que o registro existe
        super().save(*args, **kwargs)
        
        # Calcula e atualiza o acumulado
        novo_acumulado = self.calcular_acumulado_12_meses()
        if novo_acumulado is not None and novo_acumulado != self.acumulado_12_meses:
            self.acumulado_12_meses = novo_acumulado
            # Salva novamente apenas se o acumulado mudou
            super().save(update_fields=['acumulado_12_meses'])

    @classmethod
    def recalcular_acumulados(cls, tipo_indice=None):
        """
        Recalcula todos os acumulados de 12 meses para um tipo específico ou todos.
        Use após importar dados em lote.
        """
        filtro = {'tipo': tipo_indice} if tipo_indice else {}
        
        # Busca todos os índices que precisam ser recalculados
        indices = cls.objects.filter(**filtro).order_by('tipo', 'data_referencia')
        
        atualizados = 0
        for indice in indices:
            novo_acumulado = indice.calcular_acumulado_12_meses()
            if novo_acumulado is not None and novo_acumulado != indice.acumulado_12_meses:
                indice.acumulado_12_meses = novo_acumulado
                indice.save(update_fields=['acumulado_12_meses'])
                atualizados += 1
        
        return atualizados

    @classmethod
    def calcular_valor_reajustado(cls, valor_base, tipo_indice, data_inicio, data_fim=None):
        """
        Calcula o valor reajustado entre duas datas.
        Para aluguéis, use data_inicio = data do último reajuste e data_fim = hoje.
        """
        if data_fim is None:
            data_fim = date.today()

        # Normaliza para o primeiro dia do mês
        data_inicio = date(data_inicio.year, data_inicio.month, 1)
        data_fim = date(data_fim.year, data_fim.month, 1)

        # Busca os índices no período (excluindo o mês inicial, incluindo o final)
        indices = cls.objects.filter(
            tipo=tipo_indice,
            data_referencia__gt=data_inicio,  # Exclui o mês inicial
            data_referencia__lte=data_fim     # Inclui o mês final
        ).order_by('data_referencia')

        valor_reajustado = Decimal(str(valor_base))
        for indice in indices:
            valor_reajustado *= (Decimal('1.0') + (indice.valor / CEM))

        return valor_reajustado.quantize(Decimal('0.01'))

    @classmethod
    def ultimo_acumulado(cls, tipo_indice):
        """Retorna o último índice com acumulado calculado"""
        return cls.objects.filter(
            tipo=tipo_indice, 
            acumulado_12_meses__isnull=False
        ).order_by('-data_referencia').first()

    @classmethod
    def obter_acumulado_periodo(cls, tipo_indice, data_inicio, data_fim):
        """
        Calcula o acumulado entre duas datas específicas.
        Útil para reajustes de contratos com datas específicas.
        """
        indices = cls.objects.filter(
            tipo=tipo_indice,
            data_referencia__gt=data_inicio,
            data_referencia__lte=data_fim
        ).order_by('data_referencia')

        if not indices.exists():
            return Decimal('0.0000')

        acumulado = Decimal('1.0')
        for indice in indices:
            acumulado *= (Decimal('1.0') + (indice.valor / CEM))
        
        return ((acumulado - Decimal('1.0')) * CEM).quantize(Decimal('0.0001'))