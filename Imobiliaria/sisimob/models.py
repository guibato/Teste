from django.db import models
from django.utils import timezone
from decimal import Decimal
from dateutil.relativedelta import relativedelta

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
    CPF = models.CharField(max_length=14, null=True, blank=True, verbose_name="CPF")
    rg_rne = models.CharField(max_length=20, null=True, blank=True, unique=True, verbose_name="RG/RNE")
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

    def clean(self):
        super().clean()
        if self.rg_rne and Cliente.objects.filter(rg_rne=self.rg_rne).exclude(pk=self.pk).exists():
            raise ValidationError({'rg_rne': 'Este RG/RNE já está cadastrado.'})

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
    class Meta:
        ordering = ['-data_inicio']

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
        ('FIADOR', 'Fiador'),
        ('CAUCAO', 'Caução'),
        ('SEGURO_FIANCA', 'Seguro Fiança'),
        ('CAPITALIZACAO', 'Capitalização'),
        ('SEM_GARANTIA', 'Sem Garantia'),
    ]
    
    id = models.AutoField(primary_key=True)
    tipo = models.CharField(max_length=20, choices=CONTRATO_CHOICES, null=True, blank=True, verbose_name="Tipo")
    ativo = models.BooleanField(default=True, verbose_name="Ativo")
    tipo_contrato = models.CharField(max_length=20, choices=CONTRATO_CHOICES, null=True, blank=True, verbose_name="Tipo de Contrato")
    proprietario = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="contratos_proprietario", verbose_name="Proprietário")
    inquilino = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="contratos_inquilino", verbose_name="Inquilino")
    imovel = models.ForeignKey(Imovel, on_delete=models.CASCADE, related_name="contratos_imovel", verbose_name="Imóvel")
    data_inicio = models.DateField(verbose_name="Início")
    data_fim = models.DateField(verbose_name="Fim")
    carencia_dias = models.IntegerField(verbose_name="Carência (dias)", null=True, blank=True, default=0)
    fator_reajuste = models.CharField(max_length=5, choices=REAJUSTE_CHOICES, verbose_name="Fator de Reajuste")
    multa_contratual = models.CharField(max_length=20, choices=MULTA_CHOICES, verbose_name="Multa Contratual")
    TIPO_PAGAMENTO_CHOICES = [
        ('pacote', 'Pacote'),
        ('despesas_separadas', 'Despesas Separadas'),
    ]
    tipo_pagamento = models.CharField(
        max_length=50,
        choices=TIPO_PAGAMENTO_CHOICES,
        verbose_name="Tipo de Aluguel",
        default='despesas_separadas'
    )
    valor_aluguel = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor do Aluguel", null=True, blank=True, default=Decimal('0.00'))
    valor_pacote = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor do Pacote", null=True, blank=True, default=Decimal('0.00'))
    tipo_taxa = models.CharField(max_length=50, choices=TIPO_TAXA_CHOICES, verbose_name="Tipo de Taxa")
    valor_taxa_administracao_percentual = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Adm - %", null=True, blank=True, default=Decimal('0.00'))
    valor_taxa_administracao_fixo = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Adm - R$", null=True, blank=True, default=Decimal('0.00'))
    dia_pagamento = models.IntegerField(verbose_name="Dia de Pagamento")
    garantia = models.CharField(max_length=50, choices=CAUCAO_CHOICES, verbose_name="Garantia")
    fiador = models.ForeignKey(Cliente, on_delete=models.SET_NULL, null=True, blank=True, related_name="contratos_fiador", verbose_name="Fiador")
    valor_caucao = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor Caução", null=True, blank=True, default=Decimal('0.00'))
    seguradora = models.CharField(max_length=100, verbose_name="Seguradora", null=True, blank=True)
    apolice = models.CharField(max_length=50, verbose_name="Apólice", null=True, blank=True)
    valor_seguro_incendio = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor do Seguro", null=True, blank=True, default=Decimal('0.00'))
    vencimento_seguro_incendio = models.DateField(verbose_name="Vencimento do Seguro", null=True, blank=True)
    documentos = models.FileField(upload_to='contratos/documentos/', null=True, blank=True, verbose_name="Documentos")
    historico_aluguel = models.JSONField(default=dict, verbose_name="Histórico de Aluguel")

    def __str__(self):
        return f"Contrato {self.id} - {self.imovel.endereco}"

    def save(self, *args, **kwargs):
        if not self.historico_aluguel or str(self.data_inicio) not in self.historico_aluguel:
            if self.historico_aluguel:
                ultima_data = sorted(self.historico_aluguel.keys())[-1]
                self.historico_aluguel[str(self.data_inicio)] = self.historico_aluguel[ultima_data]
            else:
                self.historico_aluguel[str(self.data_inicio)] = float(self.valor_aluguel)
        super().save(*args, **kwargs)

    def valor_taxa_administracao(self):
        if self.tipo_taxa == 'percentual':
            return (self.valor_aluguel * self.valor_taxa_administracao_percentual) / 100
        elif self.tipo_taxa == 'fixa':
            return self.valor_taxa_administracao_fixo
        return Decimal('0.00')
    
    @property
    def taxa_administracao_display(self):
        """Retorna a representação textual da taxa para exibição"""
        if self.tipo_taxa == 'percentual':  # Corrigido para comparar com 'percentual'
            return f"{self.valor_taxa_administracao_percentual}%"
        elif self.tipo_taxa == 'fixo':  # Corrigido para comparar com 'fixo'
            return f"R$ {self.valor_taxa_administracao_fixo}"
        return "Isento"

    def valor_aluguel_com_reajuste(self, mes_ano):
        """
        Calcula o valor do aluguel reajustado com base no índice de inflação (ex.: IPCA).
        """
        indices = IndiceInflacao.objects.filter(
            tipo=self.fator_reajuste,
            data_referencia__lte=mes_ano
        ).order_by('data_referencia')
        valor_reajustado = self.valor_aluguel
        for indice in indices:
            valor_reajustado *= (1 + indice.valor / 100)
        return valor_reajustado

    def calcular_aluguel_projetado(self):
        """
        Calcula o Aluguel Projetado com base na inflação acumulada desde o início do contrato até o mês e ano atual.
        """
        hoje = timezone.now().date()
        max_data_final = self.data_inicio + relativedelta(months=+12)
        data_final = min(max_data_final, hoje)
        indices = IndiceInflacao.objects.filter(
            tipo=self.fator_reajuste,
            data_referencia__gte=self.data_inicio.replace(day=1),
            data_referencia__lte=data_final.replace(day=1),
        ).order_by('data_referencia')
        fator_acumulado = Decimal('1.0')
        for indice in indices:
            taxa = Decimal(str(indice.valor)) / 100
            fator_acumulado *= (1 + taxa)
        if self.tipo_pagamento == 'despesas_separadas':
            valor_base = self.valor_aluguel or Decimal('0.00')
        else:
            valor_base = self.valor_pacote or Decimal('0.00')
        aluguel_projetado = valor_base * fator_acumulado
        return aluguel_projetado.quantize(Decimal('0.01'))

    @property
    def valor_repasse(self):
        """
        Calcula o valor do repasse ao proprietário:
        - Desconta a taxa de administração do valor do aluguel.
        - Soma as demais despesas (condomínio, IPTU, outros).
        """
        if self.tipo_pagamento == 'despesas_separadas':
            taxa_administracao = self.valor_taxa_administracao()
            despesas_totais = sum(despesa.calcular_valor_parcela() for despesa in self.despesas.all())
            repasse = (
                self.valor_aluguel -
                taxa_administracao +
                despesas_totais
            )
            return max(repasse, Decimal('0.00'))  # Garante que o valor não seja negativo
        else:
            return self.valor_pacote

    def calcular_valor_total(self):
        """
        Calcula o valor total da cobrança para este contrato:
        - Inclui o valor do aluguel (ou pacote).
        - Adiciona as despesas separadas (condomínio, IPTU, outros).
        - Não inclui a taxa de administração, pois ela é descontada no repasse.
        """
        if self.tipo_pagamento == 'despesas_separadas':
            valor_total = self.valor_aluguel
            despesas_totais = sum(despesa.calcular_valor_parcela() for despesa in self.despesas.all())
            valor_total += despesas_totais
        else:
            valor_total = self.valor_pacote
        return max(valor_total, Decimal('0.00'))  # Garante que o valor não seja negativo

