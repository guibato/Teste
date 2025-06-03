# financeiro/services/reajuste_service.py

from typing import List, Dict, Optional, Any
from decimal import Decimal
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from sisimob.models import Contrato
from financeiro.models.reajuste import ReajusteAluguel
from financeiro.models.indice import IndiceInflacao


class ReajusteService:
    """Service para gestão de reajustes de aluguel"""
    
    @staticmethod
    def obter_sugestoes_pendentes(
        data_limite: date = None,
        contratos_ids: List[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Obtém todas as sugestões de reajuste pendentes
        """
        if data_limite is None:
            data_limite = date.today() + relativedelta(months=2)
        
        # Filtrar contratos ativos
        contratos_query = Contrato.objects.filter(ativo=True)
        if contratos_ids:
            contratos_query = contratos_query.filter(id__in=contratos_ids)
        
        sugestoes = []
        
        for contrato in contratos_query:
            sugestao = ReajusteAluguel.sugerir_reajuste(contrato)
            
            if (sugestao and 
                sugestao['data_reajuste'] <= data_limite and
                not ReajusteService._ja_possui_reajuste(
                    contrato, sugestao['data_reajuste']
                )):
                
                sugestao.update({
                    'contrato': contrato,
                    'status': ReajusteService._determinar_status(sugestao),
                    'variacao_percentual': ReajusteService._calcular_variacao_percentual(
                        sugestao['valor_anterior'], 
                        sugestao['valor_sugerido']
                    )
                })
                sugestoes.append(sugestao)
        
        return sorted(sugestoes, key=lambda x: x['data_reajuste'])
    
    @staticmethod
    def _ja_possui_reajuste(contrato: Contrato, data_reajuste: date) -> bool:
        """Verifica se já existe reajuste para a data"""
        return ReajusteAluguel.objects.filter(
            contrato=contrato,
            data_reajuste=data_reajuste
        ).exists()
    
    @staticmethod
    def _determinar_status(sugestao: Dict) -> str:
        """Determina o status da sugestão baseado na data"""
        hoje = date.today()
        data_reajuste = sugestao['data_reajuste']
        
        if data_reajuste <= hoje:
            return 'vencido'
        elif data_reajuste <= hoje + relativedelta(days=30):
            return 'urgente'
        else:
            return 'pendente'
    
    @staticmethod
    def _calcular_variacao_percentual(valor_anterior: Decimal, valor_novo: Decimal) -> Decimal:
        """Calcula a variação percentual entre valores"""
        if valor_anterior == 0:
            return Decimal('0')
        
        variacao = ((valor_novo - valor_anterior) / valor_anterior) * 100
        return variacao.quantize(Decimal('0.01'))
    
    @staticmethod
    @transaction.atomic
    def processar_reajustes_lote(
        sugestoes_ids: List[int],
        usuario_id: int,
        observacao_padrao: str = None
    ) -> Dict[str, Any]:
        """
        Processa múltiplos reajustes em lote
        """
        sucessos = []
        erros = []
        
        # Re-buscar sugestões atualizadas
        sugestoes = ReajusteService.obter_sugestoes_pendentes()
        sugestoes_dict = {
            f"{s['contrato'].id}_{s['data_reajuste']}": s 
            for s in sugestoes
        }
        
        for sugestao_id in sugestoes_ids:
            try:
                if sugestao_id in sugestoes_dict:
                    sugestao = sugestoes_dict[sugestao_id]
                    
                    reajuste = ReajusteService.criar_reajuste(
                        contrato=sugestao['contrato'],
                        valor_anterior=sugestao['valor_anterior'],
                        valor_reajustado=sugestao['valor_sugerido'],
                        fator_aplicado=sugestao['fator_aplicado'],
                        indice_utilizado=sugestao['indice_utilizado'],
                        data_reajuste=sugestao['data_reajuste'],
                        observacao=observacao_padrao
                    )
                    
                    sucessos.append({
                        'contrato': sugestao['contrato'],
                        'reajuste': reajuste
                    })
                else:
                    erros.append({
                        'id': sugestao_id,
                        'erro': 'Sugestão não encontrada ou inválida'
                    })
                    
            except Exception as e:
                erros.append({
                    'id': sugestao_id,
                    'erro': str(e)
                })
        
        return {
            'sucessos': sucessos,
            'erros': erros,
            'total_processados': len(sucessos),
            'total_erros': len(erros)
        }
    
    @staticmethod
    def criar_reajuste(
        contrato: Contrato,
        valor_anterior: Decimal,
        valor_reajustado: Decimal,
        fator_aplicado: Decimal,
        indice_utilizado: str,
        data_reajuste: date,
        observacao: str = None
    ) -> ReajusteAluguel:
        """
        Cria um novo reajuste
        """
        # Validações
        if valor_reajustado <= 0:
            raise ValidationError("Valor reajustado deve ser maior que zero")
        
        if fator_aplicado < 0:
            raise ValidationError("Fator aplicado não pode ser negativo")
        
        if ReajusteService._ja_possui_reajuste(contrato, data_reajuste):
            raise ValidationError(
                f"Já existe reajuste para o contrato {contrato} na data {data_reajuste}"
            )
        
        reajuste = ReajusteAluguel.objects.create(
            contrato=contrato,
            valor_anterior=valor_anterior,
            valor_reajustado=valor_reajustado,
            fator_aplicado=fator_aplicado,
            indice_utilizado=indice_utilizado,
            data_reajuste=data_reajuste,
            observacao=observacao
        )
        
        return reajuste
    
    @staticmethod
    def obter_historico_contrato(
        contrato: Contrato,
        data_inicio: date = None,
        data_fim: date = None
    ) -> List[Dict[str, Any]]:
        """
        Obtém histórico de reajustes de um contrato
        """
        query = ReajusteAluguel.objects.filter(contrato=contrato)
        
        if data_inicio:
            query = query.filter(data_reajuste__gte=data_inicio)
        if data_fim:
            query = query.filter(data_reajuste__lte=data_fim)
        
        reajustes = query.order_by('data_reajuste')
        
        historico = []
        valor_atual = contrato.valor_base
        data_atual = contrato.data_inicio
        
        for reajuste in reajustes:
            # Período anterior
            historico.append({
                'tipo': 'periodo',
                'data_inicio': data_atual,
                'data_fim': reajuste.data_reajuste - relativedelta(days=1),
                'valor': valor_atual,
                'duracao_meses': ReajusteService._calcular_duracao_meses(
                    data_atual, reajuste.data_reajuste
                )
            })
            
            # Reajuste
            historico.append({
                'tipo': 'reajuste',
                'data': reajuste.data_reajuste,
                'valor_anterior': reajuste.valor_anterior,
                'valor_novo': reajuste.valor_reajustado,
                'fator_aplicado': reajuste.fator_aplicado,
                'indice_utilizado': reajuste.indice_utilizado,
                'observacao': reajuste.observacao,
                'variacao_percentual': ReajusteService._calcular_variacao_percentual(
                    reajuste.valor_anterior, reajuste.valor_reajustado
                )
            })
            
            valor_atual = reajuste.valor_reajustado
            data_atual = reajuste.data_reajuste
        
        # Período atual (se houver)
        if data_atual <= date.today():
            historico.append({
                'tipo': 'periodo_atual',
                'data_inicio': data_atual,
                'data_fim': date.today(),
                'valor': valor_atual,
                'duracao_meses': ReajusteService._calcular_duracao_meses(
                    data_atual, date.today()
                )
            })
        
        return historico
    
    @staticmethod
    def _calcular_duracao_meses(data_inicio: date, data_fim: date) -> int:
        """Calcula duração em meses entre duas datas"""
        return (data_fim.year - data_inicio.year) * 12 + (data_fim.month - data_inicio.month)
    
    @staticmethod
    def obter_estatisticas_reajustes(
        data_inicio: date = None,
        data_fim: date = None
    ) -> Dict[str, Any]:
        """
        Obtém estatísticas dos reajustes
        """
        if data_inicio is None:
            data_inicio = date.today() - relativedelta(years=1)
        if data_fim is None:
            data_fim = date.today()
        
        reajustes = ReajusteAluguel.objects.filter(
            data_reajuste__range=[data_inicio, data_fim]
        )
        
        if not reajustes.exists():
            return {
                'total_reajustes': 0,
                'valor_total_reajustado': Decimal('0'),
                'fator_medio': Decimal('0'),
                'maior_reajuste': None,
                'menor_reajuste': None,
                'distribuicao_indices': {}
            }
        
        # Cálculos
        total_reajustes = reajustes.count()
        valor_total = sum(r.valor_reajustado - r.valor_anterior for r in reajustes)
        fator_medio = sum(r.fator_aplicado for r in reajustes) / total_reajustes
        
        maior_reajuste = max(reajustes, key=lambda r: r.fator_aplicado)
        menor_reajuste = min(reajustes, key=lambda r: r.fator_aplicado)
        
        # Distribuição por índices
        distribuicao_indices = {}
        for reajuste in reajustes:
            indice = reajuste.indice_utilizado
            if indice not in distribuicao_indices:
                distribuicao_indices[indice] = {
                    'quantidade': 0,
                    'valor_total': Decimal('0'),
                    'fator_medio': Decimal('0')
                }
            
            distribuicao_indices[indice]['quantidade'] += 1
            distribuicao_indices[indice]['valor_total'] += (
                reajuste.valor_reajustado - reajuste.valor_anterior
            )
        
        # Calcular fatores médios por índice
        for indice_data in distribuicao_indices.values():
            reajustes_indice = reajustes.filter(indice_utilizado=indice)
            indice_data['fator_medio'] = (
                sum(r.fator_aplicado for r in reajustes_indice) / 
                indice_data['quantidade']
            )
        
        return {
            'total_reajustes': total_reajustes,
            'valor_total_reajustado': valor_total,
            'fator_medio': fator_medio.quantize(Decimal('0.01')),
            'maior_reajuste': {
                'contrato': maior_reajuste.contrato,
                'fator': maior_reajuste.fator_aplicado,
                'data': maior_reajuste.data_reajuste
            },
            'menor_reajuste': {
                'contrato': menor_reajuste.contrato,
                'fator': menor_reajuste.fator_aplicado,
                'data': menor_reajuste.data_reajuste
            },
            'distribuicao_indices': distribuicao_indices,
            'periodo': {
                'inicio': data_inicio,
                'fim': data_fim
            }
        }