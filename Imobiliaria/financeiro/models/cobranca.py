# financeiro/models/cobranca.py
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from decimal import Decimal
from django.apps import apps
import datetime
from financeiro.mixins.asaas_mixin import AsaasIntegracaoMixin



class Cobranca(models.Model):
    """
    Modelo para cobrança mensal de contratos.
    
    LÓGICA SIMPLES (como era antes, mas melhor organizada):
    1. Contrato tem valor_base
    2. Despesas são calculadas/rateadas conforme regras
    3. Cobrança tem UM ÚNICO VALOR = contrato.valor_base + despesas
    4. Este valor é o que vai no boleto/PIX
    """
    STATUS_CHOICES = [
        ('rascunho', 'Rascunho'),        # Em preparação
        ('pendente', 'Pendente'),        # Enviada para pagamento  
        ('paga', 'Paga'),               # Pagamento confirmado
        ('atrasada', 'Atrasada'),       # Vencida sem pagamento
        ('cancelada', 'Cancelada'),     # Cancelada
        ('parcial', 'Pago Parcial'),    # Pagamento parcial recebido
    ]

    # === RELACIONAMENTOS ===
    contrato = models.ForeignKey(
        'sisimob.Contrato', 
        on_delete=models.CASCADE, 
        related_name='cobrancas_financeiro',
        help_text="Contrato base desta cobrança"
    )

    # === PERÍODO DE REFERÊNCIA ===
    mes_referencia = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        help_text="Mês de referência da cobrança"
    )
    ano_referencia = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(2020), MaxValueValidator(2030)],
        help_text="Ano de referência da cobrança"
    )
    
    # === VALOR ÚNICO (como era antes) ===
    valor = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Valor total da cobrança (contrato.valor_base + despesas)"
    )

    # === CONTROLE E IDENTIFICAÇÃO ===
    numero_cobranca = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        help_text="Número único da cobrança"
    )
    
    descricao = models.TextField(
        blank=True,
        help_text="Descrição detalhada da cobrança"
    )

    # === DATAS ===
    data_vencimento = models.DateField(
        help_text="Data de vencimento"
    )
    data_emissao = models.DateField(
        auto_now_add=True,
        help_text="Data de criação"
    )
    data_pagamento = models.DateField(
        null=True, 
        blank=True,
        help_text="Data do pagamento (quando paga)"
    )
    
    # === STATUS ===
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='rascunho'
    )
    
    # === CONTROLE INTERNO ===
    observacoes = models.TextField(
        blank=True, 
        help_text="Observações internas"
    )
    
    # === METADADOS PARA TRANSPARÊNCIA ===
    # Guardamos os componentes do valor para transparência/auditoria
    detalhes_calculo = models.JSONField(
        default=dict,
        help_text="Detalhes de como o valor foi calculado (valor_base + despesas)"
    )
    
    criada_automaticamente = models.BooleanField(
        default=True,
        help_text="Se foi criada pelo processo automático"
    )

    # === TIMESTAMPS ===
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cobrança"
        verbose_name_plural = "Cobranças"
        ordering = ['-data_vencimento', '-ano_referencia', '-mes_referencia']
        unique_together = [('contrato', 'mes_referencia', 'ano_referencia')]
        
        indexes = [
            models.Index(fields=['contrato', 'mes_referencia', 'ano_referencia'], name='idx_contrato_periodo'),
            models.Index(fields=['status', 'data_vencimento'], name='idx_status_vencimento'),
            models.Index(fields=['numero_cobranca'], name='idx_numero_cobranca'),
            models.Index(fields=['data_vencimento'], name='idx_vencimento'),
            models.Index(fields=['status'], name='idx_status'),
        ]
        
        constraints = [
            models.CheckConstraint(
                check=models.Q(valor__gt=0),
                name='valor_positivo'
            ),
            models.CheckConstraint(
                check=models.Q(mes_referencia__gte=1, mes_referencia__lte=12),
                name='mes_referencia_valido'
            ),
        ]

    # === PROPERTIES ESSENCIAIS ===
    @property
    def inquilino(self):
        """Inquilino do contrato"""
        if self.contrato and hasattr(self.contrato, 'inquilino'):
            if hasattr(self.contrato.inquilino, 'all'):
                return self.contrato.inquilino.first()
            return self.contrato.inquilino
        return None

    @property
    def data_referencia_texto(self):
        """Período em formato legível"""
        meses = {
            1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
            5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
            9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
        }
        mes_nome = meses.get(self.mes_referencia, f'Mês {self.mes_referencia}')
        return f"{mes_nome}/{self.ano_referencia}"

    @property
    def esta_atrasada(self):
        """Verifica se está atrasada"""
        return (
            self.status in ['pendente', 'atrasada', 'parcial'] and 
            self.data_vencimento < timezone.now().date()
        )

    @property
    def dias_atraso(self):
        """Dias em atraso"""
        if self.esta_atrasada:
            return (timezone.now().date() - self.data_vencimento).days
        return 0

    # === PROPERTIES PARA COMPATIBILIDADE ===
    @property
    def valor_total(self):
        """Compatibilidade: mesmo que .valor"""
        return self.valor

    @property
    def valor_aluguel(self):
        """Valor base do contrato (do detalhes_calculo)"""
        return Decimal(str(self.detalhes_calculo.get('valor_base', '0.00')))

    @property
    def valor_despesas(self):
        """Valor das despesas (do detalhes_calculo)"""
        return Decimal(str(self.detalhes_calculo.get('valor_despesas', '0.00')))

    @property
    def valor_base_contrato(self):
        """Alias para valor_aluguel"""
        return self.valor_aluguel

    @property
    def valor_despesas_rateadas(self):
        """Alias para valor_despesas"""
        return self.valor_despesas

    # === MÉTODOS DE CÁLCULO ===
    def recalcular_valor_total(self):
        """Recalcula o valor baseado no contrato + despesas atuais com lógica de crédito/débito"""
        from ..services.cobranca.cobranca_calculadora_service import CobrancaCalculadoraService
        
        # 1. Pegar valor base atual do contrato
        valor_base = getattr(self.contrato, 'valor_base', Decimal('0.00'))
        if hasattr(self.contrato, 'valor_aluguel'):
            valor_base = self.contrato.valor_aluguel
        
        # 2. Usar o método completo que já inclui a lógica de crédito/débito
        calculo = CobrancaCalculadoraService.calcular_valor_completo(
            self.contrato, 
            self.mes_referencia, 
            self.ano_referencia
        )
        
        # 3. Calcular valor total com a nova lógica
        novo_valor = calculo['valor_total']
        
        # 4. Atualizar se mudou
        if novo_valor != self.valor:
            self.valor = novo_valor
            self.detalhes_calculo = {
                'valor_base': float(calculo['valor_base']),
                'valor_despesas_liquido': float(calculo['valor_despesas']),  # Já é líquido (débitos - créditos)
                'detalhes_despesas': calculo['detalhes'],
                'data_calculo': timezone.now().isoformat(),
                'despesas_incluidas': calculo['detalhes'],  # Para compatibilidade
                'formula_calculo': f"Aluguel: R$ {calculo['valor_base']:.2f} + Despesas Inquilino: R$ {calculo['detalhes']['total_debitos']:.2f} - Créditos Proprietário: R$ {calculo['detalhes']['total_creditos']:.2f} = R$ {novo_valor:.2f}",
                'breakdown': {
                    'aluguel': float(calculo['valor_base']),
                    'despesas_inquilino': calculo['detalhes']['total_debitos'],
                    'creditos_proprietario': calculo['detalhes']['total_creditos'],
                    'valor_final': float(novo_valor)
                }
            }
            self.save(update_fields=['valor', 'detalhes_calculo'])
            
        return self.valor

    def get_detalhes_financeiros(self):
        """Detalhes de como o valor foi composto"""
        detalhes = self.detalhes_calculo or {}
        
        return {
            'valor_total': self.valor,
            'valor_base': Decimal(str(detalhes.get('valor_base', '0.00'))),
            'valor_despesas': Decimal(str(detalhes.get('valor_despesas', '0.00'))),
            'despesas_incluidas': detalhes.get('despesas_incluidas', []),
            'data_ultimo_calculo': detalhes.get('data_calculo'),
            'periodo': self.data_referencia_texto,
            'status': self.get_status_display(),
        }

    def get_resumo_financeiro(self):
        """Resumo completo para exibição"""
        detalhes = self.get_detalhes_financeiros()
        
        return {
            **detalhes,
            'percentual_despesas': (
                (detalhes['valor_despesas'] / self.valor * 100) 
                if self.valor > 0 else Decimal('0.00')
            ),
            'dias_atraso': self.dias_atraso if self.esta_atrasada else 0,
            'pode_ser_paga': self.status in ['pendente', 'atrasada', 'parcial']
        }

    # === AÇÕES DE STATUS ===
    def enviar_para_pagamento(self):
        """Move de rascunho para pendente"""
        if self.status == 'rascunho':
            if self.valor <= 0:
                raise ValidationError("Cobrança deve ter valor maior que zero")
            
            self.status = 'pendente'
            self.save(update_fields=['status'])
            return True
        return False

    def marcar_como_paga(self, data_pagamento=None):
        """Marca como paga"""
        if self.status == 'paga':
            return False
            
        if not data_pagamento:
            data_pagamento = timezone.now().date()
            
        self.status = 'paga'
        self.data_pagamento = data_pagamento
        self.save(update_fields=['status', 'data_pagamento'])
        
        # Criar repasse automático
        self._criar_repasse_automatico()
        return True

    def cancelar(self, motivo=None):
        """Cancela a cobrança"""
        if self.status == 'paga':
            raise ValidationError("Não é possível cancelar cobrança paga")
            
        self.status = 'cancelada'
        if motivo:
            self.observacoes = f"{self.observacoes}\n\nCancelada: {motivo}".strip()
        
        self.save(update_fields=['status', 'observacoes'])

    # === GERAÇÃO AUTOMÁTICA ===
    def gerar_numero_cobranca(self):
        """Gera número único"""
        if not self.numero_cobranca:
            prefixo = f"COB{self.ano_referencia}{str(self.mes_referencia).zfill(2)}"
            contador = str(self.contrato.id).zfill(4)
            self.numero_cobranca = f"{prefixo}{contador}"
            
    def gerar_descricao_automatica(self):
        """Gera descrição baseada nos componentes do valor"""
        detalhes = self.detalhes_calculo or {}
        valor_base = Decimal(str(detalhes.get('valor_base', '0.00')))
        valor_despesas = Decimal(str(detalhes.get('valor_despesas', '0.00')))
        
        linhas = [
            f"🏠 COBRANÇA {self.data_referencia_texto}",
            f"Contrato: {self.contrato}",
            "",
        ]
        
        # Mostrar composição do valor
        if valor_base > 0:
            linhas.append(f"💰 Valor Base: R$ {valor_base:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        
        if valor_despesas > 0:
            linhas.append(f"🏢 Despesas: R$ {valor_despesas:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
            
            # Listar despesas se disponível
            despesas_info = detalhes.get('despesas_incluidas', [])
            if despesas_info:
                linhas.append("")
                linhas.append("📋 DESPESAS INCLUÍDAS:")
                for despesa in despesas_info:
                    if isinstance(despesa, dict):
                        nome = despesa.get('nome', 'Despesa')
                        valor = despesa.get('valor_rateado', 0)
                    else:
                        nome = str(despesa)
                        valor = 0
                    
                    if valor > 0:
                        valor_fmt = f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                        linhas.append(f"• {nome}: {valor_fmt}")
        
        linhas.extend([
            "",
            f"💸 TOTAL: R$ {self.valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
            f"📅 Vencimento: {self.data_vencimento.strftime('%d/%m/%Y')}"
        ])
        
        return "\n".join(linhas)

    # === VALIDAÇÕES ===
    def clean(self):
        """Validações customizadas"""
        super().clean()
        
        errors = {}
        
        # Validar período
        if self.mes_referencia and self.ano_referencia:
            try:
                datetime.date(self.ano_referencia, self.mes_referencia, 1)
            except ValueError:
                errors['mes_referencia'] = 'Período inválido'
        
        # Validar valor
        if self.valor and self.valor <= 0:
            errors['valor'] = 'Valor deve ser positivo'
        
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        """Save com automações"""
        # Gerar número se não existe
        if not self.numero_cobranca:
            self.gerar_numero_cobranca()
        
        # Gerar descrição se vazia e criada automaticamente
        if not self.descricao and self.criada_automaticamente:
            self.descricao = self.gerar_descricao_automatica()
        
        # Validar
        self.full_clean()
        
        super().save(*args, **kwargs)
        
        # Atualizar status baseado na data
        self._atualizar_status_automatico()

    def _atualizar_status_automatico(self):
        """Atualiza status baseado na data de vencimento"""
        if self.status == 'pendente' and self.data_vencimento < timezone.now().date():
            self.status = 'atrasada'
            Cobranca.objects.filter(id=self.id).update(status='atrasada')

    def _criar_repasse_automatico(self):
        """Cria repasse para o proprietário"""
        try:
            from ..models.repasse import Repasse
            
            # Calcular valor do repasse (total - taxa de admin)
            valor_repasse = self.calcular_valor_repasse()
            
            Repasse.objects.get_or_create(
                cobranca=self,
                defaults={
                    'valor': valor_repasse,
                    'status': 'pendente',
                    'data_prevista': self.data_pagamento
                }
            )
        except ImportError:
            # Modelo Repasse ainda não criado
            pass

    def calcular_valor_repasse(self):
        """Calcula valor a ser repassado ao proprietário"""
        # Por enquanto, repassa o valor total (depois implementar taxa de administração)
        return self.valor

    def __str__(self):
        return f"{self.numero_cobranca} - {self.contrato} - {self.data_referencia_texto}"



def criar_cobranca_do_contrato(contrato, mes_referencia, ano_referencia, data_vencimento, **opcoes):
    """
    Factory function para criar cobrança com a lógica CORRETA:
    VALOR = contrato.valor_base + despesas_inquilino - despesas_proprietario
    """
    from ..services.cobranca.cobranca_calculadora_service import CobrancaCalculadoraService
    from financeiro.views.cobranca_views import obter_valor_atual_contrato
    
    # 1. VALOR BASE: pegar do contrato
    
    valor_base = Decimal(str(obter_valor_atual_contrato(contrato, mes_referencia, ano_referencia)))
        
    if valor_base <= 0:
        raise ValidationError("Contrato deve ter valor base/aluguel definido")
    
    # 2. USAR O CÁLCULO COMPLETO COM LÓGICA CORRETA
    if opcoes.get('incluir_despesas', True):
        calculo = CobrancaCalculadoraService.calcular_valor_completo(
            contrato, mes_referencia, ano_referencia
        )
        valor_total = calculo['valor_total']
        detalhes_calculo = {
            'valor_base': float(calculo['valor_base']),
            'valor_despesas_liquido': float(calculo['valor_despesas']),
            'data_calculo': timezone.now().isoformat(),
            'despesas_incluidas': calculo['detalhes'],
            'metodo_calculo': 'automatico_com_creditos',
            'formula_calculo': f"R$ {calculo['valor_base']:.2f} + R$ {calculo['detalhes']['total_debitos']:.2f} - R$ {calculo['detalhes']['total_creditos']:.2f} = R$ {valor_total:.2f}",
            'breakdown': {
                'aluguel': float(calculo['valor_base']),
                'despesas_inquilino': calculo['detalhes']['total_debitos'],
                'creditos_proprietario': calculo['detalhes']['total_creditos'],
                'valor_final': float(valor_total)
            }
        }
    else:
        # Apenas aluguel, sem despesas
        valor_total = valor_base
        detalhes_calculo = {
            'valor_base': float(valor_base),
            'valor_despesas_liquido': 0.00,
            'data_calculo': timezone.now().isoformat(),
            'metodo_calculo': 'apenas_aluguel'
        }
    
    # 3. CRIAR COBRANÇA
    cobranca = Cobranca.objects.create(
        contrato=contrato,
        mes_referencia=mes_referencia,
        ano_referencia=ano_referencia,
        data_vencimento=data_vencimento,
        valor=valor_total,  # Valor com a lógica correta
        detalhes_calculo=detalhes_calculo,
        criada_automaticamente=True
    )
    
    return cobranca

# Em models.py ou em uma função de cálculo
def calcular_valor_devido_inquilino(contrato):
    """Calcula valor devido usando a nova lógica"""
    from ..services.cobranca.cobranca_calculadora_service import CobrancaCalculadoraService
    import datetime
    
    # Usar mês/ano atual para o cálculo
    hoje = datetime.date.today()
    
    calculo = CobrancaCalculadoraService.calcular_valor_completo(
        contrato, hoje.month, hoje.year
    )
    
    return calculo['valor_total']

class AsaasIntegracao(models.Model, AsaasIntegracaoMixin):
    """Integração com gateway Asaas"""
    cobranca = models.OneToOneField(
        Cobranca, 
        on_delete=models.CASCADE, 
        related_name='asaas_integracao'
    )
    
    asaas_id = models.CharField(max_length=100, unique=True)
    gateway_status = models.CharField(max_length=30, blank=True, null=True)
    boleto_url = models.URLField(blank=True, null=True)
    pix_copia_cola = models.TextField(blank=True, null=True)
    pix_qrcode = models.TextField(blank=True, null=True)
    pix_url = models.URLField(blank=True, null=True)
    fatura_url = models.URLField(blank=True, null=True)
    formas_pagamento = models.JSONField(
        default=list,
        help_text="Formas de pagamento habilitadas ['BOLETO', 'PIX', etc]"
    )
    envio_email = models.BooleanField(default=True)
    envio_whatsapp = models.BooleanField(default=False)
    webhooks_recebidos = models.JSONField(
        default=list,
        help_text='Log dos webhooks recebidos do Asaas'
    )
    codigo_barras = models.TextField(
        blank=True, null=True, 
        verbose_name='Código de Barras',
        help_text='Código de barras numérico do boleto'
    )
    
    linha_digitavel = models.TextField(
        blank=True, null=True,
        verbose_name='Linha Digitável', 
        help_text='Linha digitável do boleto (identificationField)'
    )
    
    nosso_numero = models.CharField(
        max_length=50, blank=True, null=True,
        verbose_name='Nosso Número',
        help_text='Nosso número do boleto'
    )
    data_integracao = models.DateTimeField(auto_now_add=True)
    data_ultima_atualizacao = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Integração Asaas"
        verbose_name_plural = "Integrações Asaas"
    
    def __str__(self):
        return f"Asaas {self.cobranca}"


# === HELPER PARA COMPATIBILIDADE COM CÓDIGO EXISTENTE ===
def _add_compatibility_properties():
    """Adiciona properties para manter compatibilidade"""
    
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

# Executar ao importar
_add_compatibility_properties()