class Cobranca(models.Model):
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('paga', 'Recebida'),
        ('atrasada', 'Atrasada'),
        ('cancelada', 'Cancelada'),
    ]
    STATUS_REPASSE_CHOICES = [
        ('pendente', 'Pendente'),
        ('repassado', 'Repassada'),
        ('cancelado', 'Cancelado'),
    ]

    contrato = models.ForeignKey('Contrato', on_delete=models.CASCADE, related_name='cobrancas')
    mes_referencia = models.PositiveSmallIntegerField()
    ano_referencia = models.PositiveSmallIntegerField()
    data_vencimento = models.DateField(verbose_name="Data de Vencimento")
    valor = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor da Cobrança")
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pendente',
        verbose_name="Status do Pagamento"
    )
    
    status_repasse = models.CharField(
        max_length=10,
        choices=STATUS_REPASSE_CHOICES,
        default='pendente',
        verbose_name="Status do Repasse"
    )
    
    data_pagamento = models.DateField(null=True, blank=True, verbose_name="Data de Pagamento")
    data_repasse = models.DateField(null=True, blank=True, verbose_name="Data de Repasse")

    @property
    def valor_administracao(self):
        """Calcula o valor da taxa de administração baseado no valor do aluguel"""
        if not hasattr(self.contrato, 'tipo_taxa'):
            return Decimal('0.00')
        
        valor_aluguel = self.contrato.valor_aluguel  # Obter o valor do aluguel do contrato
        
        if self.contrato.tipo_taxa == 'percentual':
            percentual = self.contrato.valor_taxa_administracao_percentual or Decimal('0.00')
            return (valor_aluguel * percentual) / 100  # Cálculo da taxa de administração como percentual do aluguel
        elif self.contrato.tipo_taxa == 'fixa':
            return self.contrato.valor_taxa_administracao_fixo or Decimal('0.00')  # Taxa fixa
        return Decimal('0.00')

    @property
    def valor_boleto(self):
        """
        Calcula o valor total do boleto, somando as despesas relevantes.
        As despesas podem ser ou não base de cálculo da taxa de administração.
        """
        # Despesas que são base de cálculo para a cobrança do cliente
        despesas_relevantes = self.despesas_para_cobrar_cliente
        return self.valor + despesas_relevantes

    @property
    def despesas_para_cobrar_cliente(self):
        """Calcula as despesas que serão cobradas do cliente (só as relevantes)"""
        despesas_mes = Despesa.objects.filter(
            contrato=self.contrato,
            data_inicio__lte=self.data_vencimento  # Apenas despesas com início antes do vencimento
        )

        total = Decimal('0.00')
        for despesa in despesas_mes:
            # Verificar se a despesa é base para a cobrança
            if despesa.is_base_calculo_administracao:
                # Se for, somamos ao total da cobrança
                total += despesa.valor

        return total

    @property
    def valor_liquido(self):
        """Calcula o valor líquido: Aluguel - Administração + Despesas Repasse - Despesas Deduzidas"""
        return self.valor - self.valor_administracao

    @property
    def total_despesas_repassadas(self):
        """Calcula o total de despesas repassadas para esta cobrança"""
        despesas_mes = Despesa.objects.filter(
            contrato=self.contrato,
            data_inicio__lte=self.data_vencimento  # Apenas despesas com início antes do vencimento
        )

        total = Decimal('0.00')
        for despesa in despesas_mes:
            # Verifica se a despesa é base para o repasse
            if not despesa.is_base_calculo_administracao:
                # Despesas que não são base de cálculo para a administração são somadas aqui
                valor_parcela = despesa.calcular_valor_parcela()
                percentual = despesa.percentual_repassado / Decimal('100.00')
                total += valor_parcela * percentual

        return total

    @property
    def valor_repassado(self):
        """
        Calcula o valor a ser repassado após subtrair a taxa de administração do valor do boleto.
        """
        valor_boleto = self.valor_boleto
        return valor_boleto - self.valor_administracao - self.total_despesas_repassadas

