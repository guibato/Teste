from django.db import models
from decimal import Decimal
from datetime import datetime
from dateutil.relativedelta import relativedelta
from .rent_calculations import calcular_aluguel_projetado
from decimal import Decimal
from bson.decimal128 import Decimal128
import logging
from pymongo import MongoClient
from django.conf import settings
from dateutil.relativedelta import relativedelta

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
    ('Proprietario', 'Proprietário(a)'),
    ('Inquilino', 'Inquilino(a)'),
    ('Anuente', 'Anuente'),
    ('Fiador', 'Fiador(a)'),
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

    tipo_pagamento_CHOICES = [
        ('Despesas_Separadas', 'Despesas Separadas'),
        ('Pacote', 'Pacote'),
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

    # Campos básicos
    tipo = models.CharField(max_length=20, choices=TIPO_CLIENTE_CHOICES, verbose_name="Tipo", null=True, blank=True)
    ativo = models.BooleanField(default=True, verbose_name="Ativo?")
    tipo_contrato = models.CharField(max_length=20, choices=CONTRATO_CHOICES, blank=True, null=True)
    proprietario = models.ForeignKey(Cliente,on_delete=models.CASCADE,related_name='contratos_proprietario', limit_choices_to={'tipo': 'Proprietário(a)'}, verbose_name="Proprietário")
    inquilino = models.ForeignKey(Cliente,on_delete=models.CASCADE,related_name='contratos_inquilino',limit_choices_to={'tipo': 'Inquilino'}, verbose_name="Inquilino")
    imovel = models.ForeignKey(Imovel,on_delete=models.CASCADE,related_name='contratos_imovel',verbose_name="Imóvel")
    

    # Datas e condições
    data_inicio = models.DateField(verbose_name="Início")
    data_fim = models.DateField(verbose_name="Final")
    carencia_dias = models.IntegerField(verbose_name="Carência", null=True, blank=True, default=0)
    fator_reajuste = models.CharField(max_length=5, choices=REAJUSTE_CHOICES, verbose_name="Reajuste")
    multa_contratual = models.CharField(max_length=20, choices=MULTA_CHOICES, verbose_name="Multa Contratual")

    # Valores e pagamentos
    tipo_pagamento = models.CharField(max_length=50,choices=tipo_pagamento_CHOICES, verbose_name="Tipo de Aluguel")
    valor_aluguel = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor do Aluguel", null=True, blank=True, default=0.00)
    valor_pacote = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor do Pacote", null=True, blank=True, default=0.00)
    valor_condominio = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Condomínio", null=True, blank=True, default=0.00)
    valor_iptu = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="IPTU", null=True, blank=True, default=0.00)
    valor_outros = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Outros", null=True, blank=True, default=0.00)

    # Taxas
    tipo_taxa = models.CharField(
        max_length=50,
        choices=TIPO_TAXA_CHOICES,
        verbose_name="Tipo de Taxa"
    )
    valor_taxa_administracao_percentual = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Adm - %",
        null=True,
        blank=True,
        default=0.00
    )
    valor_taxa_administracao_fixo = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Adm - R$",
        null=True,
        blank=True,
        default=0.00
    )

    dia_pagamento = models.IntegerField(verbose_name="Dia de Pagamento")

    # Garantias
    garantia = models.CharField(max_length=50, choices=CAUCAO_CHOICES, verbose_name="Garantia")
    fiador = models.CharField(max_length=100, verbose_name="Fiador", null=True, blank=True)
    valor_caucao = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor Caução", null=True, blank=True, default=0.00)
    valor_segfi = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor Fiança", null=True, blank=True, default=0.00)
    apolice_segfi = models.CharField(max_length=50, verbose_name="Apólice Fiança", null=True, blank=True)
    seg_segfi = models.CharField(max_length=100, verbose_name="Seguradora Fiança", null=True, blank=True)
    valor_cap = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor Capitalização", null=True, blank=True, default=0.00)
    apolice_cap = models.CharField(max_length=50, verbose_name="Apólice Capitalização", null=True, blank=True)
    seg_cap = models.CharField(max_length=100, verbose_name="Seguradora Capitalização", null=True, blank=True)

    # Cláusulas
    clausula_12meses = models.BooleanField(default=False, verbose_name="Cláusula de 12 Meses?")

    # Seguro contra incêndio
    seguradora_incendio = models.CharField(max_length=100, verbose_name="Seguradora", null=True, blank=True)
    apolice_incendio = models.CharField(max_length=50, verbose_name="Apólice", null=True, blank=True)
    valor_seguro = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor do Seguro", null=True, blank=True, default=0.00)
    vencimento_seguro = models.DateField(verbose_name="Vencimento do Seguro", null=True, blank=True)

    # Documentos
    documentos = models.FileField(upload_to='documentos/', verbose_name="Documentos", null=True, blank=True)

    def __str__(self):
        return f"Contrato {self.tipo_contrato} - {self.imovel}"
    
    @property
    def aluguel_projetado(self):
    
        logger = logging.getLogger(__name__)
        
        # Get base value
        if hasattr(self, 'tipo_pagamento') and self.tipo_pagamento == 'Despesas_Separadas':
            base_value = self.valor_aluguel
        else:
            base_value = getattr(self, 'valor_pacote', Decimal('0.00'))
        
        # Convert Decimal128 to Decimal if needed
        if isinstance(base_value, Decimal128):
            base_value = Decimal(str(base_value))
        
        # Define calculation period
        data_inicio = self.data_inicio
        data_fim_projecao = data_inicio + relativedelta(months=12)
        
        logger.info(f"Calculating projected rent for contract ID: {self.id}")
        logger.info(f"Base value: {base_value}")
        logger.info(f"Period: {data_inicio} to {data_fim_projecao}")
        
        try:
            # Connect to MongoDB
            mongo_uri = getattr(settings, 'MONGO_URI', 'mongodb://localhost:27017/')
            mongo_db_name = getattr(settings, 'MONGO_DB_NAME', 'Palestra')
            
            mongo_client = MongoClient(mongo_uri)
            db = mongo_client[mongo_db_name]
            colecao_indices = db.sisimob_indiceinflacao
            
            # Get all IPCA indices
            indices_periodo = list(colecao_indices.find({'tipo': self.fator_reajuste}))
            logger.info(f"Found {len(indices_periodo)} IPCA indices")
            
            # No indices found
            if not indices_periodo:
                logger.warning("No indices found. Using simple 10% projection.")
                return base_value * Decimal('1.10')
            
            # Organize indices by year and month
            indices_por_mes = {}
            for indice in indices_periodo:
                if 'ano' in indice and 'mes' in indice:
                    ano_mes = (indice['ano'], indice['mes'])
                    
                    if 'valor' in indice:
                        # Handle different formats
                        if isinstance(indice['valor'], dict) and '$numberDecimal' in indice['valor']:
                            # MongoDB extended JSON format
                            raw_value = indice['valor']['$numberDecimal']
                        elif isinstance(indice['valor'], Decimal128):
                            # MongoDB Decimal128
                            raw_value = str(indice['valor'])
                        else:
                            # Other formats
                            raw_value = str(indice['valor'])
                        
                        # Convert to Decimal
                        try:
                            indices_por_mes[ano_mes] = Decimal(raw_value)
                            logger.info(f"Index for {ano_mes}: {indices_por_mes[ano_mes]}")
                        except:
                            logger.warning(f"Could not convert value: {raw_value}")
            
            # Calculate projected value
            valor_projetado = base_value
            data_atual = data_inicio
            
            while data_atual < data_fim_projecao:
                ano_mes = (data_atual.year, data_atual.month)
                if ano_mes in indices_por_mes:
                    indice = indices_por_mes[ano_mes] / Decimal('100')
                    logger.info(f"Applying index for {ano_mes}: {indice}")
                    
                    # Apply index
                    valor_anterior = valor_projetado
                    valor_projetado *= (Decimal('1') + indice)

                    
                    logger.info(f"Value before: {valor_anterior}, after: {valor_projetado}")
                
                # Move to next month
                data_atual += relativedelta(months=1)
            
            # Round to 2 decimal places
            return valor_projetado.quantize(Decimal('0.01'))
        
        except Exception as e:
            # Log error and use simple calculation
            logger.error(f"Error calculating projected rent: {e}", exc_info=True)
            return base_value * Decimal('1.10')
    
