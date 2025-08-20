# financeiro/models/repasse.py (versão melhorada)
from django.db import models
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta
import calendar
import logging

logger = logging.getLogger(__name__)


class Repasse(models.Model):
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('efetuado', 'Efetuado'),
        ('cancelado', 'Cancelado'),
    ]
    TIPO_REPASSE_CHOICES = [
        ('automatico', 'Automático'),
        ('manual', 'Manual'),
    ]
    METODO_PAGAMENTO_CHOICES = [
        ('pix', 'PIX'),
        ('transferencia', 'Transferência Bancária'),
        ('ted', 'TED'),
        ('doc', 'DOC'),
        ('cheque', 'Cheque'),
        ('dinheiro', 'Dinheiro'),
        ('outros', 'Outros'),
    ]

    proprietario = models.ForeignKey('sisimob.Cliente', on_delete=models.CASCADE, related_name='repasses_recebidos')
    cobranca = models.ForeignKey('financeiro.Cobranca', on_delete=models.SET_NULL, null=True, blank=True, related_name='repasses_cobranca')
    contrato = models.ForeignKey('sisimob.Contrato', on_delete=models.CASCADE, related_name='repasses_contrato')

    valor = models.DecimalField(max_digits=10, decimal_places=2)
    valor_desconto = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    valor_taxa_admin = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    data_criacao = models.DateTimeField(auto_now_add=True)
    data_prevista = models.DateField()
    data_efetivacao = models.DateField(null=True, blank=True)

    mes_referencia = models.PositiveSmallIntegerField()
    ano_referencia = models.PositiveSmallIntegerField()

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')
    tipo = models.CharField(max_length=20, choices=TIPO_REPASSE_CHOICES, default='automatico')
    metodo_pagamento = models.CharField(max_length=20, choices=METODO_PAGAMENTO_CHOICES, null=True, blank=True)

    descricao = models.TextField(blank=True, null=True)
    observacoes = models.TextField(blank=True, null=True)
    comprovante = models.FileField(upload_to='repasses/comprovantes/', null=True, blank=True)

    class Meta:
        verbose_name = 'Repasse'
        verbose_name_plural = 'Repasses'
        ordering = ['-ano_referencia', '-mes_referencia', '-data_prevista']

    def __str__(self):
        return f"Repasse {self.id} - {self.proprietario} - {self.mes_referencia}/{self.ano_referencia}"

    @property
    def valor_liquido(self):
        return self.valor - self.valor_desconto - self.valor_taxa_admin

    @property
    def esta_atrasado(self):
        return self.status == 'pendente' and self.data_prevista < date.today()

    @property
    def dias_atraso(self):
        return (date.today() - self.data_prevista).days if self.esta_atrasado else 0

    def efetivar_repasse(self, metodo_pagamento=None, observacoes=None):
        if self.status != 'pendente':
            return False
        self.status = 'efetuado'
        self.data_efetivacao = date.today()
        if metodo_pagamento:
            self.metodo_pagamento = metodo_pagamento
        if observacoes:
            self.observacoes = observacoes
        self.save()

        if self.cobranca:
            self.cobranca.status_repasse = 'repassado'
            self.cobranca.data_repasse = self.data_efetivacao
            self.cobranca.save(update_fields=['status_repasse', 'data_repasse'])

        from .movimento import MovimentoConta
        MovimentoConta.objects.create(
            proprietario=self.proprietario,
            contrato=self.contrato,
            tipo='repasse',
            descricao=f"Repasse referente a {self.mes_referencia}/{self.ano_referencia}",
            valor=self.valor_liquido,
            data_referencia=date(self.ano_referencia, self.mes_referencia, 1)
        )
        return True

    def cancelar_repasse(self, motivo=None):
        if self.status != 'pendente':
            return False
        self.status = 'cancelado'
        if motivo:
            self.observacoes = (self.observacoes or '') + f"\nCancelado: {motivo}"
        self.save()
        if self.cobranca:
            self.cobranca.status_repasse = 'cancelado'
            self.cobranca.save(update_fields=['status_repasse'])
        return True


