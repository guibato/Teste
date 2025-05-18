# models/despesa.py
from django.db import models
from django.utils import timezone
from decimal import Decimal
from dateutil.relativedelta import relativedelta
from datetime import date


class TipoDespesa(models.Model):
    """
    Modelo para categorizar os tipos de despesas do sistema.
    Permite criar dinamicamente novos tipos de despesas.
    """
    nome = models.CharField(max_length=50, unique=True)
    descricao = models.TextField(null=True, blank=True)
    codigo = models.CharField(max_length=20, unique=True)
    icone = models.CharField(max_length=50, null=True, blank=True, 
                            help_text="Classe do ícone (ex: fa-home)")
    cor = models.CharField(max_length=20, null=True, blank=True,
                          help_text="Código de cor CSS (ex: #FF5733)")
    is_recorrente_padrao = models.BooleanField(
        default=False,
        verbose_name="É recorrente por padrão?",
        help_text="Indica se despesas deste tipo são recorrentes por padrão"
    )
    is_base_calculo_admin_padrao = models.BooleanField(
        default=False,
        verbose_name="Base para administração por padrão?",
        help_text="Indica se despesas deste tipo são base para cálculo da taxa de administração por padrão"
    )
    ordem_exibicao = models.PositiveSmallIntegerField(default=99)
    ativo = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Tipo de Despesa"
        verbose_name_plural = "Tipos de Despesas"
        ordering = ['ordem_exibicao', 'nome']
    
    def __str__(self):
        return self.nome


