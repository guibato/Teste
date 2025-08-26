from decimal import Decimal
from datetime import date
from django.db import transaction
from django.shortcuts import get_object_or_404


class CobrancaCriadorService:
    """Service para criação de cobranças"""
    
    @staticmethod
    def criar_cobranca_unica(dados):
        """
        Cria uma cobrança individual
        """
        try:
            Contrato = apps.get_model('core', 'Contrato')
            from ..models import Cobranca
            
            contrato = get_object_or_404(Contrato, id=dados['contrato_id'])
            
            # Verificar se já existe
            if Cobranca.objects.filter(
                contrato=contrato,
                mes_referencia=dados['mes_referencia'],
                ano_referencia=dados['ano_referencia']
            ).exists():
                return {
                    'success': False,
                    'error': f'Cobrança já existe para {contrato} no período {dados["mes_referencia"]}/{dados["ano_referencia"]}'
                }
            
            # Calcular valores
            valor_aluguel = CobrancaCalculadoraService.calcular_valor_aluguel(
                contrato, dados['mes_referencia'], dados['ano_referencia']
            )
            
            despesas = []
            if dados.get('incluir_despesas', True):
                despesas = CobrancaCalculadoraService.buscar_despesas_periodo(
                    contrato, dados['mes_referencia'], dados['ano_referencia']
                )
            
            valor_despesas = CobrancaCalculadoraService.calcular_valor_despesas(despesas)
            valor_total = valor_aluguel + valor_despesas
            
            # Criar cobrança
            cobranca = Cobranca.objects.create(
                contrato=contrato,
                mes_referencia=dados['mes_referencia'],
                ano_referencia=dados['ano_referencia'],
                valor_aluguel=valor_aluguel,
                valor_despesas=valor_despesas,
                valor_total=valor_total,
                data_vencimento=dados['data_vencimento'],
                status='pendente'
            )
            
            # Gerar descrição se solicitado
            if dados.get('gerar_descricao_automatica', True):
                cobranca.descricao = CobrancaDescricaoService.gerar_descricao_completa(cobranca)
                cobranca.save(update_fields=['descricao'])
            
            return {
                'success': True,
                'cobranca': cobranca,
                'valor_total': float(valor_total)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Erro ao criar cobrança: {str(e)}'
            }
    
    @staticmethod
    @transaction.atomic
    def criar_cobrancas_lote(lista_dados):
        """
        Cria múltiplas cobranças em uma transação
        """
        cobrancas_criadas = []
        erros = []
        
        for dados in lista_dados:
            resultado = CobrancaCriadorService.criar_cobranca_unica(dados)
            
            if resultado['success']:
                cobrancas_criadas.append(resultado['cobranca'])
            else:
                erros.append(resultado['error'])
        
        return {
            'success': len(cobrancas_criadas) > 0,
            'cobrancas_criadas': len(cobrancas_criadas),
            'cobrancas': cobrancas_criadas,
            'erros': erros
        }
    
    @staticmethod
    def criar_cobrancas_selecionadas(dados_request):
        """
        Cria cobranças baseado em seleção de preview
        """
        try:
            mes_referencia = dados_request['mes_referencia']
            ano_referencia = dados_request['ano_referencia']
            data_vencimento = date.fromisoformat(dados_request['data_vencimento'])
            contratos_selecionados = dados_request['cobrancas_selecionadas']
            incluir_despesas = dados_request.get('incluir_despesas', True)
            gerar_descricao = dados_request.get('gerar_descricao_automatica', True)
            
            lista_dados = []
            for contrato_id in contratos_selecionados:
                lista_dados.append({
                    'contrato_id': contrato_id,
                    'mes_referencia': mes_referencia,
                    'ano_referencia': ano_referencia,
                    'data_vencimento': data_vencimento,
                    'incluir_despesas': incluir_despesas,
                    'gerar_descricao_automatica': gerar_descricao
                })
            
            return CobrancaCriadorService.criar_cobrancas_lote(lista_dados)
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Erro ao processar dados: {str(e)}'
            }