class PoliticaRepasseContrato(models.Model):
    """Política de repasse específica por contrato"""
    
    PERIODICIDADE_CHOICES = [
        ('diaria', 'Diária'),
        ('semanal', 'Semanal'),
        ('quinzenal', 'Quinzenal'),
        ('mensal', 'Mensal'),
    ]
    
    DIA_SEMANA_CHOICES = [(i, d) for i, d in enumerate([
        'Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo'
    ], start=1)]
    
    TIPO_DIA_CHOICES = [
        ('corridos', 'Dias Corridos'),
        ('uteis', 'Dias Úteis'),
    ]

    # Relacionamento com contrato (um-para-um)
    contrato = models.OneToOneField(
        'sisimob.Contrato', 
        on_delete=models.CASCADE, 
        related_name='politica_repasse'
    )
    
    # Configurações básicas
    ativa = models.BooleanField(default=True)
    periodicidade = models.CharField(max_length=20, choices=PERIODICIDADE_CHOICES, default='mensal')
    tipo_dias = models.CharField(max_length=10, choices=TIPO_DIA_CHOICES, default='uteis')
    
    # Configurações de data
    dia_mes = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Dia do mês para repasse mensal (1-31)")
    dia_semana = models.PositiveSmallIntegerField(choices=DIA_SEMANA_CHOICES, null=True, blank=True, help_text="Dia da semana para repasse semanal")
    dias_apos_recebimento = models.PositiveSmallIntegerField(default=2, help_text="Dias para aguardar após recebimento")
    
    # Configurações financeiras
    percentual_adiantamento = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    taxa_adiantamento = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    valor_minimo_repasse = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    taxa_admin_personalizada = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Taxa específica para este contrato (deixe vazio para usar padrão)")
    
    # Configurações avançadas
    considerar_feriados = models.BooleanField(default=True, help_text="Considerar feriados no cálculo de dias úteis")
    antecipar_fds_feriados = models.BooleanField(default=True, help_text="Antecipar repasse se data cair em final de semana/feriado")
    
    # Metadados
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    observacoes = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = 'Política de Repasse do Contrato'
        verbose_name_plural = 'Políticas de Repasse dos Contratos'
        ordering = ['-data_atualizacao']

    def __str__(self):
        return f"Política {self.contrato} - {self.get_periodicidade_display()}"

    def calcular_proxima_data_repasse(self, data_referencia=None):
        """Calcula a próxima data de repasse considerando tipo de dias"""
        if not data_referencia:
            data_referencia = date.today()

        proxima_data = None

        if self.periodicidade == 'mensal' and self.dia_mes:
            proxima_data = self._calcular_data_mensal(data_referencia)
        elif self.periodicidade == 'semanal' and self.dia_semana:
            proxima_data = self._calcular_data_semanal(data_referencia)
        elif self.periodicidade == 'quinzenal':
            proxima_data = self._calcular_data_quinzenal(data_referencia)
        elif self.periodicidade == 'diaria':
            proxima_data = self._calcular_data_diaria(data_referencia)

        if proxima_data and self.tipo_dias == 'uteis':
            proxima_data = self._ajustar_para_dia_util(proxima_data)

        return proxima_data

    def _calcular_data_mensal(self, data_referencia):
        """Calcula próxima data para periodicidade mensal"""
        ano, mes = data_referencia.year, data_referencia.month
        
        if data_referencia.day > self.dia_mes:
            mes += 1
            if mes > 12:
                mes = 1
                ano += 1
        
        ultimo_dia = calendar.monthrange(ano, mes)[1]
        dia = min(self.dia_mes, ultimo_dia)
        
        return date(ano, mes, dia)

    def _calcular_data_semanal(self, data_referencia):
        """Calcula próxima data para periodicidade semanal"""
        dias_ate = (self.dia_semana - data_referencia.isoweekday()) % 7
        if dias_ate == 0:
            dias_ate = 7
        return data_referencia + timedelta(days=dias_ate)

    def _calcular_data_quinzenal(self, data_referencia):
        """Calcula próxima data para periodicidade quinzenal"""
        ano, mes = data_referencia.year, data_referencia.month
        
        if data_referencia.day < 15:
            return date(ano, mes, 15)
        else:
            ultimo_dia = calendar.monthrange(ano, mes)[1]
            if data_referencia.day >= ultimo_dia:
                mes += 1
                if mes > 12:
                    mes = 1
                    ano += 1
                return date(ano, mes, 15)
            return date(ano, mes, ultimo_dia)

    def _calcular_data_diaria(self, data_referencia):
        """Calcula próxima data para periodicidade diária"""
        return data_referencia + timedelta(days=1)

    def _ajustar_para_dia_util(self, data):
        """Ajusta data para próximo dia útil se necessário"""
        if not data:
            return data

        # Verifica se é final de semana
        while data.weekday() >= 5:  # 5=Sábado, 6=Domingo
            if self.antecipar_fds_feriados:
                data = data - timedelta(days=1)
            else:
                data = data + timedelta(days=1)

        # TODO: Implementar verificação de feriados se considerar_feriados=True
        # Pode usar biblioteca como python-holidays ou criar modelo de feriados
        
        return data

    def _is_feriado(self, data):
        """Verifica se uma data é feriado (implementar conforme necessidade)"""
        # Implementar verificação de feriados
        # Por exemplo, usando biblioteca holidays:
        # import holidays
        # br_holidays = holidays.Brazil()
        # return data in br_holidays
        return False

    def get_taxa_admin(self):
        """Retorna a taxa administrativa a ser usada"""
        if self.taxa_admin_personalizada is not None:
            return self.taxa_admin_personalizada
        
        # Buscar taxa padrão global (implementar ConfiguracaoGeral depois)
        return Decimal('8.00')  # Padrão de 8%

    def simular_proximo_repasse(self, valor_base=None):
        """Simula como seria o próximo repasse"""
        if not valor_base:
            valor_base = self.contrato.valor_aluguel

        proxima_data = self.calcular_proxima_data_repasse()
        taxa_admin = self.get_taxa_admin()
        valor_taxa = valor_base * (taxa_admin / 100)
        valor_liquido = valor_base - valor_taxa

        if valor_liquido < self.valor_minimo_repasse:
            return {
                'viavel': False,
                'motivo': f'Valor líquido (R$ {valor_liquido:.2f}) abaixo do mínimo (R$ {self.valor_minimo_repasse:.2f})'
            }

        return {
            'viavel': True,
            'data_prevista': proxima_data,
            'valor_bruto': valor_base,
            'valor_taxa_admin': valor_taxa,
            'valor_liquido': valor_liquido,
            'tipo_dias': self.get_tipo_dias_display(),
            'periodicidade': self.get_periodicidade_display()
        }
