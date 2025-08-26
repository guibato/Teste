from django.db import models
from django.core.exceptions import ValidationError
from .base import TimestampedModel


class Cliente(TimestampedModel):
    """
    Modelo para clientes (proprietários, inquilinos, fiadores, etc.)
    """
    TIPO_CLIENTE_CHOICES = [
        ('Proprietario', 'Proprietário(a)'),
        ('Inquilino', 'Inquilino(a)'),
        ('Anuente', 'Anuente'),
        ('Fiador(a)', 'Fiador(a)'),
        ('Representante Legal', 'Representante Legal'),
    ]
    
    MODALIDADE_PIX_CHOICES = [
        ('cpf', 'CPF'),
        ('email', 'E-mail'),
        ('telefone', 'Telefone'),
        ('aleatorio', 'Chave Aleatória'),
    ]
    
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
    
    TIPO_PESSOA_CHOICES = [
        ('F', 'Pessoa Física'),
        ('J', 'Pessoa Jurídica'),
    ]

    # Dados básicos
    tipo_pessoa = models.CharField(
        max_length=1, 
        choices=TIPO_PESSOA_CHOICES, 
        default='F', 
        verbose_name='Tipo de Pessoa'
    )
    tipo = models.CharField(
        max_length=20, 
        choices=TIPO_CLIENTE_CHOICES, 
        verbose_name="Tipo"
    )
    nome = models.CharField(max_length=100, verbose_name="Nome")

    # Dados PJ
    razao_social = models.CharField(
        max_length=255, 
        null=True, 
        blank=True, 
        verbose_name="Razão Social"
    )
    nome_fantasia = models.CharField(
        max_length=255, 
        null=True, 
        blank=True, 
        verbose_name="Nome Fantasia"
    )
    cnpj = models.CharField(
        max_length=18, 
        null=True, 
        blank=True, 
        verbose_name="CNPJ"
    )
    representante_legal = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={
            'tipo_pessoa': 'F',
            'tipo': 'Representante Legal',
        },
        related_name="clientes_representados",
        verbose_name="Representante Legal"
    )

    # Dados PF
    CPF = models.CharField(
        max_length=14, 
        null=True, 
        blank=True, 
        verbose_name="CPF"
    )
    rg_rne = models.CharField(
        max_length=20, 
        null=True, 
        blank=True, 
        unique=True, 
        verbose_name="RG/RNE"
    )
    nacionalidade = models.CharField(max_length=100, null=True, blank=True)
    profissao = models.CharField(max_length=100, null=True, blank=True)
    estado_civil = models.CharField(
        max_length=20, 
        choices=ESTADO_CIVIL_CHOICES, 
        null=True, 
        blank=True
    )
    regime_casamento = models.CharField(
        max_length=30, 
        choices=REGIME_CASAMENTO_CHOICES, 
        null=True, 
        blank=True
    )
    anuente = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='anuentes', 
        verbose_name="Anuente"
    )

    # Contato
    telefone = models.CharField(max_length=15, null=True, blank=True)
    celular = models.CharField(max_length=15, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)

    # Dados bancários
    pix_modalidade = models.CharField(
        max_length=20, 
        choices=MODALIDADE_PIX_CHOICES, 
        null=True, 
        blank=True
    )
    chave_pix = models.CharField(max_length=100, null=True, blank=True)
    banco = models.CharField(max_length=100, null=True, blank=True)
    agencia = models.CharField(max_length=100, null=True, blank=True)
    conta_corrente = models.CharField(max_length=100, null=True, blank=True)
    poupanca = models.CharField(max_length=100, null=True, blank=True)

    # Endereço
    cep = models.CharField(max_length=10)
    endereco = models.CharField(max_length=255)
    numero = models.CharField(max_length=10)
    complemento = models.CharField(max_length=100, null=True, blank=True)
    bairro = models.CharField(max_length=100, null=True, blank=True)
    cidade = models.CharField(max_length=100)
    estado = models.CharField(max_length=2)

    # Outros
    documento = models.CharField(max_length=100, null=True, blank=True)
    asaas_id = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ['nome']

    def __str__(self):
        if self.tipo_pessoa == 'J' and self.razao_social:
            return self.razao_social
        return self.nome

    def clean(self):
        """Validações customizadas"""
        if self.rg_rne and Cliente.objects.filter(rg_rne=self.rg_rne).exclude(pk=self.pk).exists():
            raise ValidationError({'rg_rne': 'Este RG/RNE já está cadastrado.'})

    def save(self, *args, **kwargs):
        """Override do save para integração com Asaas"""
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Integração com Asaas (importar aqui para evitar imports circulares)
        from financeiro.utils.integracao_asaas import cadastrar_cliente_no_asaas, atualizar_cliente_no_asaas
        
        if self.asaas_id:
            atualizado = atualizar_cliente_no_asaas(self)
            if not atualizado:
                print(f"Erro ao atualizar cliente {self.nome} no Asaas")
        else:
            resposta = cadastrar_cliente_no_asaas(self)
            if resposta:
                self.asaas_id = resposta
                super().save(update_fields=['asaas_id'])
            else:
                print(f"Erro ao cadastrar cliente {self.nome} no Asaas")

    @property
    def primeiro_nome(self):
        """Retorna o primeiro nome do cliente"""
        return self.nome.split()[0] if self.nome else ''

    @property
    def nome_exibicao(self):
        """Retorna o nome para exibição (fantasia para PJ, nome para PF)"""
        if self.tipo_pessoa == 'J':
            return self.nome_fantasia or self.razao_social or self.nome
        return self.nome

    @property
    def documento_principal(self):
        """Retorna o documento principal (CPF para PF, CNPJ para PJ)"""
        if self.tipo_pessoa == 'J':
            return self.cnpj
        return self.CPF

    @property
    def endereco_completo(self):
        """Retorna o endereço completo formatado"""
        partes = []
        
        if self.endereco:
            partes.append(self.endereco)
        if self.numero:
            partes.append(self.numero)
        if self.complemento:
            partes.append(f"- {self.complemento}")
        if self.bairro:
            partes.append(f"- {self.bairro}")
        if self.cidade and self.estado:
            partes.append(f"- {self.cidade}/{self.estado}")
        
        return ", ".join(partes)