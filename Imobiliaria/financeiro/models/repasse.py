# financeiro/models/repasse.py
from django.db import models
from django.utils import timezone
from decimal import Decimal
from datetime import date
import calendar


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
    cobranca = models.ForeignKey('financeiro.Cobranca', on_delete=models.SET_NULL, null=True, blank=True, related_name='repasses')
    contrato = models.ForeignKey('sisimob.Contrato', on_delete=models.CASCADE, related_name='repasses')

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


class PoliticaRepasse(models.Model):
    PERIODICIDADE_CHOICES = [
        ('diaria', 'Diária'),
        ('semanal', 'Semanal'),
        ('quinzenal', 'Quinzenal'),
        ('mensal', 'Mensal'),
    ]
    DIA_SEMANA_CHOICES = [(i, d) for i, d in enumerate([
        'Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo'
    ], start=1)]

    nome = models.CharField(max_length=100)
    ativa = models.BooleanField(default=True)
    periodicidade = models.CharField(max_length=20, choices=PERIODICIDADE_CHOICES, default='mensal')
    dia_mes = models.PositiveSmallIntegerField(null=True, blank=True)
    dia_semana = models.PositiveSmallIntegerField(choices=DIA_SEMANA_CHOICES, null=True, blank=True)
    dias_apos_recebimento = models.PositiveSmallIntegerField(default=2)
    percentual_adiantamento = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    taxa_adiantamento = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    valor_minimo_repasse = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Política de Repasse'
        verbose_name_plural = 'Políticas de Repasse'
        ordering = ['-ativa', 'nome']

    def __str__(self):
        return f"{self.nome} - {'Ativa' if self.ativa else 'Inativa'}"

    def calcular_proxima_data_repasse(self, data_referencia=None):
        if not data_referencia:
            data_referencia = date.today()

        if self.periodicidade == 'mensal' and self.dia_mes:
            ano, mes = data_referencia.year, data_referencia.month
            if data_referencia.day > self.dia_mes:
                mes += 1
                if mes > 12:
                    mes = 1
                    ano += 1
            ultimo_dia = calendar.monthrange(ano, mes)[1]
            dia = min(self.dia_mes, ultimo_dia)
            return date(ano, mes, dia)

        elif self.periodicidade == 'semanal' and self.dia_semana:
            dias_ate = (self.dia_semana - data_referencia.isoweekday()) % 7
            if dias_ate == 0:
                dias_ate = 7
            return data_referencia + timezone.timedelta(days=dias_ate)

        elif self.periodicidade == 'quinzenal':
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

        elif self.periodicidade == 'diaria':
            return self._proximo_dia_util(data_referencia)

    def _proximo_dia_util(self, data_referencia):
        dias = 1
        proxima_data = data_referencia + timezone.timedelta(days=dias)
        while proxima_data.weekday() >= 5:
            dias += 1
            proxima_data = data_referencia + timezone.timedelta(days=dias)
        return proxima_data


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
        if self.status not in ['agendado', 'falha']:
            return False
        self.status = 'cancelado'
        if motivo:
            self.detalhes_processamento = (self.detalhes_processamento or '') + f"\nCancelado: {motivo}"
        self.save()
        return True
