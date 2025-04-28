from django.db import models
from django.utils import timezone
from decimal import Decimal
from dateutil.relativedelta import relativedelta
from sisimob.utils.integracao_asaas import cadastrar_cliente_no_asaas  # Certifique-se que esse caminho está correto
from django.conf import settings
from sisimob.utils.cobrancas_asaas import gerar_cobranca
from djmoney.models.fields import MoneyField
from djmoney.money import Money
from calendar import monthrange
from datetime import date
from django.db.models import Sum

class Cliente(models.Model):
    TIPO_CLIENTE_CHOICES = [
        ('Proprietario', 'Proprietário(a)'),
        ('Inquilino', 'Inquilino(a)'),
        ('Anuente', 'Anuente'),
        ('Fiador(a)', 'Fiador(a)'),
        ('Representante Legal', 'Representante Legal'),
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
    TIPO_PESSOA_CHOICES = [
    ('F', 'Pessoa Física'),
    ('J', 'Pessoa Jurídica'),
    ]

    tipo_pessoa = models.CharField(
        max_length=1,
        choices=TIPO_PESSOA_CHOICES,
        default='F',
        verbose_name='Tipo de Pessoa'
    )
    razao_social = models.CharField(max_length=255, null=True, blank=True, verbose_name="Razão Social")
    cnpj = models.CharField(max_length=18, null=True, blank=True, verbose_name="CNPJ")
    representante_legal = models.ForeignKey(
    'self',
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    limit_choices_to={
        'tipo_pessoa': 'F',
        'tipo': 'Representante Legal'
    },
    related_name="clientes_representados",
    verbose_name="Representante Legal"
)
    nome_fantasia = models.CharField(max_length=255, null=True, blank=True, verbose_name="Nome Fantasia")
    asaas_id = models.CharField(max_length=50, null=True, blank=True, verbose_name="ID Asaas")
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
        if self.tipo_pessoa == 'J' and self.razao_social:
            return self.razao_social
        return self.nome


    def clean(self):
        super().clean()
        if self.rg_rne and Cliente.objects.filter(rg_rne=self.rg_rne).exclude(pk=self.pk).exists():
            raise ValidationError({'rg_rne': 'Este RG/RNE já está cadastrado.'})
        
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)  # Salva o cliente no banco

        # Chama a API do Asaas para cadastrar o cliente
        resposta = cadastrar_cliente_no_asaas(self)

        if resposta:  # Garante que resposta não seja None
            self.asaas_id = resposta  # Agora estamos atribuindo corretamente o ID
        else:
            print(f"Erro ao cadastrar cliente {self.nome} no Asaas")

    @property
    def primeiro_nome(self):
        return self.nome.split()[0] if self.nome else ''
    
    
    @property
    def nome_exibicao(self):
        if self.tipo_pessoa == 'J':
            return self.nome_fantasia or self.razao_social or self.nome
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
    
    @property
    def endereco_resumido(self):
        partes = [self.endereco, self.numero]
        if self.bairro:
            partes.append(self.bairro)
        return ", ".join(partes)
    
    def endereco_completo(self):
        endereco_base = f"{self.endereco}, {self.numero}"
        if self.complemento:
            return f"{endereco_base} - {self.complemento}"
        return endereco_base

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
    TIPO_PAGAMENTO_CHOICES = [
        ('pacote', 'Pacote'),
        ('despesas_separadas', 'Despesas Separadas'),
    ]
    
    id = models.AutoField(primary_key=True)
    ativo = models.BooleanField(default=True, verbose_name="Ativo")
    clausula_12meses = models.BooleanField(default=False, verbose_name="Cláusula 12 Meses")
    tipo_contrato = models.CharField(max_length=20, choices=CONTRATO_CHOICES, null=True, blank=True, verbose_name="Tipo de Contrato")
    proprietario = models.ForeignKey('Cliente', on_delete=models.CASCADE, related_name="contratos_proprietario", verbose_name="Proprietário")
    inquilino = models.ForeignKey('Cliente', on_delete=models.CASCADE, related_name="contratos_inquilino", verbose_name="Inquilino")
    imovel = models.ForeignKey('Imovel', on_delete=models.CASCADE, related_name="contratos_imovel", verbose_name="Imóvel")
    data_inicio = models.DateField(verbose_name="Início")
    data_fim = models.DateField(verbose_name="Fim")
    carencia_dias = models.IntegerField(null=True, blank=True, default=0, verbose_name="Carência (dias)")
    fator_reajuste = models.CharField(max_length=5, choices=REAJUSTE_CHOICES, null=True, blank=True, verbose_name="Fator de Reajuste")
    multa_contratual = models.CharField(max_length=20, choices=MULTA_CHOICES, null=True, blank=True, verbose_name="Multa Contratual")
    tipo_pagamento = models.CharField(max_length=50, choices=TIPO_PAGAMENTO_CHOICES, default='despesas_separadas', verbose_name="Tipo de Aluguel")
    valor_aluguel = MoneyField(max_digits=10, decimal_places=2, null=True, blank=True, default_currency='BRL', default=Money(0, 'BRL'), verbose_name="Valor do Aluguel")
    valor_pacote = MoneyField(max_digits=10, decimal_places=2, null=True, blank=True, default_currency='BRL', default=Money(0, 'BRL'), verbose_name="Valor do Pacote")
    tipo_taxa = models.CharField(max_length=50, choices=TIPO_TAXA_CHOICES, null=True, blank=True, verbose_name="Tipo de Taxa")
    valor_taxa_administracao_percentual = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, default=0, verbose_name="Adm - %")
    valor_taxa_administracao_fixo = MoneyField(max_digits=10, decimal_places=2, null=True, blank=True, default_currency='BRL', default=Money(0, 'BRL'), verbose_name="Adm - R$")
    dia_pagamento = models.IntegerField(null=True, blank=True, verbose_name="Dia de Pagamento")
    garantia = models.CharField(max_length=50, choices=CAUCAO_CHOICES, null=True, blank=True, verbose_name="Garantia")
    fiador = models.ForeignKey('Cliente', on_delete=models.SET_NULL, null=True, blank=True, related_name="contratos_fiador", verbose_name="Fiador")
    valor_caucao = MoneyField(max_digits=10, decimal_places=2, null=True, blank=True, default_currency='BRL', default=Money(0, 'BRL'), verbose_name="Valor Caução")
    valor_segfi = MoneyField(max_digits=10, decimal_places=2, null=True, blank=True, default_currency='BRL', default=Money(0, 'BRL'), verbose_name="Valor Seguro Fiança")
    apolice_segfi = models.CharField(max_length=100, null=True, blank=True, verbose_name="Apólice Seguro Fiança")
    seg_segfi = models.CharField(max_length=100, null=True, blank=True, verbose_name="Seguradora Seguro Fiança")
    valor_cap = MoneyField(max_digits=10, decimal_places=2, null=True, blank=True, default_currency='BRL', default=Money(0, 'BRL'), verbose_name="Valor Capitalização")
    apolice_cap = models.CharField(max_length=100, null=True, blank=True, verbose_name="Apólice Capitalização")
    seg_cap = models.CharField(max_length=100, null=True, blank=True, verbose_name="Seguradora Capitalização")
    seguradora_incendio = models.CharField(max_length=100, null=True, blank=True, verbose_name="Seguradora Incêndio")
    apolice_incendio = models.CharField(max_length=50, null=True, blank=True, verbose_name="Apólice Incêndio")
    vencimento_seguro_incendio = models.DateField(null=True, blank=True, verbose_name="Vencimento do Seguro")
    documentos = models.FileField(upload_to='contratos/documentos/', null=True, blank=True, verbose_name="Documentos")
    historico_aluguel = models.JSONField(default=dict, blank=True, null=True, verbose_name="Histórico de Aluguel")

    def __str__(self):
        return f"Contrato {self.id} - {self.imovel.endereco}"

    def save(self, *args, **kwargs):
        try:
            if not isinstance(self.historico_aluguel, dict):
                self.historico_aluguel = {}
            data_inicio_str = str(self.data_inicio)
            if data_inicio_str not in self.historico_aluguel:
                if self.historico_aluguel:
                    ultima_data = sorted(self.historico_aluguel.keys())[-1]
                    valor_ultima_data = self.historico_aluguel.get(ultima_data, 0)
                    if isinstance(valor_ultima_data, Money):
                        valor_ultima_data = valor_ultima_data.amount
                    self.historico_aluguel[data_inicio_str] = float(valor_ultima_data)
                else:
                    valor_aluguel = self.valor_aluguel or Money(0, 'BRL')
                    self.historico_aluguel[data_inicio_str] = float(valor_aluguel.amount)
        except Exception as e:
            print("Erro ao salvar histórico de aluguel:", e)
            self.historico_aluguel = {}
        super().save(*args, **kwargs)

    def valor_taxa_administracao(self):
        aluguel = self.valor_aluguel or Money(0, 'BRL')
        if self.tipo_taxa == 'percentual':
            percentual = self.valor_taxa_administracao_percentual or Decimal('0')
            return aluguel * percentual / 100
        elif self.tipo_taxa == 'fixo':
            return self.valor_taxa_administracao_fixo or Money(0, 'BRL')
        return Money(0, 'BRL')

    @property
    def valor_repasse(self):
        if self.tipo_pagamento == 'despesas_separadas':
            aluguel = self.valor_aluguel or Money(0, 'BRL')
            taxa = self.valor_taxa_administracao()
            despesas_totais = sum((d.calcular_valor_parcela() for d in self.despesas.all()), Decimal('0.00'))
            total = aluguel - taxa + Money(despesas_totais, 'BRL')
            return max(total, Money(0, 'BRL'))
        return self.valor_pacote or Money(0, 'BRL')

    @property
    def taxa_administracao_display(self):
        if self.tipo_taxa == 'percentual':
            return f"{self.valor_taxa_administracao_percentual}%"
        elif self.tipo_taxa == 'fixo':
            return format_currency_br(self.valor_taxa_administracao_fixo)
        return "Isento"

    def valor_aluguel_com_reajuste(self, mes_ano):
        from .models import IndiceInflacao
        indices = IndiceInflacao.objects.filter(
            tipo=self.fator_reajuste,
            data_referencia__lte=mes_ano
        ).order_by('data_referencia')
        valor_reajustado = self.valor_aluguel or Money(0, 'BRL')
        for indice in indices:
            fator = Decimal(1) + (indice.valor / 100)
            valor_reajustado = valor_reajustado * fator  # Django Money permite multiplicação com Decimal
        return valor_reajustado

    def calcular_aluguel_projetado(self):
        from .models import IndiceInflacao
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
        valor_base = self.valor_aluguel if self.tipo_pagamento == 'despesas_separadas' else self.valor_pacote
        return (valor_base or 0) * fator_acumulado

    def calcular_valor_total(self):
        despesas_raw = self.despesas.aggregate(total=Sum('valor_total'))['total']
        despesas_total = Money(despesas_raw or 0, 'BRL')
        valor_aluguel = self.valor_aluguel or Money(0, 'BRL')
        if not isinstance(valor_aluguel, Money):
            valor_aluguel = Money(0, 'BRL')
        if not isinstance(despesas_total, Money):
            despesas_total = Money(0, 'BRL')
        return valor_aluguel + despesas_total

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
    valor = MoneyField(max_digits=10, decimal_places=2, default_currency='BRL', verbose_name="Valor")
    valor_administracao = MoneyField(max_digits=10, decimal_places=2, default_currency='BRL', verbose_name="Valor Administração")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pendente', verbose_name="Status do Pagamento")
    status_repasse = models.CharField(max_length=10, choices=STATUS_REPASSE_CHOICES, default='pendente', verbose_name="Status do Repasse")
    data_pagamento = models.DateField(null=True, blank=True, verbose_name="Data de Pagamento")
    data_repasse = models.DateField(null=True, blank=True, verbose_name="Data de Repasse")
    asaas_payment_id = models.CharField(max_length=100, null=True, blank=True)
    asaas_boleto_url = models.URLField(null=True, blank=True)
    asaas_pix_copia_cola = models.TextField(null=True, blank=True)
    asaas_pix_url = models.URLField(null=True, blank=True)
    asaas_codigo_barras = models.CharField(max_length=150, null=True, blank=True)
    inquilino = models.ForeignKey("Cliente", on_delete=models.SET_NULL, null=True, blank=True)
    descricao = models.TextField(null=True, blank=True)


    @property
    def valor_administracao(self):
        """Calcula o valor da taxa de administração baseado no valor do aluguel"""
        if not hasattr(self.contrato, 'tipo_taxa'):
            return Money(0, 'BRL')
        valor_aluguel = self.contrato.valor_aluguel  # Obter o valor do aluguel do contrato
        if self.contrato.tipo_taxa == 'percentual':
            percentual = self.contrato.valor_taxa_administracao_percentual or Decimal('0.00')
            return valor_aluguel * percentual / 100  # Cálculo da taxa de administração como percentual do aluguel
        elif self.contrato.tipo_taxa == 'fixo':
            return self.contrato.valor_taxa_administracao_fixo or Money(0, 'BRL')  # Taxa fixa
        return Money(0, 'BRL')

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
            if despesa.paga == 'inquilino':
                valor_parcela = despesa.calcular_valor_parcela()
                total += valor_parcela


        return total
    
    

    @property
    def despesas_mes_referencia(self):
        despesas = Despesa.objects.filter(
            contrato=self.contrato,
            data_inicio__lte=self.data_vencimento
        )
        despesas_referencia = []
        for despesa in despesas:
            if despesa.parcela_atual_ativa(self.data_vencimento):
                despesas_referencia.append(despesa)
        return despesas_referencia  

    @property
    def valor_liquido(self):
        """Calcula o valor líquido: Aluguel - Administração + Despesas Repasse - Despesas Deduzidas"""
        
        valor_despesas_repasses = sum(despesa.valor_total * (despesa.percentual_repassado / 100) 
                                      for despesa in self.contrato.despesas.filter(tipo='repasse'))
        
        valor_despesas_deduzidas = sum(despesa.valor_total for despesa in self.contrato.despesas.filter(tipo='outros'))
        
        # Calculando o valor líquido com MoneyField
        return self.valor - self.valor_administracao + valor_despesas_repasses - valor_despesas_deduzidas



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
    
    def save(self, *args, **kwargs):
        # Se a cobrança ainda não foi gerada no Asaas, cria ela
        if not self.asaas_payment_id and self.inquilino and self.inquilino.asaas_id:
            resposta = gerar_cobranca(self.inquilino.asaas_id, self.valor, self.data_vencimento, self.inquilino.nome)
            
            if "erro" not in resposta:
                self.asaas_payment_id = resposta["id"]
                self.asaas_boleto_url = resposta.get("bankSlipUrl")
                self.asaas_pix_copia_cola = resposta.get("pix", {}).get("payload")
                self.asaas_pix_url = resposta.get("pix", {}).get("qrCodeUrl")
                self.asaas_codigo_barras = resposta.get("identificationField")

        super().save(*args, **kwargs)  # Salva a cobrança no banco de dados

