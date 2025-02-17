from django.db import models

class Cliente(models.Model):
    # Tipos de cliente
    TIPO_CLIENTE_CHOICES = [
        ('Proprietario', 'Proprietário(a)'),
        ('Inquilino', 'Inquilino(a)'),
        ('Anuente', 'Anuente'),
        ('Fiador(a)', 'Fiador(a)'),
    ]

    # Modalidades de PIX
    MODALIDADE_PIX_CHOICES = [
        ('cpf', 'CPF'),
        ('email', 'E-mail'),
        ('telefone', 'Telefone'),
        ('aleatorio', 'Chave Aleatória'),
    ]

    # Estados civis
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
    nacionalidade = models.CharField(max_length=100, blank=True, null=True, verbose_name="Nacionalidade")
    profissao = models.CharField(max_length=100, blank=True, null=True, verbose_name="Profissão")
    estado_civil = models.CharField(max_length=20, choices=ESTADO_CIVIL_CHOICES, blank=True, null=True)
    regime_casamento = models.CharField(max_length=20, choices=REGIME_CASAMENTO_CHOICES, blank=True, null=True)
    anuente = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, limit_choices_to={'tipo': 'Anuente'}, verbose_name="Anuente")
    telefone = models.CharField(max_length=15, blank=True, null=True, verbose_name="Telefone")
    codigo_internacional_celular = models.CharField(max_length=5, blank=True, null=True, verbose_name="Código Internacional (Celular)")
    celular = models.CharField(max_length=15, blank=True, null=True, verbose_name="Celular")  # Tornado opcional
    email = models.EmailField(blank=True, null=True, verbose_name="E-mail")
    pix_modalidade = models.CharField(max_length=20, choices=MODALIDADE_PIX_CHOICES, blank=True, null=True, verbose_name="Modalidade PIX")
    chave_pix = models.CharField(max_length=100, blank=True, null=True, verbose_name="Chave PIX")
    banco = models.CharField(max_length=100, blank=True, null=True, verbose_name="Banco")
    agencia = models.CharField(max_length=100, blank=True, null=True, verbose_name="Agência")
    conta_corrente = models.CharField(max_length=100, blank=True, null=True, verbose_name="Conta Corrente")
    poupanca = models.CharField(max_length=100, blank=True, null=True, verbose_name="Poupança")
    cep = models.CharField(max_length=10, verbose_name="CEP")
    endereco = models.CharField(max_length=255, verbose_name="Endereço")
    numero = models.CharField(max_length=10, verbose_name="Número")
    complemento = models.CharField(max_length=100, blank=True, null=True, verbose_name="Complemento")
    bairro = models.CharField(max_length=100, blank=True, null=True, verbose_name="Bairro")
    cidade = models.CharField(max_length=100, verbose_name="Cidade")
    estado = models.CharField(max_length=2, verbose_name="Estado")
    documento = models.FileField(upload_to='documentos/', blank=True, null=True)
    

    def __str__(self):
        return f"{self.nome}"
    
class Imovel(models.Model):
    cep = models.CharField(max_length=10, verbose_name="CEP")
    endereco = models.CharField(max_length=255, verbose_name="Endereço")
    numero = models.CharField(max_length=10, verbose_name="Número")
    complemento = models.CharField(max_length=100, blank=True, null=True, verbose_name="Complemento")
    bairro = models.CharField(max_length=100, blank=True, null=True, verbose_name="Bairro")
    cidade = models.CharField(max_length=100, verbose_name="Cidade")
    estado = models.CharField(max_length=2, verbose_name="Estado")
    iptu = models.CharField(max_length=14, blank=True, null=True, verbose_name="IPTU")  # Armazena apenas números
    comgas = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="Comgás")
    sabesp = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="Sabesp")
    enel = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="Enel")

    def __str__(self):
        if self.complemento == None:
            return f"{self.endereco}, {self.numero}"
        return f"{self.endereco}, {self.numero} - {self.complemento}"
    