class Cobranca(models.Model):
    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente'),
        ('PAGO', 'Pago'),
        ('ATRASADO', 'Atrasado'),
    ]
    
    REPASSE_CHOICES = [
        ('PENDENTE', 'Pendente'),
        ('REPASSADO', 'Repassado'),
    ]
    
    contrato = models.ForeignKey('Contrato', on_delete=models.CASCADE)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2)
    data_vencimento = models.DateField()
    status_pagamento = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDENTE')
    status_repasse = models.CharField(max_length=20, choices=REPASSE_CHOICES, default='PENDENTE')
    data_geracao = models.DateTimeField(auto_now_add=True)
    numero_referencia = models.CharField(max_length=20)  # Para armazenar "seu número"
    
    class Meta:
        unique_together = ['contrato', 'data_vencimento']
        
    def __str__(self):
        return f"{self.contrato} - {self.data_vencimento}"

class IndiceInflacao(models.Model):
    
    TIPO_INDICE_CHOICES = [
        ('IPCA', 'IPC-A'),
        ('IGPM', 'IGP-M'),
    ]

    tipo = models.CharField(max_length=10, choices=TIPO_INDICE_CHOICES, verbose_name="Tipo de Índice")
    ano = models.IntegerField(verbose_name="Ano")
    mes = models.IntegerField(verbose_name="Mês")
    valor = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor (%)")

    class Meta:
        unique_together = ['tipo', 'ano', 'mes']  # Garante que não haja duplicatas para o mesmo mês/ano/tipo

    def __str__(self):
        return f"{self.tipo} - {self.ano}/{self.mes}: {self.valor}%"