class IndiceInflacao(models.Model):
    tipo = models.CharField(max_length=50, verbose_name="Nome do Índice")
    valor = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor do Índice")
    data_referencia = models.DateField(verbose_name="Data de Referência")

    def __str__(self):
        return f"{self.tipo} - {self.data_referencia.strftime('%Y-%m')}"

class MovimentoConta(models.Model):
    TIPO_MOVIMENTO = (
        ('credito', 'Crédito'),
        ('debito', 'Débito'),
        ('repasse', 'Repasse Efetuado'),
    )

    proprietario = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    contrato = models.ForeignKey(Contrato, on_delete=models.SET_NULL, null=True, blank=True)
    tipo = models.CharField(max_length=10, choices=TIPO_MOVIMENTO)
    descricao = models.CharField(max_length=255)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    data = models.DateField(auto_now_add=True)
    data_referencia = models.DateField(null=True, blank=True)  # mês/ano do aluguel

    class Meta:
        ordering = ['data']

    def __str__(self):
        return f"{self.data} - {self.get_tipo_display()} - {self.valor} - {self.descricao}"
    
class LancamentoContaCorrente(models.Model):

    TIPOS = [
        ('credito', 'Crédito'),
        ('debito', 'Débito'),
        ('repasse', 'Repasse'),
    ]
    proprietario = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    data = models.DateField()
    tipo = models.CharField(max_length=10, choices=TIPOS)
    descricao = models.CharField(max_length=255)
    valor = models.DecimalField(max_digits=10, decimal_places=2)

