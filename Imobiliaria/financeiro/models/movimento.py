# financeiro/models/movimento.py
from django.db import models
from decimal import Decimal


# financeiro/models/movimento.py
from django.db import models
from decimal import Decimal


class MovimentoConta(models.Model):
    """
    Modelo único para registrar movimentações na conta dos proprietários:
    créditos (aluguel), débitos (taxas), repasses e ajustes manuais.
    """
    TIPO_MOVIMENTO = [
        ('credito', 'Crédito'),
        ('debito', 'Débito'),
        ('repasse', 'Repasse Efetuado'),
    ]

    proprietario = models.ForeignKey('core.Cliente', on_delete=models.CASCADE, related_name='movimentos_financeiro')
    contrato = models.ForeignKey('core.Contrato', on_delete=models.SET_NULL, null=True, blank=True, related_name='movimentos_financeiro')
    tipo = models.CharField(max_length=10, choices=TIPO_MOVIMENTO)
    descricao = models.CharField(max_length=255)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    data = models.DateField(auto_now_add=True)
    data_referencia = models.DateField(null=True, blank=True)
    origem_simplificada = models.BooleanField(default=False, help_text="Indica se foi um lançamento manual/simplificado")

    class Meta:
        ordering = ['data']
        verbose_name = 'Movimento de Conta'
        verbose_name_plural = 'Movimentos de Conta'

    def __str__(self):
        return f"{self.data} - {self.get_tipo_display()} - {self.valor_formatado} - {self.descricao}"

    @property
    def valor_formatado(self):
        return f"R$ {self.valor:.2f}".replace('.', ',')

    @property
    def is_credito(self):
        return self.tipo == 'credito'

    @property
    def is_debito(self):
        return self.tipo == 'debito'

    @property
    def is_repasse(self):
        return self.tipo == 'repasse'


class SaldoProprietario(models.Model):
    """
    Saldo atual consolidado do proprietário com métodos seguros de movimentação.
    """
    proprietario = models.OneToOneField('core.Cliente', on_delete=models.CASCADE, related_name='saldo_financeiro')
    saldo_atual = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    ultima_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Saldo de Proprietário'
        verbose_name_plural = 'Saldos de Proprietários'

    def __str__(self):
        return f"Saldo de {self.proprietario}: {self.saldo_formatado}"

    @property
    def saldo_formatado(self):
        return f"R$ {self.saldo_atual:.2f}".replace('.', ',')

    def adicionar_credito(self, valor, descricao, contrato=None, data_referencia=None):
        self.saldo_atual += valor
        self.save()
        MovimentoConta.objects.create(
            proprietario=self.proprietario,
            contrato=contrato,
            tipo='credito',
            descricao=descricao,
            valor=valor,
            data_referencia=data_referencia
        )
        return True

    def debitar(self, valor, descricao, contrato=None, data_referencia=None, permitir_negativo=False):
        if not permitir_negativo and self.saldo_atual < valor:
            raise ValueError("Saldo insuficiente para débito.")
        self.saldo_atual -= valor
        self.save()
        MovimentoConta.objects.create(
            proprietario=self.proprietario,
            contrato=contrato,
            tipo='debito',
            descricao=descricao,
            valor=valor,
            data_referencia=data_referencia
        )
        return True

    def registrar_repasse(self, valor, descricao, contrato=None, data_referencia=None):
        return self.debitar(valor, descricao, contrato, data_referencia)

