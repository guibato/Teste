from django.db import models
from django.utils import timezone
from decimal import Decimal
from datetime import date
from sisimob.models import Contrato


class Repasse(models.Model):
    """
    Modelo para registrar os repasses financeiros aos proprietários
    """
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
    
    proprietario = models.ForeignKey('Cliente', on_delete=models.CASCADE, related_name='repasses_recebidos')
    cobranca = models.ForeignKey('Cobranca', on_delete=models.SET_NULL, null=True, blank=True, related_name='repasses')
    contrato = models.ForeignKey('Contrato', on_delete=models.CASCADE, related_name='repasses')
    
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
        """Retorna o valor líquido do repasse (valor - descontos - taxa)"""
        return self.valor - self.valor_desconto - self.valor_taxa_admin
    
    @property
    def valor_formatado(self):
        """Retorna o valor formatado como moeda"""
        return f"R$ {self.valor:.2f}".replace('.', ',')
    
    @property
    def valor_liquido_formatado(self):
        """Retorna o valor líquido formatado como moeda"""
        return f"R$ {self.valor_liquido:.2f}".replace('.', ',')
    
    @property
    def esta_atrasado(self):
        """Verifica se o repasse está atrasado"""
        return self.status == 'pendente' and self.data_prevista < date.today()
    
    @property
    def dias_atraso(self):
        """Calcula quantos dias o repasse está atrasado"""
        if not self.esta_atrasado:
            return 0
        return (date.today() - self.data_prevista).days
    
    def efetivar_repasse(self, metodo_pagamento=None, observacoes=None):
        """
        Efetiva o repasse, atualizando o status e registrando a data
        """
        if self.status != 'pendente':
            return False
        
        self.status = 'efetuado'
        self.data_efetivacao = date.today()
        
        if metodo_pagamento:
            self.metodo_pagamento = metodo_pagamento
            
        if observacoes:
            self.observacoes = observacoes
            
        self.save()
        
        # Atualiza o status da cobrança relacionada
        if self.cobranca:
            self.cobranca.status_repasse = 'repassado'
            self.cobranca.data_repasse = self.data_efetivacao
            self.cobranca.save(update_fields=['status_repasse', 'data_repasse'])
        
        # Registra o movimento de repasse
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
        """
        Cancela um repasse pendente
        """
        if self.status != 'pendente':
            return False
        
        self.status = 'cancelado'
        
        if motivo:
            self.observacoes = (self.observacoes or '') + f"\nCancelado: {motivo}"
            
        self.save()
        
        # Atualiza o status da cobrança relacionada
        if self.cobranca:
            self.cobranca.status_repasse = 'cancelado'
            self.cobranca.save(update_fields=['status_repasse'])
        
        return True