class Reajuste(models.Model):
    contrato = models.ForeignKey('Contrato', on_delete=models.CASCADE, related_name='reajustes')
    data_reajuste = models.DateField()
    fator_calculado = models.DecimalField(max_digits=6, decimal_places=4)
    fator_aprovado = models.DecimalField(max_digits=6, decimal_places=4, null=True, blank=True)
    valor_calculado = models.DecimalField(max_digits=10, decimal_places=2)
    valor_aprovado = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    aprovado = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Reajuste {self.contrato} em {self.data_reajuste}"
    
    def aplicar_reajuste(self):
        if self.aprovado and self.valor_aprovado:
            self.contrato.valor_aluguel = self.valor_aprovado
            self.contrato.save()

    @staticmethod
    def calcular_fator(indices):
        acumulado = Decimal('1.00')
        for indice in indices:
            acumulado *= (Decimal('1.00') + (indice.valor / Decimal('100.00')))
        return max(acumulado, Decimal('1.00'))  # nunca menor que 1
    def clean(self):
        if self.aprovado and not self.valor_aprovado:
            raise ValidationError("Valor aprovado deve ser preenchido se o reajuste for aprovado.")

    def proximo_reajuste(contrato):
        ultimo_reajuste = contrato.reajustes.order_by('-data_reajuste').first()
        if ultimo_reajuste:
            return ultimo_reajuste.data_reajuste + relativedelta(years=1)
        return contrato.data_inicio + relativedelta(years=1)