class IndiceInflacao(models.Model):
    tipo = models.CharField(max_length=50, verbose_name="Nome do Índice")
    valor = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor do Índice")
    data_referencia = models.DateField(verbose_name="Data de Referência")

    def __str__(self):
        return f"{self.tipo} - {self.data_referencia.strftime('%Y-%m')}"

class Despesa(models.Model):
    TIPO_DESPESA_CHOICES = [
        ('repasse', 'Repasse'),
        ('iptu', 'IPTU'),
        ('condominio', 'Condomínio'),
        ('manutencao', 'Manutenção'),
        ('outros', 'Outros'),
    ]
    PAGA_CHOICES = [
        ('proprietario', 'Proprietário'),
        ('inquilino', 'Inquilino'),
        ('imobiliaria', 'Imobiliária'),
    ]
    PERIODICIDADE_CHOICES = [
        ('mensal', 'Mensal'),
        ('trimestral', 'Trimestral'),
        ('semestral', 'Semestral'),
        ('anual', 'Anual'),
        ('unica', 'Única'),  # Para despesas avulsas
    ]

    contrato = models.ForeignKey(
        'Contrato',
        on_delete=models.CASCADE,
        related_name='despesas',
        verbose_name="Contrato"
    )
    tipo = models.CharField(
        max_length=20,
        choices=TIPO_DESPESA_CHOICES,
        verbose_name="Tipo de Despesa"
    )
    descricao = models.CharField(max_length=255, verbose_name="Descrição", null=True, blank=True)
    valor_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Valor Total"
    )
    paga = models.CharField(
        max_length=20,
        choices=PAGA_CHOICES,
        verbose_name="Quem paga?"
    )
    numero_parcelas = models.PositiveIntegerField(
        verbose_name="Número de Parcelas",
        default=1
    )
    periodicidade = models.CharField(
        max_length=20,
        choices=PERIODICIDADE_CHOICES,
        default='mensal',
        verbose_name="Periodicidade"
    )
    data_inicio = models.DateField(verbose_name="Data de Início")
    cobranca_referencia = models.CharField(
        max_length=20,
        verbose_name="Cobrança de Referência",
        help_text="Ex: 01/2023 para IPTU ou nome do condomínio",
        null=True,
        blank=True
    )
    percentual_repassado = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="Percentual repassado",
        default=100,
        help_text="Percentual da despesa que será repassado ao inquilino"
    )
    is_base_calculo_administracao = models.BooleanField(default=False, verbose_name="É base para cálculo da administração?")

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.descricao}"

    def calcular_valor_parcela(self):
        """Calcula o valor de cada parcela"""
        return self.valor_total / self.numero_parcelas if self.numero_parcelas else Decimal('0.00')

    def parcelas_pagas(self, data_referencia=None):
        """Retorna quantas parcelas já foram pagas até uma data específica"""
        if not data_referencia:
            data_referencia = date.today()

        meses_passados = (data_referencia.year - self.data_inicio.year) * 12 + (data_referencia.month - self.data_inicio.month)
        return min(meses_passados, self.numero_parcelas)

    def parcela_atual_ativa(self, data_referencia=None):
        """Verifica se a parcela para a data de referência ainda está ativa"""
        if not data_referencia:
            data_referencia = date.today()
        
        return self.parcelas_pagas(data_referencia) < self.numero_parcelas