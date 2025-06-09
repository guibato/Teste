# financeiro/models/cobranca.py
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from decimal import Decimal
from django.apps import apps
import datetime


class Cobranca(models.Model):
    """
    Modelo para cobrança de aluguel e outras despesas.
    Redesenhado para maior clareza, flexibilidade e robustez.
    """
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('paga', 'Recebida'),
        ('atrasada', 'Atrasada'),
        ('cancelada', 'Cancelada'),
    ]

    # === RELACIONAMENTOS PRINCIPAIS ===
    contrato = models.ForeignKey(
        'sisimob.Contrato', 
        on_delete=models.CASCADE, 
        related_name='cobrancas_financeiro',
        help_text="Contrato ao qual esta cobrança se refere"
    )
    # REMOVIDO: inquilino (agora é property através do contrato)

    # === DADOS DE REFERÊNCIA ===
    mes_referencia = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        help_text="Mês ao qual se refere esta cobrança"
    )
    ano_referencia = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(2020), MaxValueValidator(2030)],
        help_text="Ano de referência da cobrança"
    )
    descricao = models.TextField(
        blank=True, 
        null=True,
        help_text="Descrição detalhada da cobrança"
    )

    # === VALORES ===
    valor_aluguel = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Valor base do aluguel"
    )
    valor_despesas = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Valor total das despesas incluídas"
    )
    valor_total = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        help_text="Valor total da cobrança (aluguel + despesas)"
    )

    # === DATAS ===
    data_vencimento = models.DateField(
        help_text="Data limite para pagamento"
    )
    data_emissao = models.DateField(
        auto_now_add=True,
        help_text="Data de criação da cobrança"
    )
    data_pagamento = models.DateField(
        null=True, 
        blank=True,
        help_text="Data em que o pagamento foi recebido"
    )
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    # === STATUS ===
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pendente'
    )
    status_detalhes = models.JSONField(
        default=dict, 
        blank=True,
        help_text="Detalhes adicionais sobre o status"
    )

    # === CONTROLE DE LEMBRETES ===
    lembrete_10_enviado = models.BooleanField(default=False)
    lembrete_3_enviado = models.BooleanField(default=False)
    lembrete_0_enviado = models.BooleanField(default=False)

    # === CAMPOS ADICIONAIS ===
    observacoes = models.TextField(
        blank=True, 
        null=True, 
        help_text="Observações internas"
    )
    
    class Meta:
        verbose_name = "Cobrança"
        verbose_name_plural = "Cobranças"
        ordering = ['-data_vencimento', '-ano_referencia', '-mes_referencia']
        unique_together = [('contrato', 'mes_referencia', 'ano_referencia')]
        
        indexes = [
            # Consultas mais comuns
            models.Index(fields=['status', 'data_vencimento'], name='idx_status_vencimento'),
            models.Index(fields=['contrato', 'mes_referencia', 'ano_referencia'], name='idx_contrato_periodo'),
            
            # Relatórios e dashboards
            models.Index(fields=['ano_referencia', 'mes_referencia'], name='idx_periodo'),
            models.Index(fields=['data_emissao'], name='idx_data_emissao'),
            models.Index(fields=['data_pagamento'], name='idx_data_pagamento'),
            
            # Status e controle
            models.Index(fields=['status'], name='idx_status'),
        ]
        
        constraints = [
            # Validações a nível de banco
            models.CheckConstraint(
                check=models.Q(valor_aluguel__gt=0),
                name='valor_aluguel_positivo'
            ),
            models.CheckConstraint(
                check=models.Q(valor_total__gte=models.F('valor_aluguel')),
                name='valor_total_maior_igual_aluguel'
            ),
            models.CheckConstraint(
                check=models.Q(valor_despesas__gte=0),
                name='valor_despesas_nao_negativo'
            ),
            models.CheckConstraint(
                check=models.Q(mes_referencia__gte=1, mes_referencia__lte=12),
                name='mes_referencia_valido'
            ),
        ]

    # === PROPERTIES ===
    @property
    def inquilino(self):
        """Acessa inquilino através do contrato"""
        if self.contrato and hasattr(self.contrato, 'inquilino'):
            # Suporte para relacionamento ManyToMany ou ForeignKey
            if hasattr(self.contrato.inquilino, 'all'):
                return self.contrato.inquilino.first()
            return self.contrato.inquilino
        return None

    @property
    def esta_atrasada(self):
        """Verifica se a cobrança está atrasada"""
        return (
            self.status in ['pendente', 'atrasada'] and 
            self.data_vencimento < timezone.now().date()
        )

    @property
    def dias_atraso(self):
        """Calcula dias de atraso"""
        if self.esta_atrasada:
            return (timezone.now().date() - self.data_vencimento).days
        return 0

    @property
    def data_referencia_texto(self):
        """Retorna período em formato legível"""
        meses = {
            1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
            5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
            9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
        }
        mes_nome = meses.get(self.mes_referencia, f'Mês {self.mes_referencia}')
        return f"{mes_nome} de {self.ano_referencia}"

    @property
    def is_quitada(self):
        """Verifica se a cobrança está quitada"""
        return self.status == 'paga' and self.data_pagamento is not None

    # === VALIDAÇÕES ===
    def clean(self):
        """Validações customizadas do modelo"""
        super().clean()
        
        errors = {}
        
        # Validar período de referência
        if self.mes_referencia and self.ano_referencia:
            try:
                data_referencia = datetime.date(self.ano_referencia, self.mes_referencia, 1)
                data_limite_passado = datetime.date(2020, 1, 1)
                data_limite_futuro = datetime.date(2030, 12, 31)
                
                if data_referencia < data_limite_passado:
                    errors['ano_referencia'] = 'Data de referência muito antiga'
                elif data_referencia > data_limite_futuro:
                    errors['ano_referencia'] = 'Data de referência muito distante'
                    
            except ValueError:
                errors['mes_referencia'] = 'Combinação mês/ano inválida'
        
        # Validar valores
        if self.valor_aluguel is not None and self.valor_aluguel <= 0:
            errors['valor_aluguel'] = 'Valor do aluguel deve ser positivo'
            
        if self.valor_despesas is not None and self.valor_despesas < 0:
            errors['valor_despesas'] = 'Valor das despesas não pode ser negativo'
            
        if (self.valor_aluguel and self.valor_despesas and self.valor_total and
            self.valor_total < (self.valor_aluguel + self.valor_despesas)):
            errors['valor_total'] = 'Valor total deve ser pelo menos a soma do aluguel e despesas'
        
        # Validar datas
        if self.data_vencimento and self.data_emissao:
            if self.data_vencimento < self.data_emissao:
                errors['data_vencimento'] = 'Data de vencimento não pode ser anterior à emissão'
        
        if self.data_pagamento and self.data_emissao:
            if self.data_pagamento < self.data_emissao:
                errors['data_pagamento'] = 'Data de pagamento não pode ser anterior à emissão'
        
        # Validar status vs datas
        if self.status == 'paga' and not self.data_pagamento:
            errors['data_pagamento'] = 'Data de pagamento é obrigatória para cobranças pagas'
            
        if self.data_pagamento and self.status not in ['paga']:
            errors['status'] = 'Status deve ser "paga" quando há data de pagamento'
        
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        """Save simplificado - apenas validações essenciais"""
        # Executar validações
        self.full_clean()
        
        # Atualizar status automático baseado na data (só se ainda não foi definido manualmente)
        if self.status == 'pendente' and self.data_vencimento < timezone.now().date():
            self.status = 'atrasada'
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Cobrança {self.mes_referencia}/{self.ano_referencia} - {self.contrato}"

    # === MÉTODOS DE CÁLCULO (usando services) ===
    def calcular_valor_administracao(self):
        """Calcula valor da taxa de administração"""
        from financeiro.services.cobranca.cobranca_calculadora_service import CobrancaCalculadoraService
        return CobrancaCalculadoraService.calcular_taxa_administracao(self.contrato, self.valor_aluguel)

    def get_despesas_cobranca(self):
        """Retorna despesas ativas para esta cobrança"""
        from financeiro.services.cobranca.cobranca_calculadora_service import CobrancaCalculadoraService
        return CobrancaCalculadoraService.buscar_despesas_periodo(
            self.contrato, self.mes_referencia, self.ano_referencia
        )

    def calcular_valor_total(self):
        """Calcula valor total incluindo despesas"""
        from financeiro.services.cobranca.cobranca_calculadora_service import CobrancaCalculadoraService
        return CobrancaCalculadoraService.calcular_valor_total(
            self.valor_aluguel, 
            self.get_despesas_cobranca()
        )

    def atualizar_valor_total(self):
        """Atualiza o valor total da cobrança"""
        despesas = self.get_despesas_cobranca()
        self.valor_despesas = sum(d.calcular_valor_parcela() for d in despesas)
        self.valor_total = self.valor_aluguel + self.valor_despesas
        self.save(update_fields=['valor_despesas', 'valor_total'])

    def gerar_descricao_automatica(self):
        """Gera descrição automática baseada nas despesas"""
        from ..services.cobranca_descricao_service import CobrancaDescricaoService
        return CobrancaDescricaoService.gerar_descricao_completa(self)

    def get_detalhes_financeiros(self):
        """Retorna detalhamento financeiro da cobrança"""
        despesas = self.get_despesas_cobranca()
        
        return {
            "valor_aluguel": self.valor_aluguel,
            "valor_despesas": self.valor_despesas,
            "valor_total": self.valor_total,
            "taxa_administracao": self.calcular_valor_administracao(),
            "valor_repasse": self.calcular_valor_repasse(),
            "despesas_detalhadas": [
                {
                    'nome': d.nome if hasattr(d, 'nome') else str(d.tipo),
                    'valor': d.calcular_valor_parcela(),
                    'tipo': d.tipo.nome if hasattr(d, 'tipo') else 'Despesa'
                } for d in despesas
            ]
        }

    def get_descricao_formatada(self):
        """Retorna descrição formatada para WhatsApp"""
        if not self.descricao:
            return ""
            
        linhas = self.descricao.strip().split('\n') if self.descricao else []
        return '\n'.join([linha.strip() for linha in linhas if linha.strip()])

    # === MÉTODOS DE AÇÃO ===
    def marcar_como_paga(self, data_pagamento=None):
        """Marca cobrança como paga e cria repasse"""
        if self.status == 'paga':
            return
            
        if not data_pagamento:
            data_pagamento = timezone.now().date()
            
        self.status = 'paga'
        self.data_pagamento = data_pagamento
        self.save(update_fields=['status', 'data_pagamento'])

        # Criar repasse automaticamente
        self._criar_repasse_automatico()

    def _criar_repasse_automatico(self):
        """Cria repasse automático para o proprietário"""
        try:
            Repasse = apps.get_model('financeiro', 'Repasse')
            Repasse.objects.get_or_create(
                cobranca=self,
                defaults={
                    'valor': self.calcular_valor_repasse(),
                    'status': 'pendente'
                }
            )
        except LookupError:
            # Modelo Repasse não existe ainda
            pass

    def calcular_valor_repasse(self):
        """Calcula valor do repasse para o proprietário"""
        from financeiro.services.cobranca.cobranca_calculadora_service import CobrancaCalculadoraService
        return CobrancaCalculadoraService.calcular_valor_repasse(self)

    def cancelar(self, motivo=None):
        """Cancela a cobrança"""
        if self.status == 'paga':
            raise ValidationError("Não é possível cancelar uma cobrança já paga")
            
        self.status = 'cancelada'
        if motivo:
            self.status_detalhes['motivo_cancelamento'] = motivo
            self.status_detalhes['data_cancelamento'] = timezone.now().isoformat()
        
        self.save(update_fields=['status', 'status_detalhes'])

    @property
    def valor_repasse_proprietario(self):
        """Retorna o valor a ser repassado para o proprietário"""
        return self.calcular_valor_repasse()

    # === PROPERTIES PARA CÁLCULOS FINANCEIROS ===
    @property
    def valor_administracao(self):
        """Retorna o valor da taxa de administração"""
        try:
            return self.calcular_valor_administracao()
        except Exception:
            return Decimal('0.00')

    @property
    def valor_liquido(self):
        """
        Calcula o valor líquido do repasse para o proprietário
        Fórmula: valor_total - taxa_administracao
        """
        try:
            taxa_admin = self.calcular_valor_administracao()
            return self.valor_total - taxa_admin
        except Exception:
            return self.valor_total

    @property
    def percentual_administracao(self):
        """Retorna o percentual da taxa de administração"""
        if self.valor_total > 0:
            return (self.valor_administracao / self.valor_total) * 100
        return Decimal('0.00')