# Adicione estes métodos no modelo PoliticaRepasseContrato

    def get_taxa_admin(self):
        """
        Retorna a taxa de administração personalizada ou a padrão do contrato.
        """
        if self.taxa_admin_personalizada:
            return self.taxa_admin_personalizada
        
        # Se não há taxa personalizada, usar a do contrato
        if hasattr(self.contrato, 'valor_taxa_administracao_percentual'):
            return self.contrato.valor_taxa_administracao_percentual or Decimal('8.00')
        
        # Fallback padrão
        return Decimal('8.00')

    def simular_proximo_repasse(self):
        """
        Simula o próximo repasse baseado nesta política.
        """
        contrato = self.contrato
        
        # Obter valor atual do aluguel
        valor_atual = contrato.valor_aluguel_atual()
        
        # Calcular taxa de administração
        taxa_admin = self.get_taxa_admin()
        valor_taxa_admin = valor_atual * (taxa_admin / 100)
        valor_liquido = valor_atual - valor_taxa_admin
        
        # Verificar valor mínimo
        acima_minimo = valor_liquido >= (self.valor_minimo_repasse or Decimal('0'))
        
        # Calcular próxima data
        hoje = date.today()
        if self.tipo_dias == 'fixo':
            try:
                proxima_data = hoje.replace(day=self.dia_mes or 1)
                if proxima_data <= hoje:
                    # Se já passou este mês, vai para o próximo
                    proxima_data = proxima_data + relativedelta(months=1)
            except ValueError:
                # Dia inválido para o mês
                proxima_data = hoje + timedelta(days=30)
        else:
            # Outros tipos
            proxima_data = hoje + timedelta(days=self.dias_apos_recebimento or 7)
        
        return {
            'valor_bruto': valor_atual,
            'taxa_admin': taxa_admin,
            'valor_taxa_admin': valor_taxa_admin,
            'valor_liquido': valor_liquido,
            'valor_minimo': self.valor_minimo_repasse or Decimal('0'),
            'acima_minimo': acima_minimo,
            'proxima_data': proxima_data,
            'periodicidade': self.get_periodicidade_display(),
            'tipo_dias': self.get_tipo_dias_display(),
            'ativa': self.ativa
        }

def calcular_data_repasse(self, data_pagamento_cobranca):
        """
        Calcula a data do repasse baseado na data de pagamento da cobrança
        
        Args:
            data_pagamento_cobranca (date): Data em que a cobrança foi paga
            
        Returns:
            date: Data prevista para o repasse
            
        Exemplo:
            Cobrança paga em 02/06/2025 (segunda-feira)
            Política: 5 dias úteis
            Resultado: 09/06/2025 (segunda-feira seguinte)
        """
        if not data_pagamento_cobranca:
            data_pagamento_cobranca = date.today()
        
        # Usar a data de pagamento como referência, não hoje
        data_base = data_pagamento_cobranca
        
        # LÓGICA PRINCIPAL: X dias após o PAGAMENTO da cobrança
        if self.dias_apos_recebimento:
            if self.tipo_dias == 'uteis':
                # Calcular X dias ÚTEIS após pagamento
                data_repasse = self._adicionar_dias_uteis(data_base, self.dias_apos_recebimento)
            else:
                # Calcular X dias CORRIDOS após pagamento
                data_repasse = data_base + timedelta(days=self.dias_apos_recebimento)
        
        # LÓGICA ALTERNATIVA: Periodicidade fixa (mensal, semanal, etc.)
        elif self.periodicidade == 'mensal' and self.dia_mes:
            data_repasse = self._calcular_data_mensal_apos_pagamento(data_base)
        elif self.periodicidade == 'semanal' and self.dia_semana:
            data_repasse = self._calcular_data_semanal_apos_pagamento(data_base)
        elif self.periodicidade == 'quinzenal':
            data_repasse = self._calcular_data_quinzenal_apos_pagamento(data_base)
        else:
            # Fallback: 2 dias úteis (padrão conservador)
            data_repasse = self._adicionar_dias_uteis(data_base, 2)
        
        # Ajustar para dia útil se necessário
        if self.tipo_dias == 'uteis' and self.antecipar_fds_feriados:
            data_repasse = self._ajustar_para_dia_util(data_repasse)
        
        return data_repasse
    
