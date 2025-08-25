from django.db import models
from django.utils import timezone
from decimal import Decimal
from dateutil.relativedelta import relativedelta
from datetime import date
from .base import TimestampedModel


class Contrato(TimestampedModel):
    """
    Modelo para contratos de locação
    """
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

    # Identificação e status
    id = models.AutoField(primary_key=True)
    ativo = models.BooleanField(default=True, verbose_name="Ativo")
    tipo = models.CharField(
        max_length=20, 
        choices=CONTRATO_CHOICES, 
        null=True, 
        blank=True, 
        verbose_name="Tipo"
    )
    clausula_12meses = models.BooleanField(
        default=False, 
        verbose_name="12 meses?"
    )
    tipo_contrato = models.CharField(
        max_length=20, 
        choices=CONTRATO_CHOICES, 
        null=True, 
        blank=True, 
        verbose_name="Tipo de Contrato"
    )

    # Relacionamentos - usando import lazy para evitar imports circulares
    proprietario = models.ManyToManyField(
        'cadastro.Cliente', 
        related_name="contratos_proprietario", 
        verbose_name="Proprietários"
    )
    inquilino = models.ManyToManyField(
        'cadastro.Cliente', 
        related_name="contratos_inquilino", 
        verbose_name="Inquilinos"
    )
    imovel = models.ForeignKey(
        'cadastro.Imovel', 
        on_delete=models.CASCADE, 
        related_name="contratos_imovel", 
        verbose_name="Imóvel"
    )
    fiador = models.ForeignKey(
        'cadastro.Cliente', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="contratos_fiador", 
        verbose_name="Fiador"
    )

    # Datas e períodos
    data_inicio = models.DateField(verbose_name="Início")
    data_fim = models.DateField(verbose_name="Fim")
    carencia_dias = models.IntegerField(
        verbose_name="Carência (dias)", 
        null=True, 
        blank=True, 
        default=0
    )

    # Reajustes e multas
    fator_reajuste = models.CharField(
        max_length=5, 
        choices=REAJUSTE_CHOICES, 
        verbose_name="Fator de Reajuste"
    )
    multa_contratual = models.CharField(
        max_length=20, 
        choices=MULTA_CHOICES, 
        verbose_name="Multa Contratual"
    )

    # Valores e pagamento
    tipo_pagamento = models.CharField(
        max_length=50,
        choices=TIPO_PAGAMENTO_CHOICES,
        verbose_name="Tipo de Aluguel",
        default='despesas_separadas'
    )
    valor_base = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name="Valor Base", 
        default=Decimal('0.00')
    )
    
    # Taxa de administração
    tipo_taxa = models.CharField(
        max_length=50, 
        choices=TIPO_TAXA_CHOICES, 
        verbose_name="Tipo de Taxa"
    )
    valor_taxa_administracao_percentual = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        verbose_name="Adm - %", 
        null=True, 
        blank=True, 
        default=Decimal('0.00')
    )
    valor_taxa_administracao_fixo = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name="Adm - R$", 
        null=True, 
        blank=True, 
        default=Decimal('0.00')
    )
    
    dia_pagamento = models.IntegerField(verbose_name="Dia de Pagamento")

    # Garantias
    garantia = models.CharField(
        max_length=50, 
        choices=CAUCAO_CHOICES, 
        verbose_name="Garantia"
    )
    valor_caucao = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name="Valor Caução", 
        null=True, 
        blank=True, 
        default=Decimal('0.00')
    )

    # Seguro
    seguradora = models.CharField(
        max_length=100, 
        verbose_name="Seguradora", 
        null=True, 
        blank=True
    )
    apolice = models.CharField(
        max_length=50, 
        verbose_name="Apólice", 
        null=True, 
        blank=True
    )
    valor_seguro_incendio = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name="Valor do Seguro", 
        null=True, 
        blank=True, 
        default=Decimal('0.00')
    )
    vencimento_seguro_incendio = models.DateField(
        verbose_name="Vencimento do Seguro", 
        null=True, 
        blank=True
    )

    # Documentos e histórico
    documentos = models.FileField(
        upload_to='contratos/documentos/', 
        null=True, 
        blank=True, 
        verbose_name="Documentos"
    )
    historico_aluguel = models.JSONField(
        default=dict, 
        blank=True, 
        verbose_name="Histórico de Valores"
    )

    class Meta:
        ordering = ['-ativo', 'dia_pagamento', '-data_inicio']
        verbose_name = "Contrato"
        verbose_name_plural = "Contratos"

    def __str__(self):
        endereco = self.imovel.endereco or ''
        numero = self.imovel.numero or ''
        complemento = f" - {self.imovel.complemento}" if self.imovel.complemento else ''
        
        # Obter proprietários (ManyToMany)
        proprietarios = self.proprietario.all()
        if proprietarios.exists():
            nomes_proprietarios = ", ".join([p.nome for p in proprietarios])
            return f"#{self.id} - {nomes_proprietarios} - {endereco}, {numero}{complemento}"
        else:
            return f"#{self.id} - Sem proprietário - {endereco}, {numero}{complemento}"

    def get_display_name(self):
        """Método específico para exibição em dropdowns"""
        endereco = self.imovel.endereco or ''
        numero = self.imovel.numero or ''
        
        # Para evitar N+1 queries, usar prefetch_related na view
        proprietarios = self.proprietario.all()
        if proprietarios:
            nomes = ", ".join([p.nome for p in proprietarios])
            return f"#{self.id} - {nomes} - {endereco}, {numero}"
        else:
            return f"#{self.id} - {endereco}, {numero}"

    def valor_taxa_administracao(self):
        """Calcula o valor da taxa de administração"""
        if self.tipo_taxa == 'percentual':
            return (self.valor_base * self.valor_taxa_administracao_percentual) / 100
        elif self.tipo_taxa == 'fixo':
            return self.valor_taxa_administracao_fixo
        return Decimal('0.00')

    @property
    def taxa_administracao_display(self):
        """Retorna a representação textual da taxa para exibição"""
        if self.tipo_taxa == 'percentual':
            return f"{self.valor_taxa_administracao_percentual}%"
        elif self.tipo_taxa == 'fixo':
            return f"R$ {self.valor_taxa_administracao_fixo}"
        return "Isento"

    def valor_aluguel_com_reajuste(self, mes_ano):
        """
        Calcula o valor do aluguel reajustado com base no índice de inflação (ex.: IPCA).
        """
        from django.apps import apps
        IndiceInflacao = apps.get_model('financeiro', 'IndiceInflacao')
        
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
        from django.apps import apps
        IndiceInflacao = apps.get_model('financeiro', 'IndiceInflacao')
        
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
        """Calcula o valor de repasse para o proprietário"""
        if self.tipo_pagamento == 'despesas_separadas':
            taxa_adm = self.valor_taxa_administracao()
            # Removido referência a despesas já que não existe mais
            return max(self.valor_base - taxa_adm, Decimal('0.00'))
        return self.valor_base  # pacote

    def calcular_valor_total(self):
        """Calcula o valor total do contrato incluindo despesas"""
        if self.tipo_pagamento == 'despesas_separadas':
            # Removido referência a despesas já que não existe mais
            return self.valor_base
        return self.valor_base

    def save(self, *args, **kwargs):
        """Override do save para manter histórico de valores"""
        if not self.historico_aluguel or str(self.data_inicio) not in self.historico_aluguel:
            ultimo_valor = list(self.historico_aluguel.values())[-1] if self.historico_aluguel else self.valor_base
            self.historico_aluguel[str(self.data_inicio)] = float(ultimo_valor)
        super().save(*args, **kwargs)

    def valor_aluguel_atual(self, referencia: date = None):
        """
        Retorna o valor atual do aluguel considerando reajustes.
        Se não houver reajustes, retorna o valor_base.
        """
        if referencia is None:
            referencia = date.today()
        
        # Buscar o último reajuste até a data de referência
        # Removido referência a reajustes já que não existe mais
        
        # Se não há reajustes, retorna o valor base
        return self.valor_base

    def get_data_vencimento(self, mes: int, ano: int):
        """
        Retorna a data de vencimento da cobrança com base no dia_pagamento do contrato.
        Garante que a data gerada seja válida (não ultrapassa o fim do mês).
        """
        import calendar
        
        ultimo_dia = calendar.monthrange(ano, mes)[1]
        dia = min(self.dia_pagamento, ultimo_dia)
        return date(ano, mes, dia)

    def esta_elegivel_para_reajuste(self, referencia=None):
        """Verifica se o contrato está elegível para reajuste"""
        if not referencia:
            referencia = date.today()

        data_base = self.data_inicio.replace(day=1)
        # Removido referência a reajustes já que não existe mais

        data_proximo_reajuste = data_base + relativedelta(months=12)
        data_referencia = referencia.replace(day=1)

        return data_referencia >= data_proximo_reajuste

    @property 
    def valor_aluguel(self):
        """
        Propriedade para manter compatibilidade com código antigo.
        Retorna o valor atual do aluguel.
        """
        return self.valor_aluguel_atual()

    @property
    def valor_pacote(self):
        """Alias para valor_base quando tipo_pagamento é pacote"""
        if self.tipo_pagamento == 'pacote':
            return self.valor_base
        return Decimal('0.00')

    @property
    def esta_ativo(self):
        """Verifica se o contrato está ativo baseado nas datas"""
        hoje = date.today()
        return self.ativo and self.data_inicio <= hoje <= self.data_fim

    @property
    def dias_restantes(self):
        """Calcula quantos dias restam até o fim do contrato"""
        hoje = date.today()
        if hoje <= self.data_fim:
            return (self.data_fim - hoje).days
        return 0

    @property
    def status_vencimento(self):
        """Retorna status baseado na proximidade do vencimento"""
        dias = self.dias_restantes
        if dias <= 0:
            return 'vencido'
        elif dias <= 30:
            return 'proximo_vencimento'
        elif dias <= 90:
            return 'atencao'
        else:
            return 'normal'.data_reajuste.replace(day=1)

        data_proximo_reajuste = data_base + relativedelta(months=12)
        data_referencia = referencia.replace(day=1)

        return data_referencia >= data_proximo_reajuste

    @property 
    def valor_aluguel(self):
        """
        Propriedade para manter compatibilidade com código antigo.
        Retorna o valor atual do aluguel.
        """
        return self.valor_aluguel_atual()

    @property
    def valor_pacote(self):
        """Alias para valor_base quando tipo_pagamento é pacote"""
        if self.tipo_pagamento == 'pacote':
            return self.valor_base
        return Decimal('0.00')

    @property
    def esta_ativo(self):
        """Verifica se o contrato está ativo baseado nas datas"""
        hoje = date.today()
        return self.ativo and self.data_inicio <= hoje <= self.data_fim

    @property
    def dias_restantes(self):
        """Calcula quantos dias restam até o fim do contrato"""
        hoje = date.today()
        if hoje <= self.data_fim:
            return (self.data_fim - hoje).days
        return 0

    @property
    def status_vencimento(self):
        """Retorna status baseado na proximidade do vencimento"""
        dias = self.dias_restantes
        if dias <= 0:
            return 'vencido'
        elif dias <= 30:
            return 'proximo_vencimento'
        elif dias <= 90:
            return 'atencao'
        else:
            return 'normal'