class Contrato(models.Model):

    CONTRATO_CHOICES = [
        ('residencial', 'Residencial'),
        ('comercial', 'Comercial'),
        ('nao_residencial', 'Não-Residencial'),
    ]
    TIPO_CLIENTE_CHOICES = [
        ('Proprietário(a)', 'Proprietário(a)'),
        ('Inquilino(a)', 'Inquilino(a)'),
        ('Anuente', 'Anuente'),
        ('Fiador(a)', 'Fiador(a)'),
    ]
    REAJUSTE_CHOICES = [
        ('IPCA', 'IPC-A'),
        ('IGPM', 'IGP-M'),
    ]

    # Campos básicos
    tipo = models.CharField(max_length=20, choices=TIPO_CLIENTE_CHOICES, verbose_name="Tipo")
    ativo = models.BooleanField(default=True, verbose_name="Ativo?")
    tipo_contrato = models.CharField(max_length=20, choices=CONTRATO_CHOICES, blank=True, null=True)
    proprietario = models.ForeignKey(
        Cliente,
        on_delete=models.CASCADE,
        related_name='contratos_proprietario', 
        limit_choices_to={'tipo': 'Proprietário(a)'}, # Nome único para o acessor reverso
        verbose_name="Proprietário"
    )
    inquilino = models.ForeignKey(
        Cliente,
        on_delete=models.CASCADE,
        related_name='contratos_inquilino',
          limit_choices_to={'tipo': 'Inquilino(a)'},  # Nome único para o acessor reverso
        verbose_name="Inquilino"
    )
    imovel = models.ForeignKey(
        Imovel,
        on_delete=models.CASCADE,
        related_name='contratos_imovel',  # Nome único para o acessor reverso
        verbose_name="Imóvel"
    )

    # Datas e condições
    data_inicio = models.DateField(verbose_name="Início")
    data_fim = models.DateField(verbose_name="Final")
    carencia_dias = models.IntegerField(verbose_name="Carência")
    fator_reajuste = models.DecimalField(max_digits=5, decimal_places=2, choices=REAJUSTE_CHOICES, verbose_name="Reajuste")
    multa_contratual = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Multa Contratual")

    # Valores e pagamentos
    tipo_pagamento = models.CharField(max_length=50, verbose_name="Tipo de Aluguel")
    valor_aluguel = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor do Aluguel")
    valor_pacote = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor do Pacote", null=True, blank=True)
    condominio = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Condomínio", null=True, blank=True)
    iptu = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="IPTU", null=True, blank=True)
    outros = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Outros", null=True, blank=True)

    # Taxas
    tipo_taxa = models.CharField(max_length=50, verbose_name="Tipo de Taxa")
    valor_taxa_administracao = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor da Taxa de Administração")
    dia_pagamento = models.IntegerField(verbose_name="Dia de Pagamento")

    # Garantias
    garantia = models.CharField(max_length=50, verbose_name="Garantia")
    fiador = models.CharField(max_length=100, verbose_name="Fiador", null=True, blank=True)
    valor_caucao = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor Caução", null=True, blank=True)

    # Cláusulas
    clausula_12meses = models.BooleanField(default=False, verbose_name="Cláusula de 12 Meses?")

    # Seguro contra incêndio
    seguradora_incendio = models.CharField(max_length=100, verbose_name="Seguradora", null=True, blank=True)
    apolice_incendio = models.CharField(max_length=50, verbose_name="Apólice", null=True, blank=True)
    valor_seguro = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor do Seguro", null=True, blank=True)
    vencimento_seguro = models.DateField(verbose_name="Vencimento do Seguro", null=True, blank=True)

    # Documentos
    documentos = models.FileField(upload_to='documentos/', verbose_name="Documentos", null=True, blank=True)

    def __str__(self):
        return f"Contrato {self.tipo_contrato} - {self.imovel}"