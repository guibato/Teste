from django.db import models
from decimal import Decimal


class MovimentoConta(models.Model):
    """
    Modelo para registrar movimentações na conta dos proprietários.
    Inclui créditos, débitos e repasses efetuados.
    """
    TIPO_MOVIMENTO = (
        ('credito', 'Crédito'),
        ('debito', 'Débito'),
        ('repasse', 'Repasse Efetuado'),
    )

    proprietario = models.ForeignKey('Cliente', on_delete=models.CASCADE)
    contrato = models.ForeignKey('Contrato', on_delete=models.SET_NULL, null=True, blank=True)
    tipo = models.CharField(max_length=10, choices=TIPO_MOVIMENTO)
    descricao = models.CharField(max_length=255)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    data = models.DateField(auto_now_add=True)
    data_referencia = models.DateField(null=True, blank=True)  # mês/ano do aluguel

    class Meta:
        ordering = ['data']
        verbose_name = 'Movimento de Conta'
        verbose_name_plural = 'Movimentos de Conta'

    def __str__(self):
        return f"{self.data} - {self.get_tipo_display()} - {self.valor} - {self.descricao}"


class LancamentoContaCorrente(models.Model):
    """
    Modelo para registrar lançamentos simplificados na conta corrente dos proprietários.
    """
    TIPOS = [
        ('credito', 'Crédito'),
        ('debito', 'Débito'),
        ('repasse', 'Repasse'),
    ]
    
    proprietario = models.ForeignKey('Cliente', on_delete=models.CASCADE)
    data = models.DateField()
    tipo = models.CharField(max_length=10, choices=TIPOS)
    descricao = models.CharField(max_length=255)
    valor = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = 'Lançamento de Conta Corrente'
        verbose_name_plural = 'Lançamentos de Conta Corrente'

    def __str__(self):
        return f"{self.data} - {self.get_tipo_display()} - {self.valor} - {self.descricao}"
    
    
    @property
    def valor_formatado(self):
        """Retorna o valor formatado como moeda"""
        return f"R$ {self.valor:.2f}".replace('.', ',')
    
    @property
    def is_credito(self):
        """Verifica se é um lançamento de crédito"""
        return self.tipo == 'credito'
    
    @property
    def is_debito(self):
        """Verifica se é um lançamento de débito"""
        return self.tipo == 'debito'
    
    @property
    def is_repasse(self):
        """Verifica se é um lançamento de repasse"""
        return self.tipo == 'repasse'


class SaldoProprietario(models.Model):
    """
    Modelo para armazenar o saldo atual dos proprietários
    """
    proprietario = models.OneToOneField('Cliente', on_delete=models.CASCADE, related_name='saldo')
    saldo_atual = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    ultima_atualizacao = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Saldo de Proprietário'
        verbose_name_plural = 'Saldos de Proprietários'
    
    def __str__(self):
        return f"Saldo de {self.proprietario}: {self.saldo_formatado}"
    
    @property
    def saldo_formatado(self):
        """Retorna o saldo formatado como moeda"""
        return f"R$ {self.saldo_atual:.2f}".replace('.', ',')
    
    def adicionar_credito(self, valor, descricao, contrato=None, data_referencia=None):
        """
        Adiciona um valor ao saldo e cria um registro de movimento
        """
        self.saldo_atual += valor
        self.save()
        
        # Cria o registro de movimento
        MovimentoConta.objects.create(
            proprietario=self.proprietario,
            contrato=contrato,
            tipo='credito',
            descricao=descricao,
            valor=valor,
            data_referencia=data_referencia
        )
        
        return True
    
    def debitar(self, valor, descricao, contrato=None, data_referencia=None):
        """
        Debita um valor do saldo e cria um registro de movimento
        """
        self.saldo_atual -= valor
        self.save()
        
        # Cria o registro de movimento
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
        """
        Registra um repasse, debitando do saldo
        """
        self.saldo_atual -= valor
        self.save()
        
        # Cria o registro de movimento
        MovimentoConta.objects.create(
            proprietario=self.proprietario,
            contrato=contrato,
            tipo='repasse',
            descricao=descricao,
            valor=valor,
            data_referencia=data_referencia
        )
        
        return True