class Despesa(models.Model):
    """
    Modelo para gerenciar despesas associadas a um contrato.
    Possui mais informações sobre quem paga, periodicidade, e se é base para cálculo de administração.
    """
    PAGA_CHOICES = [
        ('proprietario', 'Proprietário'),
        ('inquilino', 'Inquilino'),
        ('imobiliaria', 'Imobiliária'),
    ]
    PERIODICIDADE_CHOICES = [
        ('mensal', 'Mensal'),
        ('bimestral', 'Bimestral'),
        ('trimestral', 'Trimestral'),
        ('semestral', 'Semestral'),
        ('anual', 'Anual'),
        ('unica', 'Única'),  # Para despesas avulsas
    ]

    # Relações com outros modelos
    contrato = models.ForeignKey(
        'sisimob.Contrato',  # Assumindo que Contrato está no app 'sisimob'
        on_delete=models.CASCADE,
        related_name='despesas',
        verbose_name="Contrato"
    )
    tipo = models.ForeignKey(
        TipoDespesa,
        on_delete=models.PROTECT,  # Protege contra exclusão acidental
        related_name='despesas',
        verbose_name="Tipo de Despesa"
    )
    
    # Campos de descrição
    descricao = models.CharField(
        max_length=255, 
        verbose_name="Descrição", 
        null=True, 
        blank=True
    )
    
    # Campos financeiros
    valor_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Valor Total"
    )
    paga = models.CharField(
        max_length=20,
        choices=PAGA_CHOICES,
        verbose_name="Responsável pelo Pagamento"
    )
    
    # Campos de parcelamento e periodicidade
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
    
    # Campos de datas
    data_inicio = models.DateField(verbose_name="Data de Início")
    data_fim_prevista = models.DateField(
        verbose_name="Data de Fim Prevista",
        null=True,
        blank=True
    )
    data_encerramento = models.DateField(
        verbose_name="Data de Encerramento",
        null=True,
        blank=True,
        help_text="Data em que a despesa foi encerrada (se aplicável)"
    )
    
    # Campos de referência
    cobranca_referencia = models.CharField(
        max_length=20,
        verbose_name="Cobrança de Referência",
        help_text="Ex: 01/2023 para IPTU ou nome do condomínio",
        null=True,
        blank=True
    )
    
    # Campos de repasse
    percentual_repassado = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="Percentual repassado",
        default=100,
        help_text="Percentual da despesa que será repassado ao inquilino"
    )
    
    # Configurações e flags
    is_base_calculo_administracao = models.BooleanField(
        default=False, 
        verbose_name="É base para cálculo da administração?",
        help_text="Se marcado, o valor desta despesa será incluído na base de cálculo da taxa de administração"
    )
    is_recorrente = models.BooleanField(
        default=False, 
        verbose_name="É despesa recorrente?",
        help_text="Marque para despesas que se repetem periodicamente como condomínio"
    )
    is_ativa = models.BooleanField(
        default=True,
        verbose_name="Está ativa?",
        help_text="Indica se a despesa está ativa para o contrato"
    )
    
    # Campos de auditoria
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    # Campos para despesas com documentos
    comprovante = models.FileField(
        upload_to='despesas/comprovantes/', 
        null=True, 
        blank=True,
        verbose_name="Comprovante"
    )
    observacoes = models.TextField(
        null=True, 
        blank=True,
        verbose_name="Observações"
    )

    class Meta:
        verbose_name = "Despesa"
        verbose_name_plural = "Despesas"
        ordering = ['-data_inicio', 'tipo']
        indexes = [
            models.Index(fields=['contrato', 'data_inicio']),
            models.Index(fields=['is_ativa', 'tipo']),
        ]

    def __str__(self):
        return f"{self.tipo.nome} - {self.descricao or self.get_descricao_padrao()}"
    
    def get_descricao_padrao(self):
        """Retorna uma descrição padrão caso não tenha sido definida"""
        if self.cobranca_referencia:
            return f"{self.tipo.nome} - {self.cobranca_referencia}"
        return f"{self.tipo.nome} - {self.data_inicio.strftime('%m/%Y')}"

    def calcular_valor_parcela(self):
        """Calcula o valor de cada parcela"""
        return self.valor_total / self.numero_parcelas if self.numero_parcelas else Decimal('0.00')

    def parcelas_pagas(self, data_referencia=None):
        """Retorna quantas parcelas já foram pagas até uma data específica"""
        if not data_referencia:
            data_referencia = date.today()

        meses_passados = self._calcular_meses_entre_datas(self.data_inicio, data_referencia)
        return min(meses_passados, self.numero_parcelas)
    
    def parcela_atual_ativa(self, data_referencia=None):
        """Verifica se a despesa tem parcela ativa na data de referência"""
        if not self.data_inicio or not self.numero_parcelas or not self.is_ativa:
            return False

        if not data_referencia:
            data_referencia = date.today()

        # Normaliza datas para o primeiro dia do mês
        data_inicio = date(self.data_inicio.year, self.data_inicio.month, 1)
        data_referencia = date(data_referencia.year, data_referencia.month, 1)
        
        # Calcula data fim com base na periodicidade
        meses_totais = self._calcular_total_meses()
        data_fim = self._adicionar_meses(data_inicio, meses_totais)

        return data_inicio <= data_referencia < data_fim
    
    def _calcular_total_meses(self):
        """Calcula o total de meses com base no número de parcelas e periodicidade"""
        meses_por_periodo = {
            'mensal': 1,
            'bimestral': 2,
            'trimestral': 3,
            'semestral': 6,
            'anual': 12,
            'unica': 1
        }
        return self.numero_parcelas * meses_por_periodo.get(self.periodicidade, 1)
    
    def _calcular_meses_entre_datas(self, data_inicio, data_fim):
        """Calcula a quantidade de meses entre duas datas, considerando a periodicidade"""
        meses_totais = (data_fim.year - data_inicio.year) * 12 + (data_fim.month - data_inicio.month)
        meses_por_periodo = {
            'mensal': 1,
            'bimestral': 2,
            'trimestral': 3,
            'semestral': 6,
            'anual': 12,
            'unica': 999  # Uma parcela única nunca terá mais que uma parcela
        }
        periodo = meses_por_periodo.get(self.periodicidade, 1)
        return meses_totais // periodo
    
    def _adicionar_meses(self, data, num_meses):
        """Adiciona um número de meses a uma data"""
        return date(
            data.year + ((data.month - 1 + num_meses) // 12),
            ((data.month - 1 + num_meses) % 12) + 1,
            1
        )
    
    def save(self, *args, **kwargs):
        """Sobrescreve o método save para aplicar regras de negócio na despesa"""
        # Calcula data fim prevista se não estiver definida
        if not self.data_fim_prevista and self.data_inicio and self.numero_parcelas:
            meses_totais = self._calcular_total_meses()
            self.data_fim_prevista = self._adicionar_meses(self.data_inicio, meses_totais)
        
        # Herda configurações do tipo de despesa, se não especificadas
        if self.tipo_id and self.pk is None:  # Só aplica na criação
            try:
                tipo = TipoDespesa.objects.get(pk=self.tipo_id)
                self.is_recorrente = getattr(self, 'is_recorrente', tipo.is_recorrente_padrao)
                self.is_base_calculo_administracao = getattr(self, 'is_base_calculo_administracao', 
                                                            tipo.is_base_calculo_admin_padrao)
            except TipoDespesa.DoesNotExist:
                pass
            
        super().save(*args, **kwargs)