class PoliticaRepasse(models.Model):
    """
    Modelo para configuração de políticas de repasse
    """
    PERIODICIDADE_CHOICES = [
        ('diaria', 'Diária'),
        ('semanal', 'Semanal'),
        ('quinzenal', 'Quinzenal'),
        ('mensal', 'Mensal'),
    ]
    
    DIA_SEMANA_CHOICES = [
        (1, 'Segunda-feira'),
        (2, 'Terça-feira'),
        (3, 'Quarta-feira'),
        (4, 'Quinta-feira'),
        (5, 'Sexta-feira'),
        (6, 'Sábado'),
        (7, 'Domingo'),
    ]

    nome = models.CharField(max_length=100)
    ativa = models.BooleanField(default=True)
    
    periodicidade = models.CharField(max_length=20, choices=PERIODICIDADE_CHOICES, default='mensal')
    dia_mes = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Dia do mês para repasses mensais")
    dia_semana = models.PositiveSmallIntegerField(choices=DIA_SEMANA_CHOICES, null=True, blank=True, help_text="Dia da semana para repasses semanais")
    
    dias_apos_recebimento = models.PositiveSmallIntegerField(default=2, help_text="Dias úteis após recebimento para efetuar o repasse")
    percentual_adiantamento = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'), help_text="Percentual para adiantamento de repasse")
    
    taxa_adiantamento = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'), help_text="Taxa (%) cobrada por adiantamento")
    valor_minimo_repasse = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), help_text="Valor mínimo para efetuar um repasse")
    
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Política de Repasse'
        verbose_name_plural = 'Políticas de Repasse'
        ordering = ['-ativa', 'nome']
    
    def __str__(self):
        return f"{self.nome} - {'Ativa' if self.ativa else 'Inativa'}"
    
    def calcular_proxima_data_repasse(self, data_referencia=None):
        """
        Calcula a próxima data de repasse com base na política
        """
        if not data_referencia:
            data_referencia = date.today()
            
        proxima_data = None
        
        if self.periodicidade == 'mensal' and self.dia_mes:
            # Determina o próximo dia do mês válido
            ano, mes = data_referencia.year, data_referencia.month
            
            # Se já passou do dia no mês atual, avança para o próximo mês
            if data_referencia.day > self.dia_mes:
                mes += 1
                if mes > 12:
                    mes = 1
                    ano += 1
            
            # Tenta criar a data (ajusta para o último dia do mês se necessário)
            import calendar
            ultimo_dia = calendar.monthrange(ano, mes)[1]
            dia = min(self.dia_mes, ultimo_dia)
            
            proxima_data = date(ano, mes, dia)
        
        elif self.periodicidade == 'semanal' and self.dia_semana:
            # Calcula dias até o próximo dia da semana especificado
            dias_ate = (self.dia_semana - data_referencia.isoweekday()) % 7
            if dias_ate == 0:  # Se for hoje, avança uma semana
                dias_ate = 7
                
            proxima_data = data_referencia + timezone.timedelta(days=dias_ate)
        
        elif self.periodicidade == 'quinzenal':
            # Implementa lógica para repasse quinzenal (dias 15 e último dia do mês)
            ano, mes = data_referencia.year, data_referencia.month
            
            # Verifica se estamos antes ou depois do dia 15
            if data_referencia.day < 15:
                proxima_data = date(ano, mes, 15)
            else:
                # Último dia do mês atual
                import calendar
                ultimo_dia = calendar.monthrange(ano, mes)[1]
                proxima_data = date(ano, mes, ultimo_dia)
                
                # Se já passou do último dia, avança para o dia 15 do próximo mês
                if data_referencia.day >= ultimo_dia:
                    mes += 1
                    if mes > 12:
                        mes = 1
                        ano += 1
                    proxima_data = date(ano, mes, 15)
        
        elif self.periodicidade == 'diaria':
            # Para repasses diários, escolhe o próximo dia útil
            proxima_data = self._proximo_dia_util(data_referencia)
        
        return proxima_data
    
    def _proximo_dia_util(self, data_referencia):
        """Helper para encontrar o próximo dia útil (exclui sábados e domingos)"""
        dias = 1  # Começa com o dia seguinte
        proxima_data = data_referencia + timezone.timedelta(days=dias)
        
        # Avança até encontrar um dia útil (não é sábado nem domingo)
        while proxima_data.weekday() >= 5:  # 5=sábado, 6=domingo
            dias += 1
            proxima_data = data_referencia + timezone.timedelta(days=dias)
            
        return proxima_data


class AgendamentoRepasse(models.Model):
    """
    Modelo para agendar repasses futuros que ainda não foram processados
    """
    STATUS_CHOICES = [
        ('agendado', 'Agendado'),
        ('processando', 'Processando'),
        ('concluido', 'Concluído'),
        ('falha', 'Falha'),
        ('cancelado', 'Cancelado'),
    ]
    
    proprietario = models.ForeignKey('Cliente', on_delete=models.CASCADE, related_name='agendamentos_repasse')
    contrato = models.ForeignKey('Contrato', on_delete=models.CASCADE, related_name='agendamentos_repasse')
    politica = models.ForeignKey(PoliticaRepasse, on_delete=models.SET_NULL, null=True, blank=True)
    
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
    
    def processar(self):
        """
        Processa o agendamento e cria o repasse
        """
        if self.status != 'agendado':
            return False
        
        self.status = 'processando'
        self.save(update_fields=['status'])
        
        try:
            # Tenta encontrar uma cobrança correspondente para vincular ao repasse
            from .cobranca import Cobranca
            cobranca = Cobranca.objects.filter(
                contrato=self.contrato,
                mes_referencia=self.mes_referencia,
                ano_referencia=self.ano_referencia,
                status='paga'
            ).first()
            
            # Cria o repasse
            repasse = Repasse.objects.create(
                proprietario=self.proprietario,
                cobranca=cobranca,
                contrato=self.contrato,
                valor=self.valor_previsto,
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
            return False
    
    def cancelar(self, motivo=None):
        """
        Cancela um agendamento pendente
        """
        if self.status not in ['agendado', 'falha']:
            return False
        
        self.status = 'cancelado'
        
        if motivo:
            self.detalhes_processamento = (self.detalhes_processamento or '') + f"\nCancelado: {motivo}"
            
        self.save()
        return True