def _adicionar_dias_uteis(self, data_inicial, quantidade_dias):
    """
    Adiciona quantidade específica de dias ÚTEIS (segunda a sexta)
    
    Exemplo:
        data_inicial = 02/06/2025 (segunda)
        quantidade_dias = 5
        Resultado = 09/06/2025 (segunda seguinte)
        
        Contagem:
        - Dia 1: 03/06 (terça)
        - Dia 2: 04/06 (quarta) 
        - Dia 3: 05/06 (quinta)
        - Dia 4: 06/06 (sexta)
        - Dia 5: 09/06 (segunda) ← RESULTADO
    """
    data_atual = data_inicial
    dias_adicionados = 0
    
    while dias_adicionados < quantidade_dias:
        data_atual = data_atual + timedelta(days=1)
        
        # Verificar se é dia útil (segunda=0 a sexta=4)
        if data_atual.weekday() < 5:  # 0-4 = segunda a sexta
            # Verificar se não é feriado (implementar depois)
            if not self._is_feriado(data_atual):
                dias_adicionados += 1
    
    return data_atual

def _calcular_data_mensal_apos_pagamento(self, data_pagamento):
    """
    Para periodicidade mensal: próximo dia X do mês após o pagamento
    
    Exemplo:
        Pagamento: 02/06/2025
        Política: dia 15 de cada mês
        Resultado: 15/06/2025 (mesmo mês se ainda não passou)
                    ou 15/07/2025 (próximo mês se já passou)
    """
    ano = data_pagamento.year
    mes = data_pagamento.month
    
    # Se ainda não passou o dia do mês, usar o mesmo mês
    if data_pagamento.day < self.dia_mes:
        try:
            return date(ano, mes, self.dia_mes)
        except ValueError:
            # Dia inválido para o mês (ex: dia 31 em fevereiro)
            ultimo_dia = calendar.monthrange(ano, mes)[1]
            return date(ano, mes, ultimo_dia)
    else:
        # Já passou o dia, ir para o próximo mês
        mes += 1
        if mes > 12:
            mes = 1
            ano += 1
        
        try:
            return date(ano, mes, self.dia_mes)
        except ValueError:
            ultimo_dia = calendar.monthrange(ano, mes)[1]
            return date(ano, mes, ultimo_dia)

def _calcular_data_semanal_apos_pagamento(self, data_pagamento):
    """
    Para periodicidade semanal: próximo dia X da semana após o pagamento
    
    Exemplo:
        Pagamento: 02/06/2025 (segunda-feira = 0)
        Política: sexta-feira (4)
        Resultado: 06/06/2025 (próxima sexta)
    """
    dia_atual = data_pagamento.weekday()  # 0=segunda, 6=domingo
    
    # Converter nossa numeração (1=segunda) para Python (0=segunda)
    dia_desejado = self.dia_semana - 1  # Nossa: 1-7, Python: 0-6
    
    if dia_atual < dia_desejado:
        # Ainda não chegou o dia desta semana
        dias_para_adicionar = dia_desejado - dia_atual
    else:
        # Já passou o dia desta semana, ir para próxima
        dias_para_adicionar = 7 - dia_atual + dia_desejado
    
    return data_pagamento + timedelta(days=dias_para_adicionar)

def _calcular_data_quinzenal_apos_pagamento(self, data_pagamento):
    """
    Para periodicidade quinzenal: dia 15 ou último dia do mês
    """
    if data_pagamento.day < 15:
        # Usar dia 15 do mesmo mês
        return date(data_pagamento.year, data_pagamento.month, 15)
    else:
        # Ir para último dia do mês atual ou dia 15 do próximo
        ano = data_pagamento.year
        mes = data_pagamento.month
        ultimo_dia = calendar.monthrange(ano, mes)[1]
        
        if data_pagamento.day < ultimo_dia:
            return date(ano, mes, ultimo_dia)
        else:
            # Próximo mês, dia 15
            mes += 1
            if mes > 12:
                mes = 1
                ano += 1
            return date(ano, mes, 15)

