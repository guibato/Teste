from django.db import models
from decimal import Decimal
from .base import TimestampedModel


class Imovel(TimestampedModel):
    """
    Modelo para imóveis
    """
    # Endereço
    cep = models.CharField(max_length=10, verbose_name="CEP")
    endereco = models.CharField(max_length=255, verbose_name="Endereço")
    numero = models.CharField(max_length=10, verbose_name="Número")
    complemento = models.CharField(
        max_length=100, 
        null=True, 
        blank=True, 
        verbose_name="Complemento"
    )
    bairro = models.CharField(
        max_length=100, 
        null=True, 
        blank=True, 
        verbose_name="Bairro"
    )
    cidade = models.CharField(max_length=100, verbose_name="Cidade")
    estado = models.CharField(max_length=2, verbose_name="Estado")

    # Informações de utilities e taxas
    iptu = models.CharField(
        max_length=14, 
        null=True, 
        blank=True, 
        verbose_name="IPTU"
    )
    comgas = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True, 
        verbose_name="Comgás"
    )
    sabesp = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True, 
        verbose_name="Sabesp"
    )
    enel = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True, 
        verbose_name="Enel"
    )

    class Meta:
        verbose_name = "Imóvel"
        verbose_name_plural = "Imóveis"
        ordering = ['endereco', 'numero']

    def __str__(self):
        """Representação string do imóvel"""
        if self.complemento:
            return f"{self.endereco}, {self.numero} - {self.complemento}"
        return f"{self.endereco}, {self.numero}"

    @property
    def endereco_resumido(self):
        """Retorna endereço resumido para listagens"""
        partes = [self.endereco, self.numero]
        if self.bairro:
            partes.append(self.bairro)
        return ", ".join(partes)

    @property
    def endereco_completo(self):
        """
        Retorna o endereço no formato: endereço, número - complemento
        """
        partes = []
        
        # Endereço base (sempre presente)
        if self.endereco:
            partes.append(self.endereco)
        
        # Adicionar número se existir
        if self.numero:
            partes.append(str(self.numero))
        
        # Juntar endereço e número com vírgula
        endereco_base = ", ".join(partes) if partes else ""
        
        # Adicionar complemento com hífen se existir
        if self.complemento:
            return f"{endereco_base} - {self.complemento}"
        
        return endereco_base

    @property
    def endereco_com_bairro(self):
        """Retorna endereço incluindo bairro e cidade"""
        endereco = self.endereco_completo
        if self.bairro:
            endereco += f", {self.bairro}"
        if self.cidade and self.estado:
            endereco += f" - {self.cidade}/{self.estado}"
        return endereco

    @property
    def total_utilities(self):
        """Calcula o total de utilities (Comgás + Sabesp + Enel)"""
        total = Decimal('0.00')
        
        if self.comgas:
            total += self.comgas
        if self.sabesp:
            total += self.sabesp
        if self.enel:
            total += self.enel
            
        return total

    def get_contratos_ativos(self):
        """Retorna contratos ativos para este imóvel"""
        return self.contratos_imovel.filter(ativo=True)

    def get_contrato_atual(self):
        """Retorna o contrato ativo atual (se houver)"""
        contratos_ativos = self.get_contratos_ativos()
        return contratos_ativos.first() if contratos_ativos.exists() else None

    @property
    def status_ocupacao(self):
        """Retorna o status de ocupação do imóvel"""
        contrato_atual = self.get_contrato_atual()
        
        if contrato_atual:
            from datetime import date
            hoje = date.today()
            
            if contrato_atual.data_inicio <= hoje <= contrato_atual.data_fim:
                return 'ocupado'
            elif hoje < contrato_atual.data_inicio:
                return 'reservado'
            else:
                return 'disponivel'
        
        return 'disponivel'

    @property
    def status_ocupacao_display(self):
        """Retorna o status de ocupação formatado para exibição"""
        status = self.status_ocupacao
        status_map = {
            'ocupado': 'Ocupado',
            'reservado': 'Reservado',
            'disponivel': 'Disponível'
        }
        return status_map.get(status, 'Indisponível')