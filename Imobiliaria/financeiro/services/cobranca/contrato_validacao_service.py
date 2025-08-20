# financeiro/services/contrato_validacao_service.py

"""
Serviço para validação de contratos considerando período específico
================================================================
Resolve o problema de renovações onde contratos ficam inativos
mas deveriam gerar cobranças para períodos anteriores.
"""

from datetime import date, datetime
import calendar
from django.db.models import Q
from sisimob.models import Contrato


class ContratoValidacaoService:
    """
    Serviço responsável por validar se um contrato deveria 
    estar ativo em um período específico, independente do 
    status atual de 'ativo'
    """
    
    @staticmethod
    def contrato_estava_ativo_no_periodo(contrato, mes_referencia, ano_referencia):
        """
        ⭐ FUNÇÃO PRINCIPAL: Verifica se contrato estava ativo no período
        
        CASOS DE USO:
        - Contrato 5: ativo=False, mas deveria gerar cobrança para Mar/2025
        - Contrato 6: ativo=True, deveria gerar cobrança para Jul/2025+
        
        Args:
            contrato: Instância do modelo Contrato
            mes_referencia: Mês da cobrança (1-12)
            ano_referencia: Ano da cobrança
            
        Returns:
            tuple: (bool_valido, str_motivo)
        """
        try:
            # Calcular período da cobrança
            data_inicio_periodo = date(ano_referencia, mes_referencia, 1)
            ultimo_dia = calendar.monthrange(ano_referencia, mes_referencia)[1]
            data_fim_periodo = date(ano_referencia, mes_referencia, ultimo_dia)
            
            print(f"🔍 Validando contrato #{contrato.id} para {mes_referencia:02d}/{ano_referencia}")
            print(f"   📅 Período: {data_inicio_periodo} até {data_fim_periodo}")
            print(f"   📋 Contrato: {contrato.data_inicio} até {contrato.data_fim or 'indefinido'}")
            print(f"   ⚡ Status atual: {'Ativo' if contrato.ativo else 'Inativo'}")
            
            # REGRA 1: Contrato deve ter iniciado antes do fim do período
            if contrato.data_inicio > data_fim_periodo:
                motivo = f"Contrato ainda não havia iniciado ({contrato.data_inicio.strftime('%d/%m/%Y')})"
                print(f"   ❌ {motivo}")
                return False, motivo
            
            # REGRA 2: Se contrato tem data_fim, verificar se estava vigente
            if contrato.data_fim:
                # Contrato deve ter estado vigente durante pelo menos parte do período
                if contrato.data_fim < data_inicio_periodo:
                    motivo = f"Contrato já havia terminado ({contrato.data_fim.strftime('%d/%m/%Y')})"
                    print(f"   ❌ {motivo}")
                    return False, motivo
                
                # Se chegou aqui, contrato estava vigente durante o período
                if contrato.data_inicio <= data_fim_periodo and contrato.data_fim >= data_inicio_periodo:
                    motivo = f"Contrato estava vigente no período ({contrato.data_inicio.strftime('%d/%m/%Y')} até {contrato.data_fim.strftime('%d/%m/%Y')})"
                    print(f"   ✅ {motivo}")
                    return True, motivo
            
            # REGRA 3: Se não tem data_fim, verificar se estava ativo no período
            else:
                # Contrato sem data_fim definida
                if contrato.data_inicio <= data_fim_periodo:
                    motivo = f"Contrato vigente (sem data fim definida, início: {contrato.data_inicio.strftime('%d/%m/%Y')})"
                    print(f"   ✅ {motivo}")
                    return True, motivo
            
            # FALLBACK: Não deveria chegar aqui
            motivo = "Situação não contemplada pelas regras"
            print(f"   ⚠️ {motivo}")
            return False, motivo
            
        except Exception as e:
            motivo = f"Erro na validação: {str(e)}"
            print(f"   ❌ {motivo}")
            return False, motivo
    
    @staticmethod
    def obter_contratos_validos_periodo(mes_referencia, ano_referencia, contratos_ids=None):
        """
        ⭐ FUNÇÃO PRINCIPAL: Obtém contratos válidos para um período específico
        
        DIFERENÇA DA FUNÇÃO ANTERIOR:
        - Não filtra apenas por ativo=True
        - Verifica vigência real no período
        - Inclui contratos que estavam ativos mas agora estão inativos
        
        Args:
            mes_referencia: Mês da cobrança (1-12)
            ano_referencia: Ano da cobrança
            contratos_ids: Lista de IDs específicos (opcional)
            
        Returns:
            QuerySet: Contratos válidos para o período
        """
        try:
            # Calcular período da cobrança
            data_inicio_periodo = date(ano_referencia, mes_referencia, 1)
            ultimo_dia = calendar.monthrange(ano_referencia, mes_referencia)[1]
            data_fim_periodo = date(ano_referencia, mes_referencia, ultimo_dia)
            
            print(f"🔍 Buscando contratos válidos para {mes_referencia:02d}/{ano_referencia}")
            print(f"📅 Período: {data_inicio_periodo} até {data_fim_periodo}")
            
            # Query base: todos os contratos (não apenas ativos!)
            queryset = Contrato.objects.all()
            
            # Filtrar apenas por IDs específicos se fornecidos
            if contratos_ids:
                queryset = queryset.filter(id__in=contratos_ids)
                print(f"📋 Filtrado por IDs: {contratos_ids}")
            
            # Aplicar filtros de vigência no período
            queryset = queryset.filter(
                # Contrato deve ter iniciado antes do fim do período
                data_inicio__lte=data_fim_periodo
            ).filter(
                # E deve ter uma das condições:
                Q(data_fim__isnull=True) |  # Sem data fim OU
                Q(data_fim__gte=data_inicio_periodo)  # Data fim depois do início do período
            )
            
            print(f"🔍 Query inicial encontrou {queryset.count()} contratos")
            
            # Validação adicional individual
            contratos_validos = []
            
            for contrato in queryset:
                valido, motivo = ContratoValidacaoService.contrato_estava_ativo_no_periodo(
                    contrato, mes_referencia, ano_referencia
                )
                
                if valido:
                    contratos_validos.append(contrato.id)
                    print(f"   ✅ Contrato #{contrato.id}: {motivo}")
                else:
                    print(f"   ❌ Contrato #{contrato.id}: {motivo}")
            
            # Retornar apenas os válidos
            resultado = Contrato.objects.filter(id__in=contratos_validos)
            
            print(f"🎯 RESULTADO: {resultado.count()} contratos válidos para o período")
            return resultado
            
        except Exception as e:
            print(f"❌ Erro ao buscar contratos: {e}")
            return Contrato.objects.none()
    
    @staticmethod
    def debug_contratos_especificos(contratos_ids, mes_referencia, ano_referencia):
        """
        Debug detalhado para contratos específicos
        """
        print(f"🧪 DEBUG: Contratos {contratos_ids} para {mes_referencia:02d}/{ano_referencia}")
        print("=" * 70)
        
        for contrato_id in contratos_ids:
            try:
                contrato = Contrato.objects.get(id=contrato_id)
                
                print(f"\n📋 CONTRATO #{contrato_id}")
                print(f"   - Status atual: {'Ativo' if contrato.ativo else 'Inativo'}")
                print(f"   - Vigência: {contrato.data_inicio} até {contrato.data_fim or 'indefinido'}")
                
                # Testar validação
                valido, motivo = ContratoValidacaoService.contrato_estava_ativo_no_periodo(
                    contrato, mes_referencia, ano_referencia
                )
                
                status = "✅ INCLUIR" if valido else "❌ EXCLUIR"
                print(f"   - Resultado: {status}")
                print(f"   - Motivo: {motivo}")
                
                # Verificar inquilino
                if contrato.inquilino.exists():
                    inquilino = contrato.inquilino.first()
                    nome = inquilino.nome or inquilino.razao_social
                    print(f"   - Inquilino: {nome}")
                
            except Contrato.DoesNotExist:
                print(f"\n❌ Contrato #{contrato_id} não encontrado")
            except Exception as e:
                print(f"\n❌ Erro no contrato #{contrato_id}: {e}")