def _ajustar_para_dia_util(self, data):
    """
    Ajusta data para dia útil se cair em final de semana ou feriado
    """
    if not data:
        return data
    
    # Se for sábado (5) ou domingo (6)
    while data.weekday() >= 5 or self._is_feriado(data):
        if self.antecipar_fds_feriados:
            # Antecipar: voltar para sexta-feira anterior
            data = data - timedelta(days=1)
        else:
            # Postergar: ir para próxima segunda-feira
            data = data + timedelta(days=1)
    
    return data

def _is_feriado(self, data):
    """
    Verifica se uma data é feriado
    
    TODO: Implementar verificação de feriados
    Pode usar biblioteca python-holidays ou criar modelo de feriados
    """
    if not self.considerar_feriados:
        return False
    
    # Implementação futura de feriados
    # Por enquanto, retorna False
    return False

def simular_repasse_com_data_pagamento(self, data_pagamento, valor_cobranca=None):
    """
    Simula um repasse baseado numa data específica de pagamento
    
    Exemplo de uso:
        politica.simular_repasse_com_data_pagamento(
            data_pagamento=date(2025, 6, 2),
            valor_cobranca=1000.00
        )
    """
    if not valor_cobranca:
        valor_cobranca = getattr(self.contrato, 'valor_aluguel', Decimal('1000.00'))
    
    # Calcular data do repasse
    data_repasse = self.calcular_data_repasse(data_pagamento)
    
    # Calcular valores
    taxa_admin = self.get_taxa_admin()
    valor_taxa = valor_cobranca * (taxa_admin / 100)
    valor_liquido = valor_cobranca - valor_taxa
    
    # Verificar se está acima do mínimo
    acima_minimo = valor_liquido >= (self.valor_minimo_repasse or Decimal('0'))
    
    return {
        'data_pagamento_cobranca': data_pagamento,
        'data_prevista_repasse': data_repasse,
        'dias_para_repasse': (data_repasse - data_pagamento).days,
        'valor_bruto': valor_cobranca,
        'valor_taxa_admin': valor_taxa,
        'valor_liquido': valor_liquido,
        'acima_minimo': acima_minimo,
        'politica_aplicada': {
            'periodicidade': self.get_periodicidade_display(),
            'dias_apos_recebimento': self.dias_apos_recebimento,
            'tipo_dias': self.get_tipo_dias_display(),
            'ativa': self.ativa
        }
    }

