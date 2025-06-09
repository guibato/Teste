from decimal import Decimal
import datetime
from django.apps import apps


class CobrancaPreviewService:
    """Service para geração de previews de cobranças"""
    
    @staticmethod
    def gerar_preview_contrato(contrato, mes, ano, opcoes=None):
        """
        Gera preview de cobrança para um contrato específico
        """
        if not contrato:
            return None
        
        opcoes = opcoes or {}
        incluir_despesas = opcoes.get('incluir_despesas', True)
        
        # Verificar se já existe cobrança
        from ..models import Cobranca
        cobranca_existente = Cobranca.objects.filter(
            contrato=contrato,
            mes_referencia=mes,
            ano_referencia=ano
        ).exists()
        
        if cobranca_existente:
            return {
                'contrato_id': contrato.pk,
                'pode_gerar': False,
                'motivo_bloqueio': 'Cobrança já existe para este período'
            }
        
        # Calcular valores
        valor_aluguel = CobrancaCalculadoraService.calcular_valor_aluguel(contrato, mes, ano)
        
        despesas = []
        valor_despesas = Decimal('0.00')
        
        if incluir_despesas:
            despesas = CobrancaCalculadoraService.buscar_despesas_periodo(contrato, mes, ano)
            valor_despesas = CobrancaCalculadoraService.calcular_valor_despesas(despesas)
        
        valor_total = valor_aluguel + valor_despesas
        
        # Informações do inquilino
        inquilino = None
        inquilino_nome = 'Sem inquilino'
        inquilino_email = ''
        
        try:
            if hasattr(contrato, 'inquilino'):
                if hasattr(contrato.inquilino, 'all'):
                    # Relacionamento ManyToMany
                    inquilino = contrato.inquilino.first()
                else:
                    # Relacionamento ForeignKey
                    inquilino = contrato.inquilino
                
                if inquilino:
                    inquilino_nome = inquilino.nome
                    inquilino_email = getattr(inquilino, 'email', '')
        except AttributeError:
            pass
        
        # Gerar descrição
        descricao = CobrancaDescricaoService.gerar_descricao_simples(valor_aluguel, mes, ano)
        
        if despesas:
            descricao += "\n\nDespesas incluídas:"
            for despesa in despesas:
                nome_despesa = getattr(despesa, 'nome', str(despesa.tipo) if hasattr(despesa, 'tipo') else 'Despesa')
                valor_despesa = despesa.calcular_valor_parcela()
                valor_formatado = CobrancaDescricaoService._formatar_valor(valor_despesa)
                descricao += f"\n• {nome_despesa}: {valor_formatado}"
            
            descricao += f"\n\nValor total: {CobrancaDescricaoService._formatar_valor(valor_total)}"
        
        return {
            'contrato_id': contrato.pk,
            'contrato_numero': getattr(contrato, 'numero_contrato', None) or getattr(contrato, 'tipo_contrato', f"Contrato {contrato.pk}"),
            'inquilino_nome': inquilino_nome,
            'inquilino_email': inquilino_email,
            'imovel_endereco': str(contrato.imovel) if hasattr(contrato, 'imovel') and contrato.imovel else 'Sem endereço',
            'valor_aluguel': float(valor_aluguel),
            'valor_despesas': float(valor_despesas),
            'valor_total': float(valor_total),
            'despesas': [
                {
                    'nome': getattr(d, 'nome', str(d.tipo) if hasattr(d, 'tipo') else 'Despesa'),
                    'valor': float(d.calcular_valor_parcela()),
                    'tipo': str(d.tipo) if hasattr(d, 'tipo') else 'Despesa'
                } for d in despesas
            ],
            'descricao': descricao,
            'pode_gerar': True,
            'motivo_bloqueio': ''
        }
    
    @staticmethod
    def gerar_preview_lote(contratos_ids, mes, ano, opcoes=None):
        """
        Gera preview para múltiplos contratos
        """
        opcoes = opcoes or {}
        
        try:
            Contrato = apps.get_model('sisimob', 'Contrato')
            
            if contratos_ids:
                contratos = Contrato.objects.filter(
                    id__in=contratos_ids,
                    ativo=True
                )
            else:
                contratos = Contrato.objects.filter(ativo=True)
            
            previews = []
            valor_total_geral = Decimal('0.00')
            
            for contrato in contratos:
                preview = CobrancaPreviewService.gerar_preview_contrato(contrato, mes, ano, opcoes)
                
                if preview and preview.get('pode_gerar'):
                    previews.append(preview)
                    valor_total_geral += Decimal(str(preview['valor_total']))
            
            return {
                'success': True,
                'cobrancas': previews,
                'total_cobrancas': len(previews),
                'valor_total_geral': float(valor_total_geral),
                'mes_nome': CobrancaDescricaoService.MESES_NOMES.get(mes, f'Mês {mes}'),
                'ano': ano
            }
            
        except LookupError:
            return {
                'success': False,
                'error': 'Modelo Contrato não encontrado'
            }