# ===============================================
# FUNÇÕES DE TESTE E EXEMPLO
# ===============================================

def testar_validacao_contratos_5_e_6():
    """
    Teste específico para os contratos 5 e 6
    """
    print("🧪 TESTE: Validação Contratos 5 e 6")
    print("=" * 50)
    
    # Cenários de teste
    cenarios = [
        (3, 2025),  # Março 2025 - Contrato 5 deveria estar ativo
        (4, 2025),  # Abril 2025 - Transição entre contratos
        (7, 2025),  # Julho 2025 - Apenas contrato 6
    ]
    
    for mes, ano in cenarios:
        print(f"\n📅 CENÁRIO: {mes:02d}/{ano}")
        ContratoValidacaoService.debug_contratos_especificos([5, 6], mes, ano)


def aplicar_nova_validacao_no_preview():
    """
    Como aplicar a nova validação na função de preview
    """
    codigo_exemplo = '''
def cobranca_api_preview_CORRIGIDO(request):
    """
    Preview de cobranças usando validação por período específico
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            mes_referencia = data.get('mes_referencia')
            ano_referencia = data.get('ano_referencia')
            
            # ⭐ USAR NOVA VALIDAÇÃO
            contratos_validos = ContratoValidacaoService.obter_contratos_validos_periodo(
                mes_referencia, ano_referencia
            )
            
            print(f"🎯 Contratos válidos encontrados: {contratos_validos.count()}")
            
            cobrancas_preview = []
            
            for contrato in contratos_validos:
                # Verificar se já existe cobrança
                if not Cobranca.objects.filter(
                    contrato=contrato,
                    mes_referencia=mes_referencia,
                    ano_referencia=ano_referencia
                ).exists():
                    
                    # Processar cobrança normalmente
                    # ... resto da lógica de cálculo
                    pass
            
            return JsonResponse({
                'success': True,
                'cobrancas': cobrancas_preview,
                'metodo': 'Validação por período específico'
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    '''
    
    print("📝 CÓDIGO DE EXEMPLO PARA IMPLEMENTAÇÃO:")
    print(codigo_exemplo)


if __name__ == "__main__":
    # Executar teste
    testar_validacao_contratos_5_e_6()
    print("\n" + "="*70)
    aplicar_nova_validacao_no_preview()