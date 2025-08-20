# financeiro/models/conta_corrente.py
from django.db import models
from django.utils import timezone
from django.db.models import Sum, Q
from decimal import Decimal
from datetime import date, datetime, timedelta
import calendar
import json


class ContaCorrenteProprietario(models.Model):
    """
    Conta corrente centralizada do proprietário para controle financeiro completo
    """
    proprietario = models.OneToOneField(
        'sisimob.Cliente', 
        on_delete=models.CASCADE, 
        related_name='conta_corrente'
    )
    
    saldo_atual = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Saldo atual da conta corrente"
    )
    
    saldo_bloqueado = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Valor bloqueado para pagamentos futuros"
    )
    
    data_abertura = models.DateField(auto_now_add=True)
    data_ultima_atualizacao = models.DateTimeField(auto_now=True)
    
    ativa = models.BooleanField(default=True)
    observacoes = models.TextField(blank=True, null=True)
    
    # Configurações de envio de extrato
    enviar_extrato_automatico = models.BooleanField(default=True)
    dia_envio_extrato = models.PositiveSmallIntegerField(
        default=5,
        help_text="Dia do mês para enviar o extrato (1-28)"
    )
    email_extrato = models.EmailField(blank=True, null=True)
    whatsapp_extrato = models.CharField(max_length=20, blank=True, null=True)
    
    class Meta:
        verbose_name = "Conta Corrente de Proprietário"
        verbose_name_plural = "Contas Correntes de Proprietários"
        ordering = ['proprietario__nome']
    
    def __str__(self):
        return f"CC {self.proprietario.nome} - Saldo: R$ {self.saldo_atual:,.2f}"
    
    @property
    def saldo_disponivel(self):
        """Saldo disponível (atual - bloqueado)"""
        return self.saldo_atual - self.saldo_bloqueado
    
    def get_saldo_em_data(self, data_consulta):
        """Calcula o saldo em uma data específica"""
        movimentos = self.movimentos.filter(
            data_movimento__lte=data_consulta
        ).aggregate(
            total_creditos=Sum('valor', filter=Q(tipo='credito')),
            total_debitos=Sum('valor', filter=Q(tipo='debito'))
        )
        
        creditos = movimentos['total_creditos'] or Decimal('0.00')
        debitos = movimentos['total_debitos'] or Decimal('0.00')
        
        return creditos - debitos
    
    def recalcular_saldo(self):
        """Recalcula o saldo baseado em todos os movimentos"""
        movimentos = self.movimentos.aggregate(
            total_creditos=Sum('valor', filter=Q(tipo='credito')),
            total_debitos=Sum('valor', filter=Q(tipo='debito'))
        )
        
        creditos = movimentos['total_creditos'] or Decimal('0.00')
        debitos = movimentos['total_debitos'] or Decimal('0.00')
        
        self.saldo_atual = creditos - debitos
        self.save(update_fields=['saldo_atual'])
        
        return self.saldo_atual