# === MODELO SEPARADO PARA INTEGRAÇÃO ASAAS ===
class AsaasIntegracao(models.Model):
    """
    Modelo separado para dados de integração com Asaas
    Segue o princípio de responsabilidade única
    """
    cobranca = models.OneToOneField(
        Cobranca, 
        on_delete=models.CASCADE, 
        related_name='asaas_integracao'
    )
    
    # IDs e status do Asaas
    asaas_id = models.CharField(
        max_length=100, 
        unique=True,
        help_text="ID da cobrança no Asaas"
    )
    gateway_status = models.CharField(
        max_length=30, 
        blank=True, 
        null=True,
        help_text="Status retornado pelo Asaas"
    )
    
    # URLs e dados de pagamento
    boleto_url = models.URLField(blank=True, null=True)
    pix_copia_cola = models.TextField(blank=True, null=True)
    pix_qrcode = models.TextField(blank=True, null=True)
    pix_url = models.URLField(blank=True, null=True)
    codigo_barras = models.CharField(max_length=150, blank=True, null=True)
    fatura_url = models.URLField(blank=True, null=True)
    
    # Configurações da integração
    formas_pagamento = models.JSONField(
        default=list,
        help_text="Formas de pagamento habilitadas ['BOLETO', 'PIX', etc]"
    )
    envio_email = models.BooleanField(default=True)
    envio_whatsapp = models.BooleanField(default=False)
    
    # Controle
    data_integracao = models.DateTimeField(auto_now_add=True)
    data_ultima_atualizacao = models.DateTimeField(auto_now=True)
    
    # Webhooks e logs
    webhooks_recebidos = models.JSONField(
        default=list,
        help_text="Log dos webhooks recebidos do Asaas"
    )
    
    class Meta:
        verbose_name = "Integração Asaas"
        verbose_name_plural = "Integrações Asaas"
        indexes = [
            models.Index(fields=['asaas_id'], name='idx_asaas_id'),
            models.Index(fields=['gateway_status'], name='idx_gateway_status'),
        ]
    
    def __str__(self):
        return f"Asaas {self.asaas_id} - {self.cobranca}"
    
    def pode_ser_integrada(self):
        """Verifica se a cobrança pode ser integrada"""
        erros = []
        
        if not self.cobranca.data_vencimento:
            erros.append("Data de vencimento não informada")
        if self.cobranca.valor_total <= 0:
            erros.append("Valor total deve ser maior que zero")
        if not self.cobranca.descricao:
            erros.append("Descrição é obrigatória")
        if not self.cobranca.inquilino:
            erros.append("Inquilino não informado")
        if hasattr(self, 'asaas_id') and self.asaas_id:
            erros.append("Cobrança já foi integrada")
            
        return len(erros) == 0, erros
    
    def integrar_asaas(self, opcoes_integracao=None):
        """Integra cobrança com o gateway de pagamento (Asaas)"""
        pode_integrar, erros = self.pode_ser_integrada()
        
        if not pode_integrar:
            return {'status': 'error', 'erros': erros}
        
        from ..services.asaas_integracao_service import AsaasIntegracaoService
        return AsaasIntegracaoService.criar_cobranca(self, opcoes_integracao)
    
    def processar_webhook(self, dados_webhook):
        """Processa webhook recebido do Asaas"""
        from ..services.asaas_integracao_service import AsaasIntegracaoService
        return AsaasIntegracaoService.processar_webhook(self, dados_webhook)


