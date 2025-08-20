# financeiro/services/indice_api.py
import requests
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from django.conf import settings
import logging

from ..models.indice import IndiceInflacao

logger = logging.getLogger(__name__)


class IndiceAPIService:
    """Serviço para buscar e atualizar índices de inflação de APIs externas"""
    
    def __init__(self):
        self.timeout = getattr(settings, 'API_TIMEOUT', 30)
    
    def gerar_periodos_ipca(self, fim_data=None):
        """Gera string de períodos para API do IBGE"""
        if fim_data is None:
            fim_data = datetime.now()
        
        start_year = 1979
        start_month = 12
        end_year = fim_data.year
        end_month = fim_data.month
        
        periodos = []
        current_year = start_year
        current_month = start_month
        
        while (current_year < end_year) or (current_year == end_year and current_month <= end_month):
            periodo = f"{current_year:04d}{current_month:02d}"
            periodos.append(periodo)
            if current_month == 12:
                current_month = 1
                current_year += 1
            else:
                current_month += 1
        
        return "|".join(periodos)
    
    def buscar_ipca(self):
        """Busca dados do IPCA na API do IBGE"""
        try:
            periodos_str = self.gerar_periodos_ipca()
            url = f"https://servicodados.ibge.gov.br/api/v3/agregados/1737/periodos/{periodos_str}/variaveis/63?localidades=N1[all]"
            
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            dados = response.json()
            return self.processar_ipca(dados)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro ao buscar IPCA: {e}")
            raise
        except Exception as e:
            logger.error(f"Erro ao processar IPCA: {e}")
            raise
    
    def buscar_igpm(self):
        """Busca dados do IGP-M na API do Ipeadata"""
        try:
            url = "http://ipeadata.gov.br/api/odata4/ValoresSerie(SERCODIGO='IGP12_IGPMG12')?$format=json"
            
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            dados = response.json()
            return self.processar_igpm(dados)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro ao buscar IGP-M: {e}")
            raise
        except Exception as e:
            logger.error(f"Erro ao processar IGP-M: {e}")
            raise
    
    def processar_ipca(self, dados):
        """Processa dados do IPCA retornados pela API"""
        indices = []
        
        try:
            serie = dados[0]['resultados'][0]['series'][0]['serie']
            
            for periodo, valor in serie.items():
                if valor in ['...', 'N/A', '', None]:
                    continue
                
                try:
                    ano = int(periodo[:4])
                    mes = int(periodo[4:])
                    valor_decimal = Decimal(str(valor))
                    
                    data_ref = date(ano, mes, 1)
                    
                    indices.append({
                        'data_referencia': data_ref,
                        'valor': valor_decimal,
                        'tipo': 'IPCA',
                        'fonte': 'IBGE'
                    })
                    
                except (ValueError, TypeError) as e:
                    logger.warning(f"Erro ao processar período {periodo}: {e}")
                    continue
                    
        except (KeyError, IndexError) as e:
            logger.error(f"Estrutura de dados IPCA inválida: {e}")
            raise
        
        return indices
    
    def processar_igpm(self, dados):
        """Processa dados do IGP-M retornados pela API"""
        indices = []
        
        try:
            items = dados.get('value', dados)
            
            for item in items:
                try:
                    data_str = item.get('VALDATA') or item.get('data')
                    valor = item.get('VALVALOR') or item.get('valor')
                    
                    if not data_str or valor in ['...', 'N/A', '', None]:
                        continue
                    
                    data_ref = datetime.fromisoformat(data_str.split('T')[0]).date()
                    valor_decimal = Decimal(str(valor))
                    
                    indices.append({
                        'data_referencia': data_ref,
                        'valor': valor_decimal,
                        'tipo': 'IGPM',
                        'fonte': 'FGV'
                    })
                    
                except (ValueError, TypeError, KeyError) as e:
                    logger.warning(f"Erro ao processar item IGP-M: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Erro ao processar dados IGP-M: {e}")
            raise
        
        return indices
    
    def atualizar_indice(self, tipo):
        """Atualiza um tipo específico de índice"""
        logger.info(f"Iniciando atualização do {tipo}")
        
        if tipo == 'IPCA':
            dados = self.buscar_ipca()
        elif tipo == 'IGPM':
            dados = self.buscar_igpm()
        else:
            raise ValueError(f"Tipo de índice inválido: {tipo}")
        
        criados = atualizados = 0
        
        # Importa os dados sem calcular acumulados (para performance)
        for item in dados:
            try:
                indice, created = IndiceInflacao.objects.get_or_create(
                    tipo=item['tipo'],
                    data_referencia=item['data_referencia'],
                    defaults={
                        'valor': item['valor'],
                        'fonte': item['fonte'],
                        'acumulado_12_meses': None  # Será calculado depois
                    }
                )
                
                if created:
                    criados += 1
                    logger.debug(f"Criado: {indice}")
                else:
                    # Atualizar se valor for diferente
                    if indice.valor != item['valor']:
                        indice.valor = item['valor']
                        indice.fonte = item['fonte']
                        indice.acumulado_12_meses = None  # Forçar recálculo
                        indice.save(update_fields=['valor', 'fonte', 'acumulado_12_meses'])
                        atualizados += 1
                        logger.debug(f"Atualizado: {indice}")
                        
            except Exception as e:
                logger.error(f"Erro ao salvar índice {item}: {e}")
                continue
        
        # ✅ NOVA FUNCIONALIDADE: Recalcula todos os acumulados após importar
        if criados > 0 or atualizados > 0:
            logger.info(f"Recalculando acumulados para {tipo}...")
            recalculados = IndiceInflacao.recalcular_acumulados(tipo)
            logger.info(f"Acumulados recalculados: {recalculados}")
        
        logger.info(f"{tipo} atualizado: {criados} criados, {atualizados} atualizados")
        return {
            'criados': criados, 
            'atualizados': atualizados,
            'recalculados': recalculados if criados > 0 or atualizados > 0 else 0
        }
    
    def atualizar_todos_indices(self):
        """Atualiza todos os tipos de índices disponíveis"""
        resultados = {}
        
        for tipo in ['IPCA', 'IGPM']:
            try:
                resultado = self.atualizar_indice(tipo)
                resultados[tipo] = {
                    'sucesso': True,
                    'criados': resultado['criados'],
                    'atualizados': resultado['atualizados'],
                    'recalculados': resultado.get('recalculados', 0)
                }
            except Exception as e:
                logger.error(f"Erro ao atualizar {tipo}: {e}")
                resultados[tipo] = {
                    'sucesso': False,
                    'erro': str(e)
                }
        
        return resultados
    
    def corrigir_acumulados_historicos(self, tipo=None):
        """
        Método para corrigir acumulados históricos já salvos incorretamente.
        Execute uma vez após implementar a correção.
        """
        logger.info(f"Iniciando correção de acumulados históricos para {tipo or 'todos os tipos'}")
        
        if tipo:
            tipos = [tipo]
        else:
            tipos = ['IPCA', 'IGPM', 'INPC']
        
        total_corrigidos = 0
        for tipo_atual in tipos:
            corrigidos = IndiceInflacao.recalcular_acumulados(tipo_atual)
            total_corrigidos += corrigidos
            logger.info(f"{tipo_atual}: {corrigidos} registros corrigidos")
        
        logger.info(f"Correção concluída: {total_corrigidos} registros corrigidos no total")
        return total_corrigidos