class MovimentoContaCorrente(models.Model):
    """
    Movimento individual na conta corrente do proprietário
    """
    TIPO_MOVIMENTO = [
        ('credito', 'Crédito'),
        ('debito', 'Débito'),
    ]
    
    CATEGORIA_MOVIMENTO = [
        ('aluguel', 'Aluguel'),
        ('despesa_inquilino', 'Despesa Paga pelo Inquilino'),
        ('despesa_proprietario', 'Despesa Paga pelo Proprietário'),
        ('taxa_admin', 'Taxa de Administração'),
        ('repasse', 'Repasse Efetuado'),
        ('ajuste', 'Ajuste Manual'),
        ('multa', 'Multa/Juros'),
        ('desconto', 'Desconto'),
        ('outros', 'Outros'),
    ]
    
    conta = models.ForeignKey(
        ContaCorrenteProprietario,
        on_delete=models.CASCADE,
        related_name='movimentos'
    )
    
    tipo = models.CharField(max_length=10, choices=TIPO_MOVIMENTO)
    categoria = models.CharField(max_length=30, choices=CATEGORIA_MOVIMENTO)
    
    # Valores
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    saldo_anterior = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        help_text="Saldo antes deste movimento"
    )
    saldo_posterior = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        help_text="Saldo após este movimento"
    )
    
    # Descrição e referências
    descricao = models.CharField(max_length=255)
    descricao_detalhada = models.TextField(blank=True, null=True)
    
    # Referências aos objetos relacionados
    contrato = models.ForeignKey(
        'sisimob.Contrato', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    cobranca = models.ForeignKey(
        'financeiro.Cobranca', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    despesa = models.ForeignKey(
        'financeiro.Despesa', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    repasse = models.ForeignKey(
        'financeiro.Repasse', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    
    # Período de referência
    mes_referencia = models.PositiveSmallIntegerField(null=True, blank=True)
    ano_referencia = models.PositiveSmallIntegerField(null=True, blank=True)
    
    # Datas
    data_movimento = models.DateField()
    data_criacao = models.DateTimeField(auto_now_add=True)
    
    # Controle
    processado = models.BooleanField(default=False)
    conciliado = models.BooleanField(default=False)
    observacoes = models.TextField(blank=True, null=True)
    
    # Metadados JSON para informações extras
    metadados = models.JSONField(default=dict, blank=True)
    
    class Meta:
        verbose_name = "Movimento de Conta Corrente"
        verbose_name_plural = "Movimentos de Conta Corrente"
        ordering = ['-data_movimento', '-data_criacao']
        indexes = [
            models.Index(fields=['conta', 'data_movimento']),
            models.Index(fields=['tipo', 'categoria']),
            models.Index(fields=['mes_referencia', 'ano_referencia']),
        ]
    
    def __str__(self):
        sinal = "+" if self.tipo == 'credito' else "-"
        return f"{self.data_movimento} {sinal}R$ {self.valor:,.2f} - {self.descricao}"
    
    @property
    def valor_formatado(self):
        sinal = "+" if self.tipo == 'credito' else "-"
        return f"{sinal}R$ {self.valor:,.2f}".replace('.', ',')
    
    @property
    def periodo_referencia(self):
        if self.mes_referencia and self.ano_referencia:
            return f"{self.mes_referencia:02d}/{self.ano_referencia}"
        return "-"
    
    def save(self, *args, **kwargs):
        """Atualiza saldos ao salvar"""
        if not self.pk:  # Novo movimento
            # Captura saldo anterior
            self.saldo_anterior = self.conta.saldo_atual
            
            # Calcula novo saldo
            if self.tipo == 'credito':
                self.saldo_posterior = self.saldo_anterior + self.valor
            else:
                self.saldo_posterior = self.saldo_anterior - self.valor
            
            # Atualiza saldo da conta
            self.conta.saldo_atual = self.saldo_posterior
            self.conta.save(update_fields=['saldo_atual'])
        
        super().save(*args, **kwargs)


class ExtratoMensal(models.Model):
    """
    Extrato mensal consolidado para envio ao proprietário
    """
    STATUS_CHOICES = [
        ('rascunho', 'Rascunho'),
        ('finalizado', 'Finalizado'),
        ('enviado', 'Enviado'),
        ('visualizado', 'Visualizado'),
    ]
    
    conta = models.ForeignKey(
        ContaCorrenteProprietario,
        on_delete=models.CASCADE,
        related_name='extratos'
    )
    
    mes_referencia = models.PositiveSmallIntegerField()
    ano_referencia = models.PositiveSmallIntegerField()
    
    # Período do extrato
    data_inicio = models.DateField()
    data_fim = models.DateField()
    
    # Saldos
    saldo_anterior = models.DecimalField(max_digits=12, decimal_places=2)
    saldo_final = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Totalizadores
    total_creditos = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    total_debitos = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    total_repasses = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    
    # Detalhamento por categoria (JSON)
    resumo_por_categoria = models.JSONField(default=dict)
    resumo_por_contrato = models.JSONField(default=dict)
    
    # Controle
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='rascunho'
    )
    
    data_geracao = models.DateTimeField(auto_now_add=True)
    data_envio = models.DateTimeField(null=True, blank=True)
    data_visualizacao = models.DateTimeField(null=True, blank=True)
    
    # Arquivo PDF gerado
    arquivo_pdf = models.FileField(
        upload_to='extratos/%Y/%m/', 
        null=True, 
        blank=True
    )
    
    # Hash para link único
    hash_acesso = models.CharField(
        max_length=64, 
        unique=True, 
        null=True, 
        blank=True
    )
    
    observacoes = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name = "Extrato Mensal"
        verbose_name_plural = "Extratos Mensais"
        ordering = ['-ano_referencia', '-mes_referencia']
        unique_together = [('conta', 'mes_referencia', 'ano_referencia')]
    
    def __str__(self):
        return f"Extrato {self.conta.proprietario.nome} - {self.mes_referencia:02d}/{self.ano_referencia}"
    
    @property
    def periodo_formatado(self):
        meses = {
            1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
            5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
            9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
        }
        return f"{meses[self.mes_referencia]}/{self.ano_referencia}"
    
    def gerar_extrato(self):
        """Gera o extrato baseado nos movimentos do período"""
        # Define período
        self.data_inicio = date(self.ano_referencia, self.mes_referencia, 1)
        ultimo_dia = calendar.monthrange(self.ano_referencia, self.mes_referencia)[1]
        self.data_fim = date(self.ano_referencia, self.mes_referencia, ultimo_dia)
        
        # Saldo anterior (último dia do mês anterior)
        data_saldo_anterior = self.data_inicio - timedelta(days=1)
        self.saldo_anterior = self.conta.get_saldo_em_data(data_saldo_anterior)
        
        # Buscar movimentos do período
        movimentos = MovimentoContaCorrente.objects.filter(
            conta=self.conta,
            data_movimento__gte=self.data_inicio,
            data_movimento__lte=self.data_fim
        ).order_by('data_movimento', 'data_criacao')
        
        # Calcular totalizadores
        self.total_creditos = Decimal('0.00')
        self.total_debitos = Decimal('0.00')
        self.total_repasses = Decimal('0.00')
        
        resumo_categoria = {}
        resumo_contrato = {}
        
        for mov in movimentos:
            if mov.tipo == 'credito':
                self.total_creditos += mov.valor
            else:
                self.total_debitos += mov.valor
            
            if mov.categoria == 'repasse':
                self.total_repasses += mov.valor
            
            # Resumo por categoria
            if mov.categoria not in resumo_categoria:
                resumo_categoria[mov.categoria] = {
                    'creditos': Decimal('0.00'),
                    'debitos': Decimal('0.00'),
                    'quantidade': 0
                }
            
            if mov.tipo == 'credito':
                resumo_categoria[mov.categoria]['creditos'] += mov.valor
            else:
                resumo_categoria[mov.categoria]['debitos'] += mov.valor
            resumo_categoria[mov.categoria]['quantidade'] += 1
            
            # Resumo por contrato
            if mov.contrato:
                contrato_key = str(mov.contrato.id)
                if contrato_key not in resumo_contrato:
                    resumo_contrato[contrato_key] = {
                        'imovel': str(mov.contrato.imovel),
                        'inquilino': str(mov.contrato.inquilino.first()) if mov.contrato.inquilino.exists() else '-',
                        'creditos': Decimal('0.00'),
                        'debitos': Decimal('0.00'),
                        'movimentos': []
                    }
                
                if mov.tipo == 'credito':
                    resumo_contrato[contrato_key]['creditos'] += mov.valor
                else:
                    resumo_contrato[contrato_key]['debitos'] += mov.valor
                
                resumo_contrato[contrato_key]['movimentos'].append({
                    'data': mov.data_movimento.strftime('%d/%m'),
                    'descricao': mov.descricao,
                    'valor': float(mov.valor),
                    'tipo': mov.tipo
                })
        
        # Converter Decimal para float para JSON
        self.resumo_por_categoria = {
            k: {
                'creditos': float(v['creditos']),
                'debitos': float(v['debitos']),
                'quantidade': v['quantidade']
            } for k, v in resumo_categoria.items()
        }
        
        self.resumo_por_contrato = {
            k: {
                'imovel': v['imovel'],
                'inquilino': v['inquilino'],
                'creditos': float(v['creditos']),
                'debitos': float(v['debitos']),
                'movimentos': v['movimentos']
            } for k, v in resumo_contrato.items()
        }
        
        # Saldo final
        self.saldo_final = self.saldo_anterior + self.total_creditos - self.total_debitos
        
        # Gerar hash único
        import hashlib
        hash_str = f"{self.conta.id}{self.mes_referencia}{self.ano_referencia}{timezone.now()}"
        self.hash_acesso = hashlib.sha256(hash_str.encode()).hexdigest()
        
        self.status = 'finalizado'
        self.save()
        
        return self
    
    def get_movimentos_detalhados(self):
        """Retorna os movimentos do período formatados"""
        movimentos = MovimentoContaCorrente.objects.filter(
            conta=self.conta,
            data_movimento__gte=self.data_inicio,
            data_movimento__lte=self.data_fim
        ).order_by('data_movimento', 'data_criacao')
        
        return movimentos
    
    def gerar_html_extrato(self):
        """Gera HTML do extrato para visualização/PDF"""
        movimentos = self.get_movimentos_detalhados()
        
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .header {{ background: #2c3e50; color: white; padding: 20px; }}
                .info-box {{ background: #ecf0f1; padding: 15px; margin: 10px 0; }}
                table {{ width: 100%; border-collapse: collapse; }}
                th {{ background: #34495e; color: white; padding: 10px; }}
                td {{ padding: 8px; border-bottom: 1px solid #ddd; }}
                .credito {{ color: #27ae60; font-weight: bold; }}
                .debito {{ color: #e74c3c; font-weight: bold; }}
                .saldo-final {{ font-size: 1.5em; font-weight: bold; }}
                .resumo {{ margin-top: 30px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Extrato Mensal - {self.periodo_formatado}</h1>
                <p>Proprietário: {self.conta.proprietario.nome}</p>
            </div>
            
            <div class="info-box">
                <h3>Resumo do Período</h3>
                <p><strong>Período:</strong> {self.data_inicio.strftime('%d/%m/%Y')} a {self.data_fim.strftime('%d/%m/%Y')}</p>
                <p><strong>Saldo Anterior:</strong> R$ {self.saldo_anterior:,.2f}</p>
                <p class="credito">Total de Créditos: R$ {self.total_creditos:,.2f}</p>
                <p class="debito">Total de Débitos: R$ {self.total_debitos:,.2f}</p>
                <p class="saldo-final">Saldo Final: R$ {self.saldo_final:,.2f}</p>
            </div>
            
            <h3>Movimentação Detalhada</h3>
            <table>
                <thead>
                    <tr>
                        <th>Data</th>
                        <th>Descrição</th>
                        <th>Contrato/Imóvel</th>
                        <th>Categoria</th>
                        <th>Valor</th>
                        <th>Saldo</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td colspan="5"><strong>Saldo Anterior</strong></td>
                        <td><strong>R$ {self.saldo_anterior:,.2f}</strong></td>
                    </tr>
        """
        
        for mov in movimentos:
            classe = 'credito' if mov.tipo == 'credito' else 'debito'
            imovel = str(mov.contrato.imovel) if mov.contrato else '-'
            
            html += f"""
                    <tr>
                        <td>{mov.data_movimento.strftime('%d/%m')}</td>
                        <td>{mov.descricao}</td>
                        <td>{imovel}</td>
                        <td>{mov.get_categoria_display()}</td>
                        <td class="{classe}">{mov.valor_formatado}</td>
                        <td>R$ {mov.saldo_posterior:,.2f}</td>
                    </tr>
            """
        
        html += f"""
                    <tr>
                        <td colspan="5"><strong>Saldo Final</strong></td>
                        <td><strong>R$ {self.saldo_final:,.2f}</strong></td>
                    </tr>
                </tbody>
            </table>
            
            <div class="resumo">
                <h3>Resumo por Imóvel</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Imóvel</th>
                            <th>Inquilino</th>
                            <th>Créditos</th>
                            <th>Débitos</th>
                            <th>Líquido</th>
                        </tr>
                    </thead>
                    <tbody>
        """
        
        for contrato_data in self.resumo_por_contrato.values():
            liquido = contrato_data['creditos'] - contrato_data['debitos']
            html += f"""
                        <tr>
                            <td>{contrato_data['imovel']}</td>
                            <td>{contrato_data['inquilino']}</td>
                            <td class="credito">R$ {contrato_data['creditos']:,.2f}</td>
                            <td class="debito">R$ {contrato_data['debitos']:,.2f}</td>
                            <td>R$ {liquido:,.2f}</td>
                        </tr>
            """
        
        html += """
                    </tbody>
                </table>
            </div>
        </body>
        </html>
        """
        
        return html.replace(',', 'X').replace('.', ',').replace('X', '.')


# ===== SERVIÇOS DE INTEGRAÇÃO =====

class ServicoContaCorrente:
    """Serviço para operações da conta corrente"""
    
    @staticmethod
    def criar_ou_atualizar_conta(proprietario):
        """Cria ou obtém conta corrente do proprietário"""
        conta, created = ContaCorrenteProprietario.objects.get_or_create(
            proprietario=proprietario,
            defaults={
                'email_extrato': proprietario.email if hasattr(proprietario, 'email') else None
            }
        )
        return conta
    
    @staticmethod
    def processar_cobranca_paga(cobranca):
        """
        Processa uma cobrança paga e lança os movimentos na conta corrente
        """
        from financeiro.models import Despesa
        
        # Obter proprietário (assumindo que contrato tem proprietário)
        proprietario = cobranca.contrato.proprietario.first()
        if not proprietario:
            return None
        
        # Criar/obter conta
        conta = ServicoContaCorrente.criar_ou_atualizar_conta(proprietario)
        
        # Data do movimento
        data_mov = cobranca.data_pagamento or date.today()
        
        # 1. Lançar crédito do aluguel
        valor_aluguel = cobranca.valor_aluguel
        if valor_aluguel > 0:
            MovimentoContaCorrente.objects.create(
                conta=conta,
                tipo='credito',
                categoria='aluguel',
                valor=valor_aluguel,
                descricao=f"Aluguel {cobranca.data_referencia_texto}",
                descricao_detalhada=f"Recebimento de aluguel referente a {cobranca.data_referencia_texto}\nContrato: {cobranca.contrato}\nInquilino: {cobranca.inquilino}",
                contrato=cobranca.contrato,
                cobranca=cobranca,
                mes_referencia=cobranca.mes_referencia,
                ano_referencia=cobranca.ano_referencia,
                data_movimento=data_mov,
                metadados={
                    'valor_original': float(valor_aluguel),
                    'numero_cobranca': cobranca.numero_cobranca
                }
            )
        
        # 2. Processar despesas
        despesas = Despesa.objects.filter(
            contrato=cobranca.contrato,
            is_ativa=True
        ).filter(
            Q(data_inicio__lte=date(cobranca.ano_referencia, cobranca.mes_referencia, 1))
        )
        
        for despesa in despesas:
            if despesa.parcela_ativa_em_data(date(cobranca.ano_referencia, cobranca.mes_referencia, 15)):
                composicao = despesa.calcular_composicao_financeira()
                
                if despesa.paga_por == 'inquilino':
                    # Despesa paga pelo inquilino - crédito para proprietário
                    MovimentoContaCorrente.objects.create(
                        conta=conta,
                        tipo='credito',
                        categoria='despesa_inquilino',
                        valor=despesa.valor_total,
                        descricao=f"{despesa.tipo.nome} - Pago pelo Inquilino",
                        descricao_detalhada=despesa.get_descricao_completa(),
                        contrato=cobranca.contrato,
                        cobranca=cobranca,
                        despesa=despesa,
                        mes_referencia=cobranca.mes_referencia,
                        ano_referencia=cobranca.ano_referencia,
                        data_movimento=data_mov,
                        metadados=composicao
                    )
                    
                    # Se tem taxa administrativa, debitar
                    if composicao['valor_taxa_admin'] > 0:
                        MovimentoContaCorrente.objects.create(
                            conta=conta,
                            tipo='debito',
                            categoria='taxa_admin',
                            valor=composicao['valor_taxa_admin'],
                            descricao=f"Taxa Admin s/ {despesa.tipo.nome}",
                            descricao_detalhada=f"Taxa administrativa sobre {despesa.tipo.nome}\nPercentual: {composicao['taxa_admin_percentual']}%",
                            contrato=cobranca.contrato,
                            cobranca=cobranca,
                            despesa=despesa,
                            mes_referencia=cobranca.mes_referencia,
                            ano_referencia=cobranca.ano_referencia,
                            data_movimento=data_mov,
                            metadados={
                                'taxa_percentual': float(composicao['taxa_admin_percentual']),
                                'valor_base': float(composicao['valor_com_incidencia'])
                            }
                        )
                
                elif despesa.paga_por == 'proprietario':
                    # Despesa paga pelo proprietário - débito
                    MovimentoContaCorrente.objects.create(
                        conta=conta,
                        tipo='debito',
                        categoria='despesa_proprietario',
                        valor=despesa.valor_total,
                        descricao=f"{despesa.tipo.nome} - Pago pelo Proprietário",
                        descricao_detalhada=despesa.get_descricao_completa(),
                        contrato=cobranca.contrato,
                        cobranca=cobranca,
                        despesa=despesa,
                        mes_referencia=cobranca.mes_referencia,
                        ano_referencia=cobranca.ano_referencia,
                        data_movimento=data_mov,
                        metadados=composicao
                    )
        
        # 3. Taxa de administração sobre aluguel (se houver)
        if hasattr(cobranca.contrato, 'valor_taxa_administracao_percentual'):
            taxa_percentual = cobranca.contrato.valor_taxa_administracao_percentual or Decimal('8.00')
            valor_taxa = valor_aluguel * (taxa_percentual / 100)
            
            if valor_taxa > 0:
                MovimentoContaCorrente.objects.create(
                    conta=conta,
                    tipo='debito',
                    categoria='taxa_admin',
                    valor=valor_taxa,
                    descricao=f"Taxa Administração {taxa_percentual}% s/ Aluguel",
                    descricao_detalhada=f"Taxa de administração sobre aluguel\nBase: R$ {valor_aluguel:,.2f}\nPercentual: {taxa_percentual}%",
                    contrato=cobranca.contrato,
                    cobranca=cobranca,
                    mes_referencia=cobranca.mes_referencia,
                    ano_referencia=cobranca.ano_referencia,
                    data_movimento=data_mov,
                    metadados={
                        'taxa_percentual': float(taxa_percentual),
                        'valor_base': float(valor_aluguel)
                    }
                )
        
        return conta
    
    @staticmethod
    def processar_repasse(repasse):
        """Processa um repasse efetuado"""
        conta = ServicoContaCorrente.criar_ou_atualizar_conta(repasse.proprietario)
        
        MovimentoContaCorrente.objects.create(
            conta=conta,
            tipo='debito',
            categoria='repasse',
            valor=repasse.valor_liquido,
            descricao=f"Repasse Efetuado - {repasse.mes_referencia:02d}/{repasse.ano_referencia}",
            descricao_detalhada=f"Repasse referente ao período {repasse.mes_referencia:02d}/{repasse.ano_referencia}\nMétodo: {repasse.metodo_pagamento or 'Transferência'}\nData: {repasse.data_efetivacao}",
            contrato=repasse.contrato,
            repasse=repasse,
            mes_referencia=repasse.mes_referencia,
            ano_referencia=repasse.ano_referencia,
            data_movimento=repasse.data_efetivacao or date.today(),
            metadados={
                'valor_bruto': float(repasse.valor),
                'taxa_admin': float(repasse.valor_taxa_admin),
                'descontos': float(repasse.valor_desconto),
                'valor_liquido': float(repasse.valor_liquido)
            }
        )
        
        return conta
    
    @staticmethod
    def gerar_extrato_mensal(proprietario, mes, ano):
        """Gera extrato mensal para o proprietário"""
        conta = ServicoContaCorrente.criar_ou_atualizar_conta(proprietario)
        
        # Verificar se já existe
        extrato, created = ExtratoMensal.objects.get_or_create(
            conta=conta,
            mes_referencia=mes,
            ano_referencia=ano,
            defaults={
                'data_inicio': date(ano, mes, 1),
                'data_fim': date(ano, mes, calendar.monthrange(ano, mes)[1])
            }
        )
        
        # Gerar/regenerar
        extrato.gerar_extrato()
        
        return extrato
    
    @staticmethod
    def enviar_extrato_mensal(extrato):
        """Envia extrato por email/WhatsApp"""
        from django.core.mail import EmailMessage
        from django.template.loader import render_to_string
        import io
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        
        if extrato.status != 'finalizado':
            return False
        
        # Gerar PDF se não existe
        if not extrato.arquivo_pdf:
            # Criar PDF com ReportLab ou WeasyPrint
            pdf_buffer = io.BytesIO()
            
            # Opção 1: HTML para PDF com WeasyPrint (se instalado)
            try:
                import weasyprint
                html_content = extrato.gerar_html_extrato()
                pdf = weasyprint.HTML(string=html_content).write_pdf()
                pdf_buffer.write(pdf)
            except ImportError:
                # Opção 2: PDF simples com ReportLab
                p = canvas.Canvas(pdf_buffer, pagesize=A4)
                p.drawString(100, 750, f"Extrato {extrato.periodo_formatado}")
                p.drawString(100, 730, f"Proprietário: {extrato.conta.proprietario.nome}")
                # ... adicionar mais conteúdo
                p.showPage()
                p.save()
            
            pdf_buffer.seek(0)
            extrato.arquivo_pdf.save(
                f"extrato_{extrato.conta.id}_{extrato.mes_referencia:02d}{extrato.ano_referencia}.pdf",
                pdf_buffer
            )
        
        # Enviar por email
        if extrato.conta.email_extrato:
            html_content = extrato.gerar_html_extrato()
            
            email = EmailMessage(
                subject=f'Extrato Mensal - {extrato.periodo_formatado}',
                body=f'''Prezado(a) {extrato.conta.proprietario.nome},

Segue seu extrato mensal referente a {extrato.periodo_formatado}.

Resumo:
- Saldo Anterior: R$ {extrato.saldo_anterior:,.2f}
- Total de Créditos: R$ {extrato.total_creditos:,.2f}
- Total de Débitos: R$ {extrato.total_debitos:,.2f}
- Total de Repasses: R$ {extrato.total_repasses:,.2f}
- Saldo Final: R$ {extrato.saldo_final:,.2f}

Para visualizar o extrato detalhado, acesse o link:
https://seudominio.com/extrato/{extrato.hash_acesso}

Atenciosamente,
Sua Imobiliária'''.replace('.', ','),
                to=[extrato.conta.email_extrato],
            )
            
            if extrato.arquivo_pdf:
                email.attach_file(extrato.arquivo_pdf.path)
            
            email.send()
        
        # Marcar como enviado
        extrato.status = 'enviado'
        extrato.data_envio = timezone.now()
        extrato.save()
        
        # TODO: Implementar envio por WhatsApp se configurado
        if extrato.conta.whatsapp_extrato:
            # Integrar com API do WhatsApp Business ou Twilio
            pass
        
        return True


# ===== COMANDOS DE GERENCIAMENTO =====

from django.core.management.base import BaseCommand

class ProcessarCobrancasPagasCommand(BaseCommand):
    """
    Comando para processar cobranças pagas e atualizar conta corrente
    python manage.py processar_cobrancas_pagas
    """
    help = 'Processa cobranças pagas e atualiza conta corrente'
    
    def handle(self, *args, **options):
        from financeiro.models import Cobranca
        
        # Buscar cobranças pagas não processadas
        cobrancas = Cobranca.objects.filter(
            status='paga'
        ).exclude(
            movimentoscontacorrente__isnull=False
        )
        
        for cobranca in cobrancas:
            try:
                ServicoContaCorrente.processar_cobranca_paga(cobranca)
                self.stdout.write(
                    self.style.SUCCESS(f'Cobrança {cobranca.numero_cobranca} processada')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Erro ao processar {cobranca.numero_cobranca}: {e}')
                )


class GerarExtratosMensaisCommand(BaseCommand):
    """
    Comando para gerar extratos mensais
    python manage.py gerar_extratos_mensais --mes=7 --ano=2024
    """
    help = 'Gera extratos mensais para todos os proprietários'
    
    def add_arguments(self, parser):
        parser.add_argument('--mes', type=int, required=True)
        parser.add_argument('--ano', type=int, required=True)
        parser.add_argument('--enviar', action='store_true')
    
    def handle(self, *args, **options):
        from sisimob.models import Cliente
        
        mes = options['mes']
        ano = options['ano']
        enviar = options.get('enviar', False)
        
        # Buscar todos os proprietários com contratos ativos
        proprietarios = Cliente.objects.filter(
            tipo='proprietario',
            contratos_proprietario__status='ativo'
        ).distinct()
        
        for proprietario in proprietarios:
            try:
                extrato = ServicoContaCorrente.gerar_extrato_mensal(
                    proprietario, mes, ano
                )
                
                if enviar:
                    ServicoContaCorrente.enviar_extrato_mensal(extrato)
                    self.stdout.write(
                        self.style.SUCCESS(f'Extrato enviado para {proprietario.nome}')
                    )
                else:
                    self.stdout.write(
                        self.style.SUCCESS(f'Extrato gerado para {proprietario.nome}')
                    )
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Erro para {proprietario.nome}: {e}')
                )


# ===== VIEWS EXEMPLO =====

from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required

@login_required
def visualizar_conta_corrente(request, proprietario_id):
    """View para visualizar conta corrente"""
    proprietario = get_object_or_404(Cliente, id=proprietario_id)
    conta = ServicoContaCorrente.criar_ou_atualizar_conta(proprietario)
    
    # Buscar movimentos recentes
    movimentos = conta.movimentos.all()[:50]
    
    # Buscar extratos
    extratos = conta.extratos.all()[:12]
    
    context = {
        'conta': conta,
        'proprietario': proprietario,
        'movimentos': movimentos,
        'extratos': extratos,
        'saldo_disponivel': conta.saldo_disponivel
    }
    
    return render(request, 'financeiro/conta_corrente.html', context)


@login_required
def gerar_extrato_view(request, proprietario_id):
    """View para gerar extrato"""
    if request.method == 'POST':
        proprietario = get_object_or_404(Cliente, id=proprietario_id)
        mes = int(request.POST.get('mes'))
        ano = int(request.POST.get('ano'))
        
        extrato = ServicoContaCorrente.gerar_extrato_mensal(proprietario, mes, ano)
        
        if request.POST.get('enviar'):
            ServicoContaCorrente.enviar_extrato_mensal(extrato)
            
        return JsonResponse({
            'success': True,
            'extrato_id': extrato.id,
            'hash': extrato.hash_acesso
        })
    
    return JsonResponse({'success': False})


def visualizar_extrato_publico(request, hash_acesso):
    """View pública para visualizar extrato via hash"""
    extrato = get_object_or_404(ExtratoMensal, hash_acesso=hash_acesso)
    
    # Marcar como visualizado
    if not extrato.data_visualizacao:
        extrato.status = 'visualizado'
        extrato.data_visualizacao = timezone.now()
        extrato.save()
    
    # Gerar HTML
    html_content = extrato.gerar_html_extrato()
    
    return HttpResponse(html_content)


# ===== SIGNALS =====

from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender='financeiro.Cobranca')
def processar_cobranca_signal(sender, instance, created, **kwargs):
    """Signal para processar cobrança quando marcada como paga"""
    if instance.status == 'paga' and instance.data_pagamento:
        # Verificar se já foi processada
        if not MovimentoContaCorrente.objects.filter(cobranca=instance).exists():
            ServicoContaCorrente.processar_cobranca_paga(instance)


@receiver(post_save, sender='financeiro.Repasse')
def processar_repasse_signal(sender, instance, created, **kwargs):
    """Signal para processar repasse quando efetuado"""
    if instance.status == 'efetuado' and instance.data_efetivacao:
        # Verificar se já foi processado
        if not MovimentoContaCorrente.objects.filter(repasse=instance).exists():
            ServicoContaCorrente.processar_repasse(instance)


# ===== ADMIN =====

from django.contrib import admin

@admin.register(ContaCorrenteProprietario)
class ContaCorrenteAdmin(admin.ModelAdmin):
    list_display = ['proprietario', 'saldo_atual', 'saldo_bloqueado', 'saldo_disponivel', 'ativa']
    list_filter = ['ativa', 'enviar_extrato_automatico']
    search_fields = ['proprietario__nome', 'proprietario__cpf_cnpj']
    readonly_fields = ['saldo_atual', 'data_abertura', 'data_ultima_atualizacao']
    
    actions = ['recalcular_saldos']
    
    def recalcular_saldos(self, request, queryset):
        for conta in queryset:
            conta.recalcular_saldo()
        self.message_user(request, f"{queryset.count()} contas recalculadas")
    recalcular_saldos.short_description = "Recalcular saldos"


@admin.register(MovimentoContaCorrente)
class MovimentoContaCorrenteAdmin(admin.ModelAdmin):
    list_display = ['data_movimento', 'conta', 'tipo', 'categoria', 'valor_formatado', 'saldo_posterior']
    list_filter = ['tipo', 'categoria', 'data_movimento', 'processado', 'conciliado']
    search_fields = ['descricao', 'conta__proprietario__nome']
    date_hierarchy = 'data_movimento'
    readonly_fields = ['saldo_anterior', 'saldo_posterior', 'data_criacao']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'conta', 'conta__proprietario', 'contrato', 'cobranca', 'despesa', 'repasse'
        )


@admin.register(ExtratoMensal)
class ExtratoMensalAdmin(admin.ModelAdmin):
    list_display = ['conta', 'periodo_formatado', 'status', 'saldo_final', 'data_envio']
    list_filter = ['status', 'mes_referencia', 'ano_referencia']
    search_fields = ['conta__proprietario__nome']
    readonly_fields = ['hash_acesso', 'data_geracao', 'resumo_por_categoria', 'resumo_por_contrato']
    
    actions = ['gerar_extratos', 'enviar_extratos']
    
    def gerar_extratos(self, request, queryset):
        for extrato in queryset:
            extrato.gerar_extrato()
        self.message_user(request, f"{queryset.count()} extratos gerados")
    gerar_extratos.short_description = "Gerar/Regenerar extratos"
    
    def enviar_extratos(self, request, queryset):
        enviados = 0
        for extrato in queryset.filter(status='finalizado'):
            if ServicoContaCorrente.enviar_extrato_mensal(extrato):
                enviados += 1
        self.message_user(request, f"{enviados} extratos enviados")
    enviar_extratos.short_description = "Enviar extratos por email"