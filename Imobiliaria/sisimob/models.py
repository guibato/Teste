from django.db import models

class Cliente(models.Model):
    TIPO_CLIENTE_CHOICES = [
        ('Proprietario', 'Proprietário(a)'),
        ('Inquilino', 'Inquilino(a)'),
        ('Anuente', 'Anuente'),
        ('Fiador(a)', 'Fiador(a)'),
    ]

    MODALIDADE_PIX_CHOICES = [
        ('cpf', 'CPF'),
        ('email', 'E-mail'),
        ('telefone', 'Telefone'),
        ('aleatorio', 'Chave Aleatória'),
    ]

    ESTADO_CIVIL_CHOICES = [
        ('Solteiro', 'Solteiro(a)'),
        ('Casado', 'Casado(a)'),
        ('Divorciado', 'Divorciado(a)'),
        ('Viuvo', 'Viúvo(a)'),
    ]

    REGIME_CASAMENTO_CHOICES = [
        ('comunhao_total', 'Comunhão Total de Bens'),
        ('comunhao_parcial', 'Comunhão Parcial de Bens'),
        ('separacao_total', 'Separação Total de Bens'),
    ]

    tipo = models.CharField(max_length=20, choices=TIPO_CLIENTE_CHOICES, verbose_name="Tipo")
    nome = models.CharField(max_length=100, verbose_name="Nome")
    nacionalidade = models.CharField(max_length=100, null=True, blank=True, verbose_name="Nacionalidade")
    profissao = models.CharField(max_length=100, null=True, blank=True, verbose_name="Profissão")
    estado_civil = models.CharField(max_length=20, choices=ESTADO_CIVIL_CHOICES, null=True, blank=True)
    regime_casamento = models.CharField(max_length=20, choices=REGIME_CASAMENTO_CHOICES, null=True, blank=True)
    anuente = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Anuente")
    telefone = models.CharField(max_length=15, null=True, blank=True, verbose_name="Telefone")
    codigo_internacional_celular = models.CharField(max_length=5, null=True, blank=True, verbose_name="Código Internacional (Celular)")
    celular = models.CharField(max_length=15, null=True, blank=True, verbose_name="Celular")
    email = models.EmailField(null=True, blank=True, verbose_name="E-mail")
    pix_modalidade = models.CharField(max_length=20, choices=MODALIDADE_PIX_CHOICES, null=True, blank=True, verbose_name="Modalidade PIX")
    chave_pix = models.CharField(max_length=100, null=True, blank=True, verbose_name="Chave PIX")
    banco = models.CharField(max_length=100, null=True, blank=True, verbose_name="Banco")
    agencia = models.CharField(max_length=100, null=True, blank=True, verbose_name="Agência")
    conta_corrente = models.CharField(max_length=100, null=True, blank=True, verbose_name="Conta Corrente")
    poupanca = models.CharField(max_length=100, null=True, blank=True, verbose_name="Poupança")
    cep = models.CharField(max_length=10, verbose_name="CEP")
    endereco = models.CharField(max_length=255, verbose_name="Endereço")
    numero = models.CharField(max_length=10, verbose_name="Número")
    complemento = models.CharField(max_length=100, null=True, blank=True, verbose_name="Complemento")
    bairro = models.CharField(max_length=100, null=True, blank=True, verbose_name="Bairro")
    cidade = models.CharField(max_length=100, verbose_name="Cidade")
    estado = models.CharField(max_length=2, verbose_name="Estado")
    documento = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return self.nome

class Imovel(models.Model):
    cep = models.CharField(max_length=10, verbose_name="CEP")
    endereco = models.CharField(max_length=255, verbose_name="Endereço")
    numero = models.CharField(max_length=10, verbose_name="Número")
    complemento = models.CharField(max_length=100, null=True, blank=True, verbose_name="Complemento")
    bairro = models.CharField(max_length=100, null=True, blank=True, verbose_name="Bairro")
    cidade = models.CharField(max_length=100, verbose_name="Cidade")
    estado = models.CharField(max_length=2, verbose_name="Estado")
    iptu = models.CharField(max_length=14, null=True, blank=True, verbose_name="IPTU")
    comgas = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Comgás")
    sabesp = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Sabesp")
    enel = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Enel")

    def __str__(self):
        if self.complemento:
            return f"{self.endereco}, {self.numero} - {self.complemento}"
        return f"{self.endereco}, {self.numero}"

class Contrato(models.Model):
    CONTRATO_CHOICES = [
        ('residencial', 'Residencial'),
        ('comercial', 'Comercial'),
        ('nao_residencial', 'Não-Residencial'),
    ]

    REAJUSTE_CHOICES = [
        ('IPCA', 'IPC-A'),
        ('IGPM', 'IGP-M'),
    ]

    MULTA_CHOICES = [
        ('3MPR', '3M Pró Rata'),
        ('3MF', '3M Flat'),
        ('6MPR', '6M Pró Rata'),
        ('6MF', '6M Flat'),
    ]

    TIPO_TAXA_CHOICES = [
        ('percentual', 'Percentual (%)'),
        ('fixo', 'Fixo (R$)'),
    ]

    CAUCAO_CHOICES = [
        ('fiador', 'Fiador'),
        ('caucao', 'Caução'),
        ('seguro_fianca', 'Seguro Fiança'),
        ('capitalizacao', 'Capitalização'),
        ('sem_garantia', 'Sem Garantia'),
    ]

    tipo = models.CharField(max_length=20, choices=CONTRATO_CHOICES, null=True, blank=True)
    ativo = models.BooleanField(default=True)
    tipo_contrato = models.CharField(max_length=20, choices=CONTRATO_CHOICES, null=True, blank=True)
    proprietario = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="contratos_proprietario")
    inquilino = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="contratos_inquilino")
    imovel = models.ForeignKey(Imovel, on_delete=models.CASCADE, related_name="contratos_imovel")

    data_inicio = models.DateField(verbose_name="Início")
    data_fim = models.DateField(verbose_name="Fim")
    carencia_dias = models.IntegerField(verbose_name="Carência", null=True, blank=True, default=0)
    fator_reajuste = models.CharField(max_length=5, choices=REAJUSTE_CHOICES, verbose_name="Reajuste")
    multa_contratual = models.CharField(max_length=20, choices=MULTA_CHOICES, verbose_name="Multa Contratual")

    TIPO_PAGAMENTO_CHOICES = [
        ('pacote', 'Pacote'),
        ('despesas_separadas', 'Despesas Separadas'),
    ]

    tipo_pagamento = models.CharField(
        max_length=50,
        choices=TIPO_PAGAMENTO_CHOICES,
        verbose_name="Tipo de Aluguel",  # Corrigido o typo "verbo se_name"
        default='despesas_separadas'  # Valor padrão opcional
    )
    valor_aluguel = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor do Aluguel", null=True, blank=True, default=0.00)
    valor_pacote = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor do Pacote", null=True, blank=True, default=0.00)
    valor_condominio = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Condomínio", null=True, blank=True, default=0.00)
    valor_iptu = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="IPTU", null=True, blank=True, default=0.00)
    valor_outros = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Outros", null=True, blank=True, default=0.00)

    tipo_taxa = models.CharField(max_length=50, choices=TIPO_TAXA_CHOICES, verbose_name="Tipo de Taxa")
    valor_taxa_administracao_percentual = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Adm - %", null=True, blank=True, default=0.00)
    valor_taxa_administracao_fixo = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Adm - R$", null=True, blank=True, default=0.00)

    dia_pagamento = models.IntegerField(verbose_name="Dia de Pagamento")

    garantia = models.CharField(max_length=50, choices=CAUCAO_CHOICES, verbose_name="Garantia")
    fiador = models.CharField(max_length=100, verbose_name="Fiador", null=True, blank=True)
    valor_caucao = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor Caução", null=True, blank=True, default=0.00)
    valor_segfi = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor Fiança", null=True, blank=True, default=0.00)
    apolice_segfi = models.CharField(max_length=50, verbose_name="Apólice Fiança", null=True, blank=True)
    seg_segfi = models.CharField(max_length=100, verbose_name="Seguradora Fiança", null=True, blank=True)
    valor_cap = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor Capitalização", null=True, blank=True, default=0.00)
    apolice_cap = models.CharField(max_length=50, verbose_name="Apólice Capitalização", null=True, blank=True)
    seg_cap = models.CharField(max_length=100, verbose_name="Seguradora Capitalização", null=True, blank=True)

    clausula_12meses = models.BooleanField(default=False, verbose_name="Cláusula de 12 Meses?")

    seguradora_incendio = models.CharField(max_length=100, verbose_name="Seguradora", null=True, blank=True)
    apolice_incendio = models.CharField(max_length=50, verbose_name="Apólice", null=True, blank=True)
    valor_seguro = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor do Seguro", null=True, blank=True, default=0.00)
    vencimento_seguro = models.DateField(verbose_name="Vencimento do Seguro", null=True, blank=True)

    documentos = models.FileField(
        upload_to='contratos/documentos/',  # Pasta de upload
        null=True,
        blank=True,
        verbose_name="Documentos"
    )

    def __str__(self):
        return f"Contrato {self.id} - {self.imovel.endereco}"
    
class Cobranca(models.Model):
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('paga', 'Paga'),
        ('atrasada', 'Atrasada'),
        ('cancelada', 'Cancelada'),
    ]

    contrato = models.ForeignKey(Contrato, on_delete=models.CASCADE)
    mes_referencia = models.IntegerField()
    ano_referencia = models.IntegerField()
    data_vencimento = models.DateField()
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pendente')
    data_pagamento = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['-ano_referencia', '-mes_referencia']

    def __str__(self):
        return f"Cobrança {self.mes_referencia}/{self.ano_referencia} - {self.contrato.imovel.endereco}"

class IndiceInflacao(models.Model):
    tipo = models.CharField(max_length=50, verbose_name="Nome do Índice")
    valor = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor do Índice")
    data_referencia = models.DateField(verbose_name="Data de Referência")

    def __str__(self):
        # Mudar de 'self.nome' para 'self.tipo'
        return f"{self.tipo} - {self.data_referencia.strftime('%Y-%m')}"