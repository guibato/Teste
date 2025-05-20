# financeiro/models/lembrete.py
from django.db import models
from django.utils import timezone


class LembreteEnviado(models.Model):
    """
    Histórico de lembretes de cobrança enviados.
    Permite controle detalhado por tipo, data e status do envio.
    """
    CANAIS = [
        ('whatsapp', 'WhatsApp'),
        ('email', 'E-mail'),
        ('sms', 'SMS'),
    ]
    STATUS = [
        ('enviado', 'Enviado'),
        ('falha', 'Falha'),
    ]

    cobranca = models.ForeignKey('financeiro.Cobranca', on_delete=models.CASCADE, related_name='lembretes_enviados')
    data_envio = models.DateTimeField(auto_now_add=True)
    tipo = models.CharField(max_length=20, choices=CANAIS)
    dias_antes_vencimento = models.IntegerField(help_text="Quantos dias antes do vencimento este lembrete foi enviado")
    status = models.CharField(max_length=20, choices=STATUS, default='enviado')
    observacao = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Lembrete de Cobrança Enviado"
        verbose_name_plural = "Lembretes de Cobrança Enviados"
        ordering = ['-data_envio']
        indexes = [
            models.Index(fields=['cobranca', 'dias_antes_vencimento']),
            models.Index(fields=['tipo', 'status']),
        ]

    def __str__(self):
        return f"{self.tipo.title()} - {self.dias_antes_vencimento}d antes - {self.cobranca}"