# === HELPER PARA COMPATIBILIDADE ===
# Adiciona propriedades na Cobrança para manter compatibilidade
def _add_asaas_properties():
    """Adiciona properties para compatibilidade com código existente"""
    
    @property
    def integrada_asaas(self):
        return hasattr(self, 'asaas_integracao') and self.asaas_integracao.asaas_id
    
    @property
    def asaas_id(self):
        return getattr(self.asaas_integracao, 'asaas_id', None) if hasattr(self, 'asaas_integracao') else None
    
    @property
    def boleto_url(self):
        return getattr(self.asaas_integracao, 'boleto_url', None) if hasattr(self, 'asaas_integracao') else None
    
    @property
    def pix_copia_cola(self):
        return getattr(self.asaas_integracao, 'pix_copia_cola', None) if hasattr(self, 'asaas_integracao') else None
    
    @property
    def pix_url(self):
        return getattr(self.asaas_integracao, 'pix_url', None) if hasattr(self, 'asaas_integracao') else None
    
    @property
    def gateway_status(self):
        return getattr(self.asaas_integracao, 'gateway_status', None) if hasattr(self, 'asaas_integracao') else None
    
    # Adicionar as properties à classe
    Cobranca.integrada_asaas = integrada_asaas
    Cobranca.asaas_id = asaas_id
    Cobranca.boleto_url = boleto_url
    Cobranca.pix_copia_cola = pix_copia_cola
    Cobranca.pix_url = pix_url
    Cobranca.gateway_status = gateway_status

# Executar ao importar o módulo
_add_asaas_properties()