class LembreteEnviado(models.Model):
    cobranca = models.ForeignKey('Cobranca', on_delete=models.CASCADE)
    dias_antecipacao = models.IntegerField()  # 10, 3 ou 0
    data_envio = models.DateField(auto_now_add=True)

    class Meta:
        unique_together = ('cobranca', 'dias_antecipacao')


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
        ('unica', 'Única'),
    ]

    contrato = models.ForeignKey('Contrato', on_delete=models.CASCADE, related_name='despesas')
    tipo = models.CharField(max_length=20, choices=TIPO_DESPESA_CHOICES)
    descricao = models.CharField(max_length=255, null=True, blank=True)
    valor_total = MoneyField(max_digits=10, decimal_places=2, default_currency='BRL')
    paga = models.CharField(max_length=20, choices=PAGA_CHOICES)
    numero_parcelas = models.PositiveIntegerField(null=True, blank=True)
    periodicidade = models.CharField(max_length=20, choices=PERIODICIDADE_CHOICES, default='mensal')
    data_inicio = models.DateField()
    cobranca_referencia = models.CharField(max_length=20, null=True, blank=True)
    percentual_repassado = models.DecimalField(max_digits=5, decimal_places=2, default=100)
    is_base_calculo_administracao = models.BooleanField(default=False)
    valor_por_parcela = models.BooleanField(default=False)
    despesa_recorrente = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.descricao}"

    def calcular_valor_parcela(self):
        if self.despesa_recorrente or self.valor_por_parcela:
            return self.valor_total
        return self.valor_total / self.numero_parcelas if self.numero_parcelas else Money('0.00', 'BRL')

    def parcelas_pagas(self, data_referencia=None):
        if not data_referencia:
            data_referencia = date.today()
        meses_passados = (data_referencia.year - self.data_inicio.year) * 12 + (data_referencia.month - self.data_inicio.month)
        return min(meses_passados, self.numero_parcelas or 0)

    def parcela_atual_ativa(self, data_referencia=None):
        if self.despesa_recorrente:
            return True
        if not data_referencia:
            data_referencia = date.today()
        return self.parcelas_pagas(data_referencia) < (self.numero_parcelas or 0)

    @property
    def descricao_com_parcela(self):
        if self.numero_parcelas and self.numero_parcelas > 1:
            return f"{self.descricao} ({self.parcelas_pagas() + 1}/{self.numero_parcelas})"
        return self.descricao