class PoliticaRepasseGlobal(models.Model):
    """Política global padrão (para contratos sem política específica)"""
    
    PERIODICIDADE_CHOICES = [
        ('diaria', 'Diária'),
        ('semanal', 'Semanal'),
        ('quinzenal', 'Quinzenal'),
        ('mensal', 'Mensal'),
    ]
    
    DIA_SEMANA_CHOICES = [(i, d) for i, d in enumerate([
        'Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo'
    ], start=1)]
    
    TIPO_DIA_CHOICES = [
        ('corridos', 'Dias Corridos'),
        ('uteis', 'Dias Úteis'),
    ]

    nome = models.CharField(max_length=100)
    ativa = models.BooleanField(default=True)
    periodicidade = models.CharField(max_length=20, choices=PERIODICIDADE_CHOICES, default='mensal')
    tipo_dias = models.CharField(max_length=10, choices=TIPO_DIA_CHOICES, default='uteis')
    dia_mes = models.PositiveSmallIntegerField(null=True, blank=True)
    dia_semana = models.PositiveSmallIntegerField(choices=DIA_SEMANA_CHOICES, null=True, blank=True)
    dias_apos_recebimento = models.PositiveSmallIntegerField(default=2)
    percentual_adiantamento = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    taxa_adiantamento = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    valor_minimo_repasse = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    taxa_admin_padrao = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('8.00'))
    considerar_feriados = models.BooleanField(default=True)
    antecipar_fds_feriados = models.BooleanField(default=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Política de Repasse Global'
        verbose_name_plural = 'Políticas de Repasse Globais'
        ordering = ['-ativa', 'nome']

    def __str__(self):
        return f"{self.nome} - {'Ativa' if self.ativa else 'Inativa'}"


class AgendamentoRepasse(models.Model):
    STATUS_CHOICES = [
        ('agendado', 'Agendado'),
        ('processando', 'Processando'),
        ('concluido', 'Concluído'),
        ('falha', 'Falha'),
        ('cancelado', 'Cancelado'),
    ]

    proprietario = models.ForeignKey('sisimob.Cliente', on_delete=models.CASCADE, related_name='agendamentos_repasse')
    contrato = models.ForeignKey('sisimob.Contrato', on_delete=models.CASCADE, related_name='agendamentos_repasse')
    politica_contrato = models.ForeignKey(PoliticaRepasseContrato, on_delete=models.SET_NULL, null=True, blank=True)
    politica_global = models.ForeignKey(PoliticaRepasseGlobal, on_delete=models.SET_NULL, null=True, blank=True)

    data_agendada = models.DateField()
    data_processamento = models.DateTimeField(null=True, blank=True)
    valor_previsto = models.DecimalField(max_digits=10, decimal_places=2)
    mes_referencia = models.PositiveSmallIntegerField()
    ano_referencia = models.PositiveSmallIntegerField()

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='agendado')
    detalhes_processamento = models.TextField(blank=True, null=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Agendamento de Repasse'
        verbose_name_plural = 'Agendamentos de Repasse'
        ordering = ['data_agendada', 'status']

    def __str__(self):
        return f"Agendamento {self.id} - {self.proprietario} - {self.mes_referencia}/{self.ano_referencia}"

    @property
    def politica_utilizada(self):
        """Retorna a política que será/foi utilizada"""
        return self.politica_contrato or self.politica_global

    def processar(self):
        if self.status != 'agendado':
            return False
        
        self.status = 'processando'
        self.save(update_fields=['status'])

        try:
            from .cobranca import Cobranca
            cobranca = Cobranca.objects.filter(
                contrato=self.contrato,
                mes_referencia=self.mes_referencia,
                ano_referencia=self.ano_referencia,
                status='paga'
            ).first()

            # Usar política do contrato se existir, senão usar global
            politica = self.politica_utilizada
            taxa_admin = politica.get_taxa_admin() if hasattr(politica, 'get_taxa_admin') else politica.taxa_admin_padrao

            valor_taxa_admin = self.valor_previsto * (taxa_admin / 100)

            repasse = Repasse.objects.create(
                proprietario=self.proprietario,
                cobranca=cobranca,
                contrato=self.contrato,
                valor=self.valor_previsto,
                valor_taxa_admin=valor_taxa_admin,
                data_prevista=self.data_agendada,
                mes_referencia=self.mes_referencia,
                ano_referencia=self.ano_referencia,
                status='pendente',
                tipo='automatico',
                descricao=f"Repasse automático referente a {self.mes_referencia}/{self.ano_referencia}"
            )

            self.status = 'concluido'
            self.data_processamento = timezone.now()
            self.detalhes_processamento = f"Repasse {repasse.id} criado com sucesso"
            self.save(update_fields=['status', 'data_processamento', 'detalhes_processamento'])
            return repasse

        except Exception as e:
            self.status = 'falha'
            self.detalhes_processamento = f"Erro ao processar: {str(e)}"
            self.save(update_fields=['status', 'detalhes_processamento'])
            logger.error(f"Erro ao processar agendamento {self.id}: {str(e)}")
            return False

    def cancelar(self, motivo=None):
        if self.status not in ['agendado', 'falha']:
            return False
        self.status = 'cancelado'
        if motivo:
            self.detalhes_processamento = (self.detalhes_processamento or '') + f"\nCancelado: {motivo}"
        self.save()
        return True
    

# financeiro/models/repasse_integrado.py

from decimal import Decimal
from django.db import models
import json

class RepasseDetalhado(models.Model):
    """
    Repasse com cálculo baseado na composição detalhada da cobrança
    """
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('efetuado', 'Efetuado'),
        ('cancelado', 'Cancelado'),
    ]

    # Relacionamentos básicos
    proprietario = models.ForeignKey('sisimob.Cliente', on_delete=models.CASCADE)
    cobranca = models.ForeignKey('financeiro.Cobranca', on_delete=models.CASCADE)
    contrato = models.ForeignKey('sisimob.Contrato', on_delete=models.CASCADE)

    # Valores financeiros
    valor_bruto_total = models.DecimalField(
        max_digits=12, decimal_places=2,
        help_text="Valor total da cobrança (o que o inquilino pagou)"
    )
    
    valor_taxa_admin_total = models.DecimalField(
        max_digits=12, decimal_places=2,
        help_text="Total de taxa administrativa descontada"
    )
    
    valor_liquido_repasse = models.DecimalField(
        max_digits=12, decimal_places=2,
        help_text="Valor líquido a ser repassado ao proprietário"
    )
    
    # Detalhamento da composição (JSON)
    composicao_detalhada = models.JSONField(
        default=dict,
        help_text="Detalhamento de como o valor foi composto e calculado"
    )
    
    # Controle de datas
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_prevista = models.DateField()
    data_efetivacao = models.DateField(null=True, blank=True)
    
    # Período de referência
    mes_referencia = models.PositiveSmallIntegerField()
    ano_referencia = models.PositiveSmallIntegerField()
    
    # Status e controle
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')
    observacoes = models.TextField(blank=True, null=True)
    comprovante = models.FileField(upload_to='repasses/comprovantes/', null=True, blank=True)

    class Meta:
        verbose_name = 'Repasse Detalhado'
        verbose_name_plural = 'Repasses Detalhados'
        ordering = ['-data_criacao']

    def __str__(self):
        return f"Repasse {self.id} - {self.proprietario} - R$ {self.valor_liquido_repasse}"

    @classmethod
    def criar_a_partir_de_cobranca(cls, cobranca):
        """
        Cria um repasse baseado na composição detalhada de uma cobrança
        """
        from .cobranca_composicao import ComposicaoCobranca
        
        # Calcular composição
        calculadora = ComposicaoCobranca(
            cobranca.contrato, 
            cobranca.mes_referencia, 
            cobranca.ano_referencia
        )
        composicao = calculadora.calcular_composicao_completa()
        
        # Obter política de repasse para calcular data
        politica = getattr(cobranca.contrato, 'politica_repasse', None)
        
        if politica:
            data_prevista = politica.calcular_data_repasse(cobranca.data_pagamento)
        else:
            # Fallback: 2 dias úteis após pagamento
            from datetime import timedelta
            data_prevista = cobranca.data_pagamento + timedelta(days=2)
        
        # Obter primeiro proprietário
        proprietario = cobranca.contrato.proprietario.first()
        
        # Criar repasse
        repasse = cls.objects.create(
            proprietario=proprietario,
            cobranca=cobranca,
            contrato=cobranca.contrato,
            valor_bruto_total=composicao['valor_total_cobranca'],
            valor_taxa_admin_total=composicao['valor_total_taxa_admin'],
            valor_liquido_repasse=composicao['valor_total_repasse'],
            composicao_detalhada=cls._preparar_composicao_para_json(composicao),
            data_prevista=data_prevista,
            mes_referencia=cobranca.mes_referencia,
            ano_referencia=cobranca.ano_referencia,
            observacoes=f"Repasse automático - {len(composicao['componentes'])} componentes"
        )
        
        return repasse
    
    @staticmethod
    def _preparar_composicao_para_json(composicao):
        """Converte Decimal para float para armazenamento JSON"""
        def converter_decimals(obj):
            if isinstance(obj, dict):
                return {k: converter_decimals(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [converter_decimals(item) for item in obj]
            elif isinstance(obj, Decimal):
                return float(obj)
            return obj
        
        return converter_decimals(composicao)
    
    def get_composicao_legivel(self):
        """Retorna a composição em formato legível"""
        if not self.composicao_detalhada:
            return {}
        
        composicao = self.composicao_detalhada.copy()
        
        # Converter floats de volta para Decimal para cálculos
        def converter_para_decimal(obj):
            if isinstance(obj, dict):
                return {k: converter_para_decimal(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [converter_para_decimal(item) for item in obj]
            elif isinstance(obj, (int, float)):
                return Decimal(str(obj))
            return obj
        
        return converter_para_decimal(composicao)
    
    def gerar_relatorio_repasse(self):
        """
        Gera relatório detalhado do repasse
        """
        composicao = self.get_composicao_legivel()
        
        relatorio = {
            'cabecalho': {
                'repasse_id': self.id,
                'proprietario': str(self.proprietario),
                'periodo': f"{self.mes_referencia:02d}/{self.ano_referencia}",
                'contrato': str(self.contrato),
                'data_criacao': self.data_criacao.strftime('%d/%m/%Y'),
                'data_prevista': self.data_prevista.strftime('%d/%m/%Y'),
                'status': self.get_status_display()
            },
            'resumo_financeiro': {
                'valor_total_cobranca': self.valor_bruto_total,
                'total_taxa_admin': self.valor_taxa_admin_total,
                'valor_liquido_repasse': self.valor_liquido_repasse,
                'percentual_taxa_media': (
                    (self.valor_taxa_admin_total / self.valor_bruto_total * 100) 
                    if self.valor_bruto_total > 0 else Decimal('0')
                )
            },
            'componentes_detalhados': composicao.get('componentes', []),
            'observacoes': self.observacoes or ''
        }
        
        return relatorio
    
    def gerar_descricao_humanizada(self):
        """
        Gera descrição em linguagem natural
        """
        composicao = self.get_composicao_legivel()
        componentes = composicao.get('componentes', [])
        
        linhas = [
            f"💰 REPASSE #{self.id}",
            f"👤 Proprietário: {self.proprietario}",
            f"📅 Período: {self.mes_referencia:02d}/{self.ano_referencia}",
            f"🏠 Contrato: {self.contrato}",
            "",
            "📊 COMPOSIÇÃO DO REPASSE:",
        ]
        
        for comp in componentes:
            valor = Decimal(str(comp.get('valor', 0)))
            valor_fmt = f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            
            if comp.get('tem_incidencia_admin', False):
                taxa = Decimal(str(comp.get('valor_taxa_admin', 0)))
                liquido = Decimal(str(comp.get('valor_liquido_repasse', 0)))
                taxa_fmt = f"R$ {taxa:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                liquido_fmt = f"R$ {liquido:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                
                linhas.append(f"• {comp['descricao']}: {valor_fmt}")
                linhas.append(f"  - Taxa admin: -{taxa_fmt}")
                linhas.append(f"  - Líquido: {liquido_fmt}")
            else:
                linhas.append(f"• {comp['descricao']}: {valor_fmt} (sem taxa)")
        
        linhas.extend([
            "",
            "🎯 RESUMO:",
            f"Valor bruto total: R$ {self.valor_bruto_total:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
            f"Taxa admin total: R$ {self.valor_taxa_admin_total:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
            f"🏆 VALOR LÍQUIDO: R$ {self.valor_liquido_repasse:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
        ])
        
        return "\n".join(linhas)
    
    def efetivar_repasse(self, metodo_pagamento=None, observacoes_efetivacao=None):
        """
        Efetiva o repasse
        """
        if self.status != 'pendente':
            return False
        
        from datetime import date
        
        self.status = 'efetuado'
        self.data_efetivacao = date.today()
        
        if observacoes_efetivacao:
            self.observacoes = f"{self.observacoes or ''}\n\nEfetuado em {date.today().strftime('%d/%m/%Y')}: {observacoes_efetivacao}".strip()
        
        self.save()
        
        # Criar movimento financeiro
        self._criar_movimento_financeiro(metodo_pagamento)
        
        return True
    
    def _criar_movimento_financeiro(self, metodo_pagamento):
        """
        Cria movimento financeiro quando repasse é efetuado
        """
        try:
            from .movimento import MovimentoConta
            
            MovimentoConta.objects.create(
                proprietario=self.proprietario,
                contrato=self.contrato,
                tipo='repasse',
                descricao=f"Repasse {self.mes_referencia:02d}/{self.ano_referencia} - {len(self.composicao_detalhada.get('componentes', []))} componentes",
                valor=self.valor_liquido_repasse,
                data_referencia=date(self.ano_referencia, self.mes_referencia, 1),
                metodo_pagamento=metodo_pagamento,
                detalhes_json=self.composicao_detalhada
            )
        except ImportError:
            # Modelo MovimentoConta não existe ainda
            pass
    
    def pode_ser_cancelado(self):
        """Verifica se o repasse pode ser cancelado"""
        return self.status == 'pendente'
    
    def cancelar_repasse(self, motivo):
        """Cancela o repasse"""
        if not self.pode_ser_cancelado():
            return False
        
        self.status = 'cancelado'
        self.observacoes = f"{self.observacoes or ''}\n\nCancelado: {motivo}".strip()
        self.save()
        
        return True


# Função auxiliar para migrar repasses antigos
def migrar_repasse_antigo_para_detalhado(repasse_antigo):
    """
    Migra um repasse do modelo antigo para o novo modelo detalhado
    """
    from .cobranca_composicao import ComposicaoCobranca
    
    if not repasse_antigo.cobranca:
        return None
    
    cobranca = repasse_antigo.cobranca
    
    # Recalcular composição
    calculadora = ComposicaoCobranca(
        cobranca.contrato,
        cobranca.mes_referencia,
        cobranca.ano_referencia
    )
    composicao = calculadora.calcular_composicao_completa()
    
    # Criar novo repasse
    repasse_novo = RepasseDetalhado.objects.create(
        proprietario=repasse_antigo.proprietario,
        cobranca=cobranca,
        contrato=repasse_antigo.contrato,
        valor_bruto_total=composicao['valor_total_cobranca'],
        valor_taxa_admin_total=composicao['valor_total_taxa_admin'],
        valor_liquido_repasse=composicao['valor_total_repasse'],
        composicao_detalhada=RepasseDetalhado._preparar_composicao_para_json(composicao),
        data_prevista=repasse_antigo.data_prevista,
        data_efetivacao=repasse_antigo.data_efetivacao,
        mes_referencia=repasse_antigo.mes_referencia,
        ano_referencia=repasse_antigo.ano_referencia,
        status=repasse_antigo.status,
        observacoes=f"Migrado do repasse #{repasse_antigo.id}\n{repasse_antigo.observacoes or ''}".strip()
    )
    
    return repasse_novo


# Exemplo de uso:
def exemplo_criar_repasse_a_partir_de_cobranca():
    """
    Exemplo de como criar um repasse quando uma cobrança é paga
    """
    from financeiro.models import Cobranca
    
    # Quando uma cobrança é marcada como paga
    cobranca = Cobranca.objects.get(id=123)
    cobranca.marcar_como_paga()
    
    # Criar repasse automaticamente
    repasse = RepasseDetalhado.criar_a_partir_de_cobranca(cobranca)
    
    # Gerar relatório
    relatorio = repasse.gerar_relatorio_repasse()
    print(json.dumps(relatorio, indent=2, default=str))
    
    # Gerar descrição humanizada
    descricao = repasse.gerar_descricao_humanizada()
    print(descricao)
    
    return repasse