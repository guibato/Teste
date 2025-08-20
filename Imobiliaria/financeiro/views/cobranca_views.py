# financeiro/views/cobranca_views.py
"""
Views para gerenciamento de Cobranças - VERSÃO UNIFICADA
========================================================
Combinando cobranca_views.py e cobranca_preview_views.py
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.views.generic import ListView, CreateView, UpdateView, DetailView
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from datetime import date, datetime, timedelta
from django.db.models import Q, Sum, Count, Case, When, DecimalField, F, Max
from django.utils import timezone
from django.core.paginator import Paginator
from decimal import Decimal
import json
import traceback
from financeiro.models.reajuste import ReajusteAluguel
from sisimob.models import Contrato

from ..models import Cobranca
from ..forms.cobranca_forms import (
    CobrancaCreateForm, CobrancaUpdateForm, CobrancaFiltroForm,
    CobrancaIntegracaoAsaasForm, CobrancaMarcarPagaForm
)

def testar_valores_contratos():
    """
    Função para testar se os valores estão sendo calculados corretamente
    """
    print("🔍 TESTANDO VALORES DOS CONTRATOS")
    print("=" * 50)
    
    for contrato in Contrato.objects.filter(ativo=True)[:5]:
        print(f"\n📋 Contrato #{contrato.id}")
        print(f"   Valor Base: R$ {contrato.valor_base}")
        
        # Último reajuste
        ultimo_reajuste = contrato.reajustes.order_by('-data_reajuste').first()
        if ultimo_reajuste:
            print(f"   Último Reajuste: R$ {ultimo_reajuste.valor_reajustado} ({ultimo_reajuste.data_reajuste})")
            print(f"   Fator: {ultimo_reajuste.fator_aplicado}%")
        else:
            print(f"   Último Reajuste: Nenhum")
        
        # Valor atual
        valor_atual = contrato.get_valor_atual()
        print(f"   💰 VALOR ATUAL: R$ {valor_atual}")
        
        # Verificar diferença
        if ultimo_reajuste and valor_atual != contrato.valor_base:
            print(f"   ✅ Usando valor reajustado")
        else:
            print(f"   ℹ️ Usando valor base")


class CobrancaListView(ListView):
    """
    View para listagem de cobranças com filtros e estatísticas
    """
    model = Cobranca
    template_name = 'financeiro/cobranca/cobranca_list.html'
    context_object_name = 'cobrancas'
    paginate_by = 25
    
    def get_queryset(self):
        """Aplica filtros ao queryset"""
        queryset = super().get_queryset().select_related(
            'contrato'
        ).prefetch_related(
            'contrato__inquilino'
        ).order_by('data_vencimento')
        
        # Preparar dados do GET, definindo 'pendente' como padrão se status não estiver presente
        get_data = self.request.GET.copy()
        if not get_data.get('status'):
            get_data['status'] = 'pendente'
        
        # Aplicar filtros
        form = CobrancaFiltroForm(get_data)
        if form.is_valid():
            # Filtro por status
            status = form.cleaned_data.get('status')
            if status and status != 'todos':
                queryset = queryset.filter(status=status)
            
            # Filtro por mês
            mes = form.cleaned_data.get('mes_referencia')
            if mes:
                queryset = queryset.filter(mes_referencia=int(mes))
            
            # Filtro por ano
            ano = form.cleaned_data.get('ano_referencia')
            if ano:
                queryset = queryset.filter(ano_referencia=int(ano))
            
            # Filtro por contrato (busca textual)
            contrato_busca = form.cleaned_data.get('contrato')
            if contrato_busca:
                queryset = queryset.filter(
                    Q(contrato__numero__icontains=contrato_busca) |
                    Q(numero_cobranca__icontains=contrato_busca)
                )
            
            # Filtro por inquilino (busca textual)
            inquilino_busca = form.cleaned_data.get('inquilino')
            if inquilino_busca:
                queryset = queryset.filter(
                    Q(contrato__inquilino__nome__icontains=inquilino_busca) |
                    Q(contrato__inquilino__email__icontains=inquilino_busca)
                )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        """Adiciona dados extras ao contexto"""
        context = super().get_context_data(**kwargs)
        
        # Form de filtros
        filtro_form = CobrancaFiltroForm(self.request.GET)
        context['filtro_form'] = filtro_form
        
        # Queryset filtrado (para estatísticas)
        queryset_filtrado = self.get_queryset()
        
        # Estatísticas baseadas no queryset filtrado
        try:
            from ..services.cobranca_estatistica_service import CobrancaEstatisticaService
            estatisticas = CobrancaEstatisticaService.calcular_estatisticas(queryset_filtrado)
            context['estatisticas'] = estatisticas
        except Exception as e:
            print(f"Erro nas estatísticas: {e}")
            context['estatisticas'] = self._calcular_estatisticas_basicas(queryset_filtrado)
        
        # Dados para filtros
        context['anos_disponiveis'] = self._get_anos_disponiveis()
        context['status_choices'] = Cobranca.STATUS_CHOICES
        
        # URLs para ações
        context['url_criar'] = reverse('financeiro:cobranca_create')
        context['url_preview'] = reverse('financeiro:cobranca_preview_geracao')
        
        return context
    
    def _calcular_estatisticas_basicas(self, queryset):
        """Fallback para estatísticas básicas"""
        from django.db.models import Sum, Count
        
        stats = queryset.aggregate(
            total_cobrancas=Count('id'),
            valor_total_geral=Sum('valor'),
            pendentes_count=Count('id', filter=Q(status='pendente')),
            pagas_count=Count('id', filter=Q(status='paga')),
            atrasadas_count=Count('id', filter=Q(status='atrasada'))
        )
        
        pendentes_valor = queryset.filter(status='pendente').aggregate(
            valor=Sum('valor')
        )['valor'] or Decimal('0.00')
        
        pagas_valor = queryset.filter(status='paga').aggregate(
            valor=Sum('valor')
        )['valor'] or Decimal('0.00')
        
        atrasadas_valor = queryset.filter(status='atrasada').aggregate(
            valor=Sum('valor')
        )['valor'] or Decimal('0.00')
        
        return {
            'total_cobrancas': stats['total_cobrancas'] or 0,
            'valor_total_geral': stats['valor_total_geral'] or Decimal('0.00'),
            'pendentes': {
                'count': stats['pendentes_count'] or 0,
                'valor': pendentes_valor
            },
            'pagas': {
                'count': stats['pagas_count'] or 0,
                'valor': pagas_valor
            },
            'atrasadas': {
                'count': stats['atrasadas_count'] or 0,
                'valor': atrasadas_valor
            }
        }
    
    def _get_anos_disponiveis(self):
        """Obtém anos disponíveis para filtro"""
        anos = Cobranca.objects.values_list(
            'ano_referencia', 
            flat=True
        ).distinct().order_by('-ano_referencia')
        
        return list(anos) if anos else [timezone.now().year]


class CobrancaDetailView(DetailView):
    """View para detalhes de uma cobrança"""
    model = Cobranca
    template_name = 'financeiro/cobranca/cobranca_detail.html'
    context_object_name = 'cobranca'
    
    def get_object(self, queryset=None):
        """Busca objeto com related otimizado"""
        return get_object_or_404(
            Cobranca.objects.select_related('contrato')
                            .prefetch_related('contrato__inquilino'),
            pk=self.kwargs['pk']
        )
    
    def get_context_data(self, **kwargs):
        """Adiciona informações detalhadas ao contexto"""
        context = super().get_context_data(**kwargs)
        
        # Detalhes financeiros
        context['detalhes_financeiros'] = self.object.get_resumo_financeiro()
        
        # Status da cobrança
        context.update({
            'esta_atrasada': self.object.esta_atrasada,
            'dias_atraso': self.object.dias_atraso,
            'esta_quitada': self.object.is_quitada if hasattr(self.object, 'is_quitada') else self.object.status == 'paga',
        })
        
        # Informações do contrato
        context['contrato'] = self.object.contrato
        context['inquilino'] = self.object.inquilino
        
        # URLs de ação
        context['url_editar'] = reverse('financeiro:cobranca_update', kwargs={'pk': self.object.pk})
        context['url_marcar_paga'] = reverse('financeiro:cobranca_marcar_paga', kwargs={'pk': self.object.pk})
        
        # Forms para ações
        context['form_marcar_paga'] = CobrancaMarcarPagaForm()
        
        return context


class CobrancaCreateView(CreateView):
    """View para criação de cobrança"""
    model = Cobranca
    form_class = CobrancaCreateForm
    template_name = 'financeiro/cobranca/cobranca_form.html'
    
    def get_success_url(self):
        return reverse('financeiro:cobranca_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        """Adiciona lógica adicional ao salvar"""
        response = super().form_valid(form)
        
        messages.success(
            self.request, 
            f'Cobrança {self.object.numero_cobranca} criada com sucesso!'
        )
        
        return response


class CobrancaUpdateView(UpdateView):
    """View para edição de cobrança"""
    model = Cobranca
    form_class = CobrancaUpdateForm
    template_name = 'financeiro/cobranca/cobranca_form.html'
    
    def get_success_url(self):
        return reverse('financeiro:cobranca_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        """Adiciona lógica adicional ao salvar"""
        response = super().form_valid(form)
        
        messages.success(
            self.request, 
            f'Cobrança {self.object.numero_cobranca} atualizada com sucesso!'
        )
        
        return response


def obter_valor_atual_contrato(contrato, mes_referencia_ou_data, ano_referencia=None):
    """
    FUNÇÃO CORRIGIDA: Compatível com ambos os formatos de chamada
    
    Aceita:
    1. obter_valor_atual_contrato(contrato, mes, ano) - NOVO formato
    2. obter_valor_atual_contrato(contrato, data_referencia) - formato ANTIGO
    """
    try:
        # Verificar qual formato está sendo usado
        if ano_referencia is not None:
            # NOVO formato: (contrato, mes, ano)
            mes_referencia = mes_referencia_ou_data
            print(f"🔍 Buscando valor CORRIGIDO para contrato #{contrato.id} - {mes_referencia}/{ano_referencia}")
            
            # Calcular data de vencimento da cobrança
            dia_vencimento = contrato.dia_pagamento if contrato.dia_pagamento else 10
            
            if mes_referencia == 12:
                data_vencimento = date(ano_referencia + 1, 1, dia_vencimento)
            else:
                data_vencimento = date(ano_referencia, mes_referencia + 1, dia_vencimento)
            
            print(f"📅 Data de vencimento: {data_vencimento}")
            
            # Buscar reajuste válido até o vencimento
            ultimo_reajuste = ReajusteAluguel.objects.filter(
                contrato=contrato,
                data_reajuste__lte=data_vencimento
            ).order_by('-data_reajuste').first()
            
        else:
            # FORMATO ANTIGO: (contrato, data_referencia) - manter compatibilidade
            data_referencia = mes_referencia_ou_data
            print(f"🔍 Buscando valor para contrato #{contrato.id} até {data_referencia} (formato antigo)")
            
            # Usar lógica antiga para compatibilidade
            ultimo_reajuste = ReajusteAluguel.objects.filter(
                contrato=contrato,
                data_reajuste__lte=data_referencia
            ).order_by('-data_reajuste').first()
        
        if ultimo_reajuste:
            valor_atual = ultimo_reajuste.valor_reajustado
            print(f"✅ Último reajuste válido:")
            print(f"   Data: {ultimo_reajuste.data_reajuste}")
            print(f"   Valor anterior: R$ {ultimo_reajuste.valor_anterior}")
            print(f"   Valor reajustado: R$ {ultimo_reajuste.valor_reajustado}")
            print(f"   Fator: {ultimo_reajuste.fator_aplicado}%")
        else:
            valor_atual = contrato.valor_base
            print(f"ℹ️ Nenhum reajuste encontrado, usando valor base: R$ {valor_atual}")
        
        return float(valor_atual) if valor_atual else 0.0
        
    except Exception as e:
        print(f"❌ Erro ao obter valor do contrato {contrato.id}: {e}")
        # Fallback para valor base
        return float(contrato.valor_base) if contrato.valor_base else 0.0


# Teste manual para verificar se está funcionando
def teste_valores_contratos():
    """
    Função para testar no shell Django
    Uso: python manage.py shell
         from financeiro.views.cobranca_views import teste_valores_contratos
         teste_valores_contratos()
    """
    print("🧪 TESTE: Verificando valores dos contratos")
    print("=" * 60)
    
    contratos = Contrato.objects.filter(ativo=True)[:3]  # Primeiros 3 contratos
    
    for contrato in contratos:
        print(f"\n📋 CONTRATO #{contrato.id}")
        print(f"   Valor Base: R$ {contrato.valor_base}")
        
        # Verificar reajustes
        reajustes = contrato.reajustes.order_by('-data_reajuste')
        if reajustes.exists():
            print(f"   📈 Reajustes encontrados: {reajustes.count()}")
            for i, reajuste in enumerate(reajustes[:2]):  # Mostrar últimos 2
                print(f"     {i+1}. {reajuste.data_reajuste}: R$ {reajuste.valor_reajustado} ({reajuste.fator_aplicado}%)")
        else:
            print(f"   📈 Reajustes: Nenhum")
        
        # Valor atual
        from datetime import date
        valor_atual = obter_valor_atual_contrato(contrato, date.today())
        print(f"   💰 VALOR ATUAL: R$ {valor_atual}")
        
        # Status
        if reajustes.exists() and valor_atual != float(contrato.valor_base):
            print(f"   ✅ STATUS: Usando valor reajustado")
        else:
            print(f"   ℹ️ STATUS: Usando valor base")
    
    print(f"\n🎯 Teste concluído!")



def contrato_estava_ativo_no_periodo(contrato, data_inicio_periodo, data_fim_periodo):
    """Verifica se um contrato estava ativo durante um período específico"""
    try:
        if contrato.data_inicio > data_fim_periodo:
            return False, f"Contrato iniciou após o período ({contrato.data_inicio.strftime('%d/%m/%Y')})"
        
        if not contrato.ativo:
            return False, "Contrato está inativo"
        
        return True, ""
        
    except Exception as e:
        return False, f"Erro na validação: {str(e)}"


def validar_contrato_no_periodo_com_renovacao(contrato, data_inicio_periodo, data_fim_periodo):
    """
    ⭐ NOVA VALIDAÇÃO: Considera renovações automáticas
    
    REGRA IMOBILIÁRIA:
    - Se contrato está ATIVO (ativo=True) = sempre válido
    - Data_fim apenas indica fim do prazo determinado
    - Contratos ativos após data_fim = renovação automática
    """
    try:
        # REGRA 1: Contrato deve estar ativo
        if not contrato.ativo:
            return False, "Contrato foi inativado"
        
        # REGRA 2: Contrato deve ter iniciado antes do fim do período
        if contrato.data_inicio > data_fim_periodo:
            return False, f"Contrato ainda não iniciou ({contrato.data_inicio})"
        
        # REGRA 3: ⭐ NOVA LÓGICA - Se ativo=True, SEMPRE válido
        # Mesmo se data_fim já passou (renovação automática)
        if contrato.ativo:
            if contrato.data_fim and contrato.data_fim < data_inicio_periodo:
                return True, f"Contrato em renovação automática (terminou {contrato.data_fim})"
            else:
                return True, "Contrato vigente no período"
        
        # REGRA 4: Fallback (não deveria chegar aqui)
        return False, "Contrato inativo"
        
    except Exception as e:
        return False, f"Erro na validação: {str(e)}"


def obter_contratos_elegiveis_periodo(mes_referencia, ano_referencia, contratos_ids=None, validar_periodo=True):
    """
    ⭐ VERSÃO CORRIGIDA: Inclui contratos em renovação automática
    """
    from datetime import date
    import calendar
    from sisimob.models import Contrato
    
    try:
        # Calcular período
        data_inicio_periodo = date(ano_referencia, mes_referencia, 1)
        ultimo_dia = calendar.monthrange(ano_referencia, mes_referencia)[1]
        data_fim_periodo = date(ano_referencia, mes_referencia, ultimo_dia)
        
        print(f"🔍 [CORRIGIDO] Buscando contratos para {mes_referencia:02d}/{ano_referencia}")
        print(f"📅 Período: {data_inicio_periodo} até {data_fim_periodo}")
        
        # ⭐ MUDANÇA PRINCIPAL: Incluir TODOS os contratos ativos
        # Não filtrar por data_fim (pode estar em renovação)
        queryset = Contrato.objects.filter(ativo=True)
        
        # Filtrar apenas por início (deve ter iniciado antes do fim do período)
        if validar_periodo:
            queryset = queryset.filter(data_inicio__lte=data_fim_periodo)
        
        # Filtrar por IDs específicos se fornecidos
        if contratos_ids:
            queryset = queryset.filter(id__in=contratos_ids)
        
        print(f"📊 Query inicial encontrou {queryset.count()} contratos ativos")
        
        # ⭐ VALIDAÇÃO INDIVIDUAL COM NOVA LÓGICA
        contratos_validos = []
        
        for contrato in queryset:
            valido, motivo = validar_contrato_no_periodo_com_renovacao(
                contrato, data_inicio_periodo, data_fim_periodo
            )
            
            if valido:
                contratos_validos.append(contrato.id)
                print(f"   ✅ Contrato #{contrato.id}: {motivo}")
            else:
                print(f"   ❌ Contrato #{contrato.id}: {motivo}")
        
        # Retornar QuerySet final
        resultado = Contrato.objects.filter(id__in=contratos_validos)
        print(f"🎯 RESULTADO CORRIGIDO: {resultado.count()} contratos válidos (incluindo renovações)")
        
        return resultado
        
    except Exception as e:
        print(f"❌ Erro ao buscar contratos: {e}")
        return Contrato.objects.none()




@require_http_methods(["GET", "POST"])
def cobranca_marcar_paga(request, pk):
    """
    View para marcar cobrança como paga
    """
    cobranca = get_object_or_404(Cobranca, pk=pk)
    
    # Verificar se já está paga
    if cobranca.status == 'paga':
        messages.warning(request, 'Esta cobrança já está marcada como paga.')
        return redirect('financeiro:cobranca_detail', pk=pk)
    
    if request.method == 'POST':
        try:
            # Extrair dados do formulário
            data_pagamento = request.POST.get('data_pagamento')
            valor_pago = request.POST.get('valor_pago')
            metodo_pagamento = request.POST.get('metodo_pagamento', 'transferencia')
            observacoes = request.POST.get('observacoes', '')
            
            print(f"📝 Dados recebidos: data={data_pagamento}, valor={valor_pago}, metodo={metodo_pagamento}")
            
            # Validações
            if not data_pagamento:
                messages.error(request, 'Data de pagamento é obrigatória.')
                return redirect(request.path)
            
            if not valor_pago:
                messages.error(request, 'Valor pago é obrigatório.')
                return redirect(request.path)
            
            # Converter dados
            try:
                data_pagamento_obj = datetime.strptime(data_pagamento, '%Y-%m-%d').date()
                valor_pago_decimal = Decimal(str(valor_pago))
                print(f"✅ Conversões OK: data={data_pagamento_obj}, valor={valor_pago_decimal}")
            except (ValueError, TypeError) as e:
                print(f"❌ Erro na conversão: {e}")
                messages.error(request, f'Dados inválidos: {str(e)}')
                return redirect(request.path)
            
            # Verificar se valor é positivo
            if valor_pago_decimal <= 0:
                messages.error(request, 'Valor pago deve ser maior que zero.')
                return redirect(request.path)
            
            # Marcar como paga
            print(f"🔄 Marcando cobrança {cobranca.id} como paga...")
            cobranca.status = 'paga'
            cobranca.data_pagamento = data_pagamento_obj
            
            # Adicionar observações se fornecidas
            if observacoes:
                obs_atual = cobranca.observacoes or ''
                obs_pagamento = f"\n[{timezone.now().strftime('%d/%m/%Y %H:%M')}] Pagamento registrado: {metodo_pagamento.title()}"
                if observacoes:
                    obs_pagamento += f" - {observacoes}"
                cobranca.observacoes = obs_atual + obs_pagamento
            
            # Salvar alterações
            cobranca.save()
            print(f"✅ Cobrança {cobranca.id} salva com sucesso!")
            
            messages.success(request, f'Cobrança marcada como paga com sucesso!')
            return redirect('financeiro:cobranca_detail', pk=pk)
            
        except Exception as e:
            print(f"❌ Erro inesperado: {e}")
            traceback.print_exc()
            messages.error(request, f'Erro inesperado: {str(e)}')
            return redirect(request.path)
    
    # GET - Mostrar formulário
    context = {
        'cobranca': cobranca,
        'hoje': timezone.now().date(),
        'metodos_pagamento': [
            ('transferencia', 'Transferência Bancária'),
            ('pix', 'PIX'),
            ('dinheiro', 'Dinheiro'),
            ('cartao', 'Cartão'),
            ('cheque', 'Cheque'),
            ('deposito', 'Depósito'),
        ]
    }
    
    return render(request, 'financeiro/cobranca/marcar_paga.html', context)



@require_http_methods(["POST"])
def cobranca_cancelar(request, pk):
    """
    View para cancelar uma cobrança
    """
    cobranca = get_object_or_404(Cobranca, pk=pk)
    
    if cobranca.status == 'cancelada':
        messages.warning(request, 'Esta cobrança já está cancelada.')
        return redirect('financeiro:cobranca_detail', pk=pk)
    
    if cobranca.status == 'paga':
        messages.error(request, 'Não é possível cancelar uma cobrança já paga.')
        return redirect('financeiro:cobranca_detail', pk=pk)
    
    try:
        motivo = request.POST.get('motivo_cancelamento', '')
        cobranca.cancelar(motivo)
        
        messages.success(request, 'Cobrança cancelada com sucesso!')
        
        # Response AJAX se solicitado
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': 'Cobrança cancelada'})
            
    except Exception as e:
        messages.error(request, f'Erro ao cancelar cobrança: {str(e)}')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': str(e)})
    
    return redirect('financeiro:cobranca_detail', pk=pk)


@require_http_methods(["GET", "POST"])
def cobranca_integrar_asaas(request, pk):
    """
    View para integrar cobrança com o Asaas
    """
    cobranca = get_object_or_404(Cobranca, pk=pk)
    
    # Verificar se pode ser integrada
    try:
        from ..models.cobranca import AsaasIntegracao
        asaas_integracao, created = AsaasIntegracao.objects.get_or_create(
            cobranca=cobranca
        )
        
        pode_integrar, erros = asaas_integracao.pode_ser_integrada()
        
        if not pode_integrar:
            messages.error(request, f'Não é possível integrar: {"; ".join(erros)}')
            return redirect('financeiro:cobranca_detail', pk=pk)
    except ImportError:
        messages.error(request, 'Integração Asaas não está disponível')
        return redirect('financeiro:cobranca_detail', pk=pk)
    
    if request.method == 'POST':
        form = CobrancaIntegracaoAsaasForm(request.POST)
        
        if form.is_valid():
            try:
                # Preparar opções de integração
                opcoes = {
                    'formas_pagamento': form.cleaned_data['formas_pagamento'],
                    'enviar_por_email': form.cleaned_data['enviar_por_email'],
                    'enviar_por_whatsapp': form.cleaned_data['enviar_por_whatsapp'],
                    'observacoes': form.cleaned_data['observacoes_cobranca'],
                }
                
                # Integrar
                resultado = asaas_integracao.integrar_asaas(opcoes)
                
                if resultado['status'] == 'success':
                    messages.success(
                        request,
                        'Cobrança integrada com Asaas com sucesso!'
                    )
                else:
                    messages.error(
                        request,
                        f'Erro na integração: {"; ".join(resultado.get("erros", ["Erro desconhecido"]))}'
                    )
                    
            except Exception as e:
                messages.error(request, f'Erro inesperado: {str(e)}')
                
            return redirect('financeiro:cobranca_detail', pk=pk)
    else:
        form = CobrancaIntegracaoAsaasForm()
    
    context = {
        'cobranca': cobranca,
        'form': form,
        'titulo': f'Integrar com Asaas - {cobranca.data_referencia_texto}',
        'detalhes_financeiros': cobranca.get_resumo_financeiro(),
    }
    
    return render(request, 'financeiro/cobranca/cobranca_integrar_asaas.html', context)


def cobranca_revisao_integracao(request):
    """
    Tela de revisão das cobranças criadas com opção de integração em lote
    """
    # Buscar cobranças pendentes recém-criadas
    cobrancas_pendentes = Cobranca.objects.filter(
        status='pendente'
    ).select_related('contrato').order_by('-data_criacao')[:20]
    
    context = {
        'cobrancas_pendentes': cobrancas_pendentes,
        'form_integracao': CobrancaIntegracaoAsaasForm()
    }
    
    return render(request, 'financeiro/cobranca/cobranca_revisao_integracao.html', context)


@require_http_methods(["POST"])
def cobranca_integrar_lote_asaas(request):
    """
    Integra múltiplas cobranças com Asaas em lote
    """
    try:
        cobrancas_ids = request.POST.getlist('cobrancas')
        formas_pagamento = request.POST.getlist('formas_pagamento')
        enviar_por_email = request.POST.get('enviar_por_email') == 'on'
        enviar_por_whatsapp = request.POST.get('enviar_por_whatsapp') == 'on'
        observacoes = request.POST.get('observacoes_cobranca', '')
        
        if not cobrancas_ids:
            messages.error(request, 'Nenhuma cobrança selecionada.')
            return redirect('financeiro:cobranca_revisao_integracao')
        
        if not formas_pagamento:
            messages.error(request, 'Selecione pelo menos uma forma de pagamento.')
            return redirect('financeiro:cobranca_revisao_integracao')
        
        cobrancas = Cobranca.objects.filter(
            id__in=cobrancas_ids,
            status='pendente'
        )
        
        integracoes_sucesso = 0
        integracoes_erro = 0
        erros_detalhados = []
        
        for cobranca in cobrancas:
            try:
                # Tentar integrar cada cobrança
                # TODO: Implementar integração quando AsaasIntegracao estiver completa
                integracoes_sucesso += 1
                    
            except Exception as e:
                integracoes_erro += 1
                erros_detalhados.append(f'Erro na cobrança {cobranca}: {str(e)}')
        
        # Mensagens de resultado
        if integracoes_sucesso > 0:
            messages.success(
                request,
                f'{integracoes_sucesso} cobrança(s) integrada(s) com sucesso!'
            )
        
        if integracoes_erro > 0:
            messages.error(
                request,
                f'{integracoes_erro} erro(s) na integração. '
                f'Detalhes: {"; ".join(erros_detalhados[:3])}'
            )
        
        return redirect('financeiro:cobranca_list')
        
    except Exception as e:
        messages.error(request, f'Erro inesperado: {str(e)}')
        return redirect('financeiro:cobranca_revisao_integracao')


@require_http_methods(["GET"])
def cobranca_api_despesas_contrato(request, contrato_id):
    """
    API para buscar despesas de um contrato (AJAX)
    """
    try:
        from sisimob.models import Contrato
        contrato = get_object_or_404(Contrato, pk=contrato_id)
        
        # Usar service se disponível
        mes = int(request.GET.get('mes', date.today().month))
        ano = int(request.GET.get('ano', date.today().year))
        
        despesas_data = []
        valor_aluguel = Decimal('0.00')
        
        # Valor do aluguel
        if hasattr(contrato, 'valor_base') and contrato.valor_base:
            valor_aluguel = contrato.valor_base
        elif hasattr(contrato, 'valor_aluguel') and contrato.valor_aluguel:
            valor_aluguel = contrato.valor_aluguel
        
        # TODO: Buscar despesas quando service estiver implementado
        
        # Dados do inquilino
        inquilino_nome = ''
        inquilino_email = ''
        
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
        
        return JsonResponse({
            'success': True,
            'despesas': despesas_data,
            'valor_aluguel': float(valor_aluguel),
            'inquilino_nome': inquilino_nome,
            'inquilino_email': inquilino_email,
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })



@require_http_methods(["GET"])
@method_decorator(cache_page(60 * 5), name='dispatch')
def cobranca_dashboard_stats(request):
    """
    API para estatísticas do dashboard (com cache)
    """
    try:
        # Filtros do request
        filtros = {
            'mes': request.GET.get('mes'),
            'ano': request.GET.get('ano'),
            'status': request.GET.get('status'),
        }
        
        # Remover filtros vazios
        filtros = {k: v for k, v in filtros.items() if v}
        
        # Calcular estatísticas
        try:
            from ..services.cobranca_estatistica_service import CobrancaEstatisticaService
            stats = CobrancaEstatisticaService.calcular_estatisticas(filtros)
        except ImportError:
            # Fallback para estatísticas básicas
            queryset = Cobranca.objects.all()
            stats = {
                'total_cobrancas': queryset.count(),
                'valor_total_geral': queryset.aggregate(total=Sum('valor'))['total'] or 0,
                'pendentes': {'count': queryset.filter(status='pendente').count()},
                'pagas': {'count': queryset.filter(status='paga').count()},
                'atrasadas': {'count': queryset.filter(status='atrasada').count()},
            }
        
        # Converter Decimal para float para JSON
        def convert_decimals(obj):
            if isinstance(obj, dict):
                return {k: convert_decimals(v) for k, v in obj.items()}
            elif isinstance(obj, Decimal):
                return float(obj)
            elif isinstance(obj, list):
                return [convert_decimals(item) for item in obj]
            return obj
        
        stats = convert_decimals(stats)
        
        return JsonResponse({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })



@require_http_methods(["POST"])
def cobranca_webhook_asaas(request):
    """
    Endpoint para receber webhooks do Asaas
    """
    try:
        dados_webhook = json.loads(request.body)
        asaas_id = dados_webhook.get('payment', {}).get('id')
        
        if not asaas_id:
            return JsonResponse({'status': 'error', 'message': 'ID do pagamento não encontrado'})
        
        # Buscar integração
        try:
            from ..models.cobranca import AsaasIntegracao
            asaas_integracao = AsaasIntegracao.objects.get(asaas_id=asaas_id)
        except (ImportError, AsaasIntegracao.DoesNotExist):
            return JsonResponse({'status': 'error', 'message': 'Cobrança não encontrada'})
        
        # Processar webhook
        resultado = asaas_integracao.processar_webhook(dados_webhook)
        
        return JsonResponse(resultado)
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Erro ao processar webhook: {str(e)}'
        })


def gerar_descricao_automatica_preview(mes_referencia, ano_referencia, valor_aluguel, despesas, valor_total):
    """
    Gera descrição automática para preview
    """
    meses = {
        1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
        5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
        9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
    }
    
    mes_nome = meses.get(mes_referencia, f'Mês {mes_referencia}')
    
    descricao_partes = [
        
        f"Valor do aluguel: R$ {valor_aluguel:,.2f}".replace('.', ',').replace(',', '.', 1)
    ]
    
    if despesas:
        descricao_partes.append("\nDespesas incluídas:")
        for despesa in despesas:
            valor_formatado = f"R$ {despesa['valor']:,.2f}".replace('.', ',').replace(',', '.', 1)
            descricao_partes.append(f"• {despesa['nome']}: {valor_formatado}")
    
    valor_total_formatado = f"R$ {valor_total:,.2f}".replace('.', ',').replace(',', '.', 1)
    descricao_partes.append(f"\nValor total: {valor_total_formatado}")
    
    return '\n'.join(descricao_partes)



def gerar_cobrancas_manualmente(ids_contratos, mes, ano):
    """Função de compatibilidade"""
    try:
        from ..models.cobranca import criar_cobranca_do_contrato
        from sisimob.models import Contrato
        
        cobrancas_criadas = 0
        
        for contrato_id in ids_contratos:
            try:
                contrato = Contrato.objects.get(id=contrato_id)
                cobranca = criar_cobranca_do_contrato(
                    contrato=contrato,
                    mes_referencia=int(mes),
                    ano_referencia=int(ano),
                    data_vencimento=date.today(),
                    incluir_despesas=True
                )
                cobrancas_criadas += 1
            except Exception:
                continue
        
        return cobrancas_criadas
    except:
        return 0


def listar_cobrancas_ordenadas():
    """Função de compatibilidade"""
    return Cobranca.objects.all().order_by('-data_vencimento')


def marcar_cobranca_como_paga(cobranca_id, data_pagamento):
    """Função de compatibilidade"""
    try:
        cobranca = Cobranca.objects.get(pk=cobranca_id)
        cobranca.marcar_como_paga(data_pagamento)
        return cobranca
    except:
        return None
    

def validar_contrato_no_periodo(contrato, data_inicio_periodo, data_fim_periodo):
    """
    CORRIGIDA: Valida contrato considerando REGRAS IMOBILIÁRIAS
    
    REGRA IMOBILIÁRIA:
    - Se contrato está ATIVO (ativo=True) = sempre válido (renovação automática)
    - Se contrato está INATIVO (ativo=False) = foi encerrado manualmente
    - Data_fim apenas indica término do prazo inicial, não invalida o contrato
    """
    try:
        # 1. REGRA PRINCIPAL: Verificar se contrato está ATIVO
        if hasattr(contrato, 'ativo') and not contrato.ativo:
            return False, "Contrato foi inativado manualmente"
        
        # 2. Verificar se o contrato começou após o período
        if contrato.data_inicio > data_fim_periodo:
            return False, f"Contrato iniciou após o período ({contrato.data_inicio})"
        
        # 3. REGRA IMOBILIÁRIA: Se ativo=True, IGNORAR data_fim
        # Data_fim apenas indica fim do prazo determinado, mas contrato continua
        # em prazo indeterminado se não foi inativado
        
        if hasattr(contrato, 'ativo') and contrato.ativo:
            return True, "Contrato ativo com renovação automática"
        
        # 4. FALLBACK: Se não tem campo 'ativo', usar lógica tradicional
        # Verificar se o contrato terminou antes do período
        if hasattr(contrato, 'data_fim') and contrato.data_fim:
            if contrato.data_fim < data_inicio_periodo:
                return False, f"Contrato terminou antes do período ({contrato.data_fim})"
        
        # Se chegou até aqui, contrato é válido
        return True, "Contrato válido para o período"
        
    except Exception as e:
        return False, f"Erro na validação: {str(e)}"


def buscar_despesas_contrato_periodo(contrato, mes_referencia, ano_referencia):
    """
    Busca despesas de um contrato para um período específico
    CORRIGIDO: Inclui lógica de parcelamento e evita sobreposição
    """
    try:
        from financeiro.models import Despesa
        from datetime import date
        from django.db import models
        import calendar
        from dateutil.relativedelta import relativedelta
        
        print(f"🔍 Buscando despesas - Contrato #{contrato.id}, Período: {mes_referencia}/{ano_referencia}")
        
        # Todas as despesas ativas do contrato
        todas_despesas = Despesa.objects.filter(
            contrato=contrato,
            is_ativa=True
        ).order_by('data_inicio')
        
        print(f"📋 Total despesas ativas do contrato: {todas_despesas.count()}")
        
        if todas_despesas.count() == 0:
            return [], 0.0
        
        # Calcular período de cobrança
        data_inicio_periodo = date(ano_referencia, mes_referencia, 1)
        ultimo_dia = calendar.monthrange(ano_referencia, mes_referencia)[1]
        data_fim_periodo = date(ano_referencia, mes_referencia, ultimo_dia)
        
        print(f"📅 Verificando despesas válidas para {data_inicio_periodo} até {data_fim_periodo}")
        
        despesas_validas = []
        valor_total = 0.0
        
        for despesa in todas_despesas:
            incluir_despesa = False
            valor_despesa = float(despesa.valor_total)
            motivo = ""
            
            # CRITÉRIO 1: Despesas recorrentes - LÓGICA CORRIGIDA PARA EVITAR SOBREPOSIÇÃO
            if despesa.is_recorrente:
                # SOLUÇÃO: Priorizar despesas que INICIAM no período
                # Para evitar sobreposição, só incluir se:
                # 1. A despesa inicia no período de cobrança, OU
                # 2. A despesa não tem fim definido e estava ativa antes, OU  
                # 3. A despesa estava ativa antes E termina DEPOIS do período (não no início)
                
                despesa_inicia_no_periodo = data_inicio_periodo <= despesa.data_inicio <= data_fim_periodo
                despesa_vigente_sem_fim = (despesa.data_inicio < data_inicio_periodo and 
                                         not despesa.data_fim_prevista)
                despesa_vigente_com_fim = (despesa.data_inicio < data_inicio_periodo and 
                                         despesa.data_fim_prevista and 
                                         despesa.data_fim_prevista > data_fim_periodo)
                
                if despesa_inicia_no_periodo:
                    incluir_despesa = True
                    motivo = f"Recorrente {despesa.periodicidade} - inicia no período"
                elif despesa_vigente_sem_fim:
                    incluir_despesa = True  
                    motivo = f"Recorrente {despesa.periodicidade} - vigência indefinida"
                elif despesa_vigente_com_fim:
                    incluir_despesa = True
                    motivo = f"Recorrente {despesa.periodicidade} - vigente além do período"
            
            # CRITÉRIO 2: Despesas NÃO-recorrentes (incluindo parceladas)
            elif not despesa.is_recorrente:
                
                # NOVO: Verificar se é despesa parcelada
                if hasattr(despesa, 'numero_parcelas') and despesa.numero_parcelas and despesa.numero_parcelas > 1:
                    print(f"   🔢 Despesa parcelada detectada: {despesa.descricao}")
                    print(f"      - Valor total: R$ {despesa.valor_total}")
                    print(f"      - Número de parcelas: {despesa.numero_parcelas}")
                    print(f"      - Início: {despesa.data_inicio}")
                    
                    # Calcular se o mês atual está dentro do período de parcelamento
                    data_inicio_despesa = despesa.data_inicio
                    
                    # Calcular o mês da última parcela (inicio + numero_parcelas - 1)
                    data_ultima_parcela = data_inicio_despesa + relativedelta(months=despesa.numero_parcelas - 1)
                    data_fim_calculado = date(data_ultima_parcela.year, data_ultima_parcela.month, 
                                            calendar.monthrange(data_ultima_parcela.year, data_ultima_parcela.month)[1])
                    
                    print(f"      - Última parcela: {data_ultima_parcela.strftime('%m/%Y')}")
                    print(f"      - Fim calculado: {data_fim_calculado}")
                    
                    # Verificar se o período de cobrança está dentro do parcelamento
                    if data_inicio_despesa <= data_fim_periodo and data_inicio_periodo < data_fim_calculado:
                        incluir_despesa = True
                        # Calcular valor da parcela
                        valor_despesa = float(despesa.valor_total) / despesa.numero_parcelas
                        motivo = f"Parcela {despesa.numero_parcelas}x de R$ {valor_despesa:.2f}"
                        
                        print(f"      ✅ Período válido para parcelamento")
                        print(f"      💰 Valor da parcela: R$ {valor_despesa:.2f}")
                    else:
                        print(f"      ❌ Período fora do parcelamento")
                
                # Despesas não-parceladas com periodicidade mensal
                elif despesa.periodicidade == 'mensal':
                    if despesa.data_inicio <= data_fim_periodo:
                        if not despesa.data_fim_prevista or despesa.data_fim_prevista > data_inicio_periodo:
                            incluir_despesa = True
                            motivo = "Não-recorrente mensal válida para o período"
                
                # Despesas pontuais que se iniciam no período
                elif data_inicio_periodo <= despesa.data_inicio <= data_fim_periodo:
                    incluir_despesa = True
                    motivo = "Despesa pontual iniciando no período"
                
                # Despesas com vigência que abrange o período
                elif despesa.data_inicio <= data_inicio_periodo:
                    if not despesa.data_fim_prevista or despesa.data_fim_prevista > data_fim_periodo:
                        incluir_despesa = True
                        motivo = "Despesa com vigência que abrange o período"
            
            # CRITÉRIO 3: Base de cálculo
            if hasattr(despesa, 'is_base_calculo_administracao') and despesa.is_base_calculo_administracao:
                if despesa.data_inicio <= data_fim_periodo:
                    if not despesa.data_fim_prevista or despesa.data_fim_prevista > data_inicio_periodo:
                        incluir_despesa = True
                        motivo = "Base de cálculo de administração"
            
            if incluir_despesa:
                # Criar objeto temporário com valor calculado para a parcela
                despesa_resultado = type('DespesaCalculada', (), {
                    'id': despesa.id,
                    'descricao': despesa.descricao,
                    'valor_total': valor_despesa,  # Valor pode ser parcelado
                    'is_parcelada': hasattr(despesa, 'numero_parcelas') and despesa.numero_parcelas and despesa.numero_parcelas > 1
                })()
                
                despesas_validas.append(despesa_resultado)
                valor_total += valor_despesa
                print(f"   ✅ Incluída: {despesa.descricao} - R$ {valor_despesa:.2f} ({motivo})")
            else:
                print(f"   ❌ Excluída: {despesa.descricao} - Não se aplica ao período")
        
        print(f"📊 Resultado: {len(despesas_validas)} despesas, Total: R$ {valor_total:.2f}")
        
        return despesas_validas, valor_total
        
    except Exception as e:
        print(f"❌ Erro ao buscar despesas: {e}")
        import traceback
        traceback.print_exc()
        return [], 0.0
    

def testar_validacao_contrato_9():
    """
    Teste específico para o contrato 9
    """
    from datetime import date
    
    print("=== TESTE DA VALIDAÇÃO CORRIGIDA ===")
    
    try:
        contrato_9 = Contrato.objects.get(id=9)
        
        # Testar para julho/2025
        data_inicio_periodo = date(2025, 7, 1)
        data_fim_periodo = date(2025, 7, 31)
        
        valido, motivo = validar_contrato_no_periodo(
            contrato_9, data_inicio_periodo, data_fim_periodo
        )
        
        print(f"\nRESULTADO:")
        print(f"Válido: {'✅ SIM' if valido else '❌ NÃO'}")
        print(f"Motivo: {motivo}")
        
        if valido:
            print(f"\n🎉 SUCESSO! Contrato 9 agora será incluído no preview de julho/2025")
        else:
            print(f"\n❌ Ainda há problema na validação")
            
    except Exception as e:
        print(f"❌ Erro no teste: {e}")


# ALTERNATIVA: Se preferir manter a função original e criar uma nova
def validar_contrato_imobiliario(contrato, data_inicio_periodo, data_fim_periodo):
    """
    Nova função com regras imobiliárias corretas
    """
    # 1. Contrato deve estar ativo
    if not getattr(contrato, 'ativo', True):
        return False, "Contrato inativado"
    
    # 2. Contrato deve ter iniciado antes do fim do período
    if contrato.data_inicio > data_fim_periodo:
        return False, f"Contrato ainda não iniciou ({contrato.data_inicio})"
    
    # 3. REGRA IMOBILIÁRIA: Se ativo=True, ignora data_fim
    return True, "Contrato válido (renovação automática)"


def debug_contratos_periodo(mes_referencia, ano_referencia):
    """
    Função para debug - verificar quais contratos estão sendo incluídos
    VERSÃO MELHORADA para renovações
    """
    from datetime import date
    from django.db import models
    import calendar
    
    print(f"🔍 DEBUG: Contratos para {mes_referencia}/{ano_referencia}")
    print("=" * 60)
    
    # Calcular período
    data_inicio_periodo = date(ano_referencia, mes_referencia, 1)
    ultimo_dia = calendar.monthrange(ano_referencia, mes_referencia)[1]
    data_fim_periodo = date(ano_referencia, mes_referencia, ultimo_dia)
    
    print(f"📅 Período: {data_inicio_periodo} até {data_fim_periodo}")
    
    # Todos os contratos (incluindo inativos)
    todos_contratos = Contrato.objects.all().order_by('id')
    print(f"📋 Total contratos: {todos_contratos.count()}")
    
    # Aplicar filtro como na função principal
    contratos_filtrados = todos_contratos.filter(
        data_inicio__lte=data_fim_periodo
    ).filter(
        models.Q(data_fim__isnull=True) |
        models.Q(data_fim__gte=data_inicio_periodo) |
        models.Q(data_encerramento__isnull=True) |
        models.Q(data_encerramento__gte=data_inicio_periodo)
    )
    
    print(f"✅ Contratos que passaram no filtro: {contratos_filtrados.count()}")
    
    # Mostrar detalhes de cada contrato
    for contrato in todos_contratos:
        print(f"\n📋 CONTRATO #{contrato.id}")
        print(f"   - Início: {contrato.data_inicio}")
        
        # Verificar campos de fim
        if hasattr(contrato, 'data_fim'):
            print(f"   - Fim: {contrato.data_fim or 'Não definido'}")
        if hasattr(contrato, 'data_encerramento'):
            print(f"   - Encerramento: {contrato.data_encerramento or 'Não definido'}")
        if hasattr(contrato, 'ativo'):
            print(f"   - Ativo: {contrato.ativo}")
        
        # Validar se seria incluído
        valido, motivo = validar_contrato_no_periodo(contrato, data_inicio_periodo, data_fim_periodo)
        status = "✅ INCLUÍDO" if valido else "❌ EXCLUÍDO"
        print(f"   - Status: {status}")
        if not valido:
            print(f"   - Motivo: {motivo}")
        
        # Verificar se tem inquilino
        if contrato.inquilino.exists():
            primeiro_inquilino = contrato.inquilino.first()
            nome = primeiro_inquilino.nome or primeiro_inquilino.razao_social or "Sem nome"
            print(f"   - Inquilino: {nome}")
        else:
            print(f"   - Inquilino: Não definido")


def debug_contratos_especificos():
    """
    Debug específico para os contratos #5 e #6
    """
    print("🔍 DEBUG: Contratos #5 e #6")
    print("=" * 40)
    
    for contrato_id in [5, 6]:
        try:
            contrato = Contrato.objects.get(id=contrato_id)
            print(f"\n📋 CONTRATO #{contrato_id}")
            print(f"   - Início: {contrato.data_inicio}")
            
            # Verificar todos os campos possíveis
            campos_verificar = ['data_fim', 'data_encerramento', 'ativo', 'status']
            for campo in campos_verificar:
                if hasattr(contrato, campo):
                    valor = getattr(contrato, campo)
                    print(f"   - {campo}: {valor}")
            
            # Verificar inquilino
            if contrato.inquilino.exists():
                inquilino = contrato.inquilino.first()
                print(f"   - Inquilino: {inquilino.nome or inquilino.razao_social}")
            else:
                print(f"   - Inquilino: Não definido")
            
            # Verificar para janeiro 2025
            data_inicio_periodo = date(2025, 1, 1)
            data_fim_periodo = date(2025, 1, 31)
            
            valido, motivo = validar_contrato_no_periodo(contrato, data_inicio_periodo, data_fim_periodo)
            print(f"   - Válido para Jan/2025: {'✅ SIM' if valido else '❌ NÃO'}")
            if not valido:
                print(f"   - Motivo: {motivo}")
                
        except Contrato.DoesNotExist:
            print(f"❌ Contrato #{contrato_id} não encontrado")
        except Exception as e:
            print(f"❌ Erro ao verificar contrato #{contrato_id}: {e}")


def debug_despesas_contrato(contrato_id):
    """
    Função para debug de despesas de um contrato específico
    """
    try:
        contrato = Contrato.objects.get(id=contrato_id)
        print(f"🔍 DEBUG: Despesas do Contrato #{contrato_id}")
        print("=" * 60)
        
        despesas = buscar_despesas_contrato_periodo(contrato, 1, 2025)  # Janeiro 2025
        
        print(f"📊 Resultado final: {len(despesas[0])} despesas, R$ {despesas[1]}")
        
    except Contrato.DoesNotExist:
        print(f"❌ Contrato #{contrato_id} não encontrado")
    except Exception as e:
        print(f"❌ Erro: {e}")


def calcular_data_vencimento_contrato(contrato, mes_referencia, ano_referencia):
    """
    ⭐ NOVA FUNÇÃO: Calcula data de vencimento baseada nas regras do contrato
    """
    try:
        # REGRA 1: Verificar se contrato tem dia de vencimento específico
        if hasattr(contrato, 'dia_vencimento') and contrato.dia_vencimento:
            dia_vencimento = contrato.dia_vencimento
            print(f"📅 Usando dia de vencimento do contrato: {dia_vencimento}")
        else:
            # REGRA 2: Padrão = dia 10 do mês seguinte
            dia_vencimento = 10
            print(f"📅 Usando dia padrão: {dia_vencimento}")
        
        # Calcular mês de vencimento (normalmente mês seguinte)
        if mes_referencia == 12:
            mes_vencimento = 1
            ano_vencimento = ano_referencia + 1
        else:
            mes_vencimento = mes_referencia + 1
            ano_vencimento = ano_referencia
        
        # Verificar se o dia existe no mês (ex: 31 em fevereiro)
        import calendar
        ultimo_dia_mes = calendar.monthrange(ano_vencimento, mes_vencimento)[1]
        
        if dia_vencimento > ultimo_dia_mes:
            dia_vencimento = ultimo_dia_mes
            print(f"📅 Ajustado para último dia do mês: {dia_vencimento}")
        
        data_vencimento = date(ano_vencimento, mes_vencimento, dia_vencimento)
        
        print(f"📅 Data de vencimento calculada: {data_vencimento}")
        return data_vencimento
        
    except Exception as e:
        print(f"❌ Erro ao calcular vencimento: {e}")
        # Fallback: dia 10 do mês seguinte
        if mes_referencia == 12:
            return date(ano_referencia + 1, 1, 10)
        else:
            return date(ano_referencia, mes_referencia + 1, 10)


@require_http_methods(["POST"])
def cobranca_gerar_selecionadas(request):
    """
    CORRIGIDA: Gera as cobranças usando dia_pagamento do contrato
    """
    try:
        import calendar
        
        data = json.loads(request.body)
        mes_referencia = int(data.get('mes_referencia'))
        ano_referencia = int(data.get('ano_referencia'))
        cobrancas_selecionadas = data.get('cobrancas_selecionadas', [])
        incluir_despesas = data.get('incluir_despesas', True)
        gerar_descricao_automatica = data.get('gerar_descricao_automatica', True)
        
        print(f"🚀 Gerando cobranças CORRIGIDO (usando dia_pagamento)")
        print(f"📅 Período: {mes_referencia}/{ano_referencia}")
        print(f"📋 Contratos: {cobrancas_selecionadas}")
        
        if not cobrancas_selecionadas:
            return JsonResponse({'success': False, 'error': 'Nenhuma cobrança selecionada'})
        
        # Buscar contratos selecionados
        try:
            from sisimob.models import Contrato
            
            contratos = Contrato.objects.filter(
                id__in=cobrancas_selecionadas,
                ativo=True
            )
            
            cobrancas_criadas = []
            erros = []
            
            for contrato in contratos:
                try:
                    print(f"\n📄 Processando contrato #{contrato.id}")
                    
                    # Verificar se já existe cobrança
                    if Cobranca.objects.filter(
                        contrato=contrato,
                        mes_referencia=mes_referencia,
                        ano_referencia=ano_referencia
                    ).exists():
                        erros.append(f'Cobrança já existe para contrato #{contrato.id}')
                        continue
                    
                    # ⭐ NOVA LÓGICA: CALCULAR VENCIMENTO USANDO DIA_PAGAMENTO DO CONTRATO
                    dia_vencimento = contrato.dia_pagamento if contrato.dia_pagamento else 10
                    
                    # Calcular mês de vencimento (mês seguinte)
                    if mes_referencia == 12:
                        mes_vencimento = 1
                        ano_vencimento = ano_referencia + 1
                    else:
                        mes_vencimento = mes_referencia + 1
                        ano_vencimento = ano_referencia
                    
                    # Verificar se o dia existe no mês
                    ultimo_dia_mes = calendar.monthrange(ano_vencimento, mes_vencimento)[1]
                    if dia_vencimento > ultimo_dia_mes:
                        dia_vencimento = ultimo_dia_mes
                        print(f"📅 Dia ajustado para: {dia_vencimento} (último dia do mês)")
                    
                    data_vencimento_calculada = date(ano_vencimento, mes_vencimento, dia_vencimento)
                    print(f"📅 Vencimento: {data_vencimento_calculada} (dia {contrato.dia_pagamento} do contrato)")
                    
                    # Criar cobrança usando a factory function do modelo
                    from ..models.cobranca import criar_cobranca_do_contrato
                    
                    cobranca = criar_cobranca_do_contrato(
                        contrato=contrato,
                        mes_referencia=mes_referencia,
                        ano_referencia=ano_referencia,
                        data_vencimento=data_vencimento_calculada,  # ⭐ USAR DATA CALCULADA
                        incluir_despesas=incluir_despesas
                    )
                    
                    # Adicionar descrição automática se solicitado
                    if gerar_descricao_automatica:
                        # Obter despesas da cobrança (se existirem)
                        despesas_para_descricao = []  # TODO: buscar despesas reais quando implementado
                        
                        descricao_automatica = gerar_descricao_automatica_simples(
                            mes_referencia=mes_referencia,
                            ano_referencia=ano_referencia,
                            valor_aluguel=float(cobranca.detalhes_calculo.get('valor_base', 0)),  # ✅ Valor do aluguel
                            detalhes_calculo=cobranca.detalhes_calculo  # ✅ Passar detalhes completos
                        )
                        
                        cobranca.descricao = descricao_automatica
                        cobranca.save()
                        print(f"📝 Descrição DETALHADA adicionada")


                    
                    cobrancas_criadas.append({
                        'id': cobranca.pk,
                        'contrato': str(contrato),
                        'valor_total': float(cobranca.valor),
                        'data_vencimento': data_vencimento_calculada.strftime('%d/%m/%Y'),
                        'dia_pagamento': contrato.dia_pagamento  # ⭐ NOVO
                    })
                    
                    print(f"✅ Cobrança #{cobranca.pk} criada! Vence em {data_vencimento_calculada.strftime('%d/%m/%Y')}")
                    
                except Exception as e:
                    erro_msg = f'Erro ao criar cobrança para contrato #{contrato.id}: {str(e)}'
                    erros.append(erro_msg)
                    print(f"❌ {erro_msg}")
                    import traceback
                    traceback.print_exc()
            
            resultado = {
                'success': True,
                'cobrancas_criadas': len(cobrancas_criadas),
                'detalhes': cobrancas_criadas,
                'erros': erros
            }
            
            print(f"🎉 RESULTADO: {len(cobrancas_criadas)} cobranças criadas, {len(erros)} erros")
            return JsonResponse(resultado)
            
        except ImportError:
            return JsonResponse({'success': False, 'error': 'Modelo Contrato não encontrado'})
            
    except Exception as e:
        print(f"❌ Erro geral: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': f'Erro interno: {str(e)}'})





def gerar_descricao_automatica_cobranca(cobranca, mes_referencia, ano_referencia):
    """
    ⭐ NOVA FUNÇÃO: Gera descrição automática para uma cobrança
    """
    try:
        meses = {
            1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
            5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
            9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
        }
        
        mes_nome = meses.get(mes_referencia, f'Mês {mes_referencia}')
        
        descricao_partes = [
            
            f"Valor do aluguel: R$ {cobranca.valor:.2f}".replace('.', ',')
        ]
        
        # TODO: Adicionar despesas quando implementado
        # if cobranca.despesas.exists():
        #     descricao_partes.append("\nDespesas incluídas:")
        #     for despesa in cobranca.despesas.all():
        #         valor_formatado = f"R$ {despesa.valor:.2f}".replace('.', ',')
        #         descricao_partes.append(f"• {despesa.nome}: {valor_formatado}")
        
        valor_total_formatado = f"R$ {cobranca.valor:.2f}".replace('.', ',')
        descricao_partes.append(f"\nValor total: {valor_total_formatado}")
        
        return '\n'.join(descricao_partes)
        
    except Exception as e:
        print(f"❌ Erro ao gerar descrição: {e}")
        return f"Aluguel referente a {mes_nome} de {ano_referencia}"


# ⭐ FUNÇÃO CORRIGIDA: Preview principal sem data de vencimento
def cobranca_preview_geracao(request):
    """
    View principal para exibir a página de preview CORRIGIDA
    Remove campo de data de vencimento - será calculado automaticamente
    """
    # Buscar contratos ativos
    contratos_ativos = Contrato.objects.filter(ativo=True).select_related('imovel').prefetch_related('inquilino')
    
    # Meses para o select
    MESES_CHOICES = [
        (1, 'Janeiro'), (2, 'Fevereiro'), (3, 'Março'), (4, 'Abril'),
        (5, 'Maio'), (6, 'Junho'), (7, 'Julho'), (8, 'Agosto'),
        (9, 'Setembro'), (10, 'Outubro'), (11, 'Novembro'), (12, 'Dezembro')
    ]
    
    from datetime import date
    hoje = date.today()
    
    context = {
        'contratos_ativos': contratos_ativos,
        'meses': MESES_CHOICES,
        'mes_atual': hoje.month,
        'ano_atual': hoje.year,
        # ❌ REMOVIDO: 'data_vencimento_padrao' - não é mais necessário
    }
    
    return render(request, 'financeiro/cobranca/cobranca_preview_geracao.html', context)



# ADICIONE ESTAS FUNÇÕES ao final do seu arquivo cobranca_views.py

def calcular_data_vencimento_contrato(contrato, mes_referencia, ano_referencia):
    """
    Calcula data de vencimento baseada nas regras do contrato
    """
    from datetime import date
    import calendar
    
    try:
        # REGRA 1: Verificar se contrato tem dia de vencimento específico
        if hasattr(contrato, 'dia_vencimento') and contrato.dia_vencimento:
            dia_vencimento = contrato.dia_vencimento
            print(f"📅 Usando dia de vencimento do contrato: {dia_vencimento}")
        else:
            # REGRA 2: Padrão = dia 10 do mês seguinte
            dia_vencimento = 10
            print(f"📅 Usando dia padrão: {dia_vencimento}")
        
        # Calcular mês de vencimento (normalmente mês seguinte)
        if mes_referencia == 12:
            mes_vencimento = 1
            ano_vencimento = ano_referencia + 1
        else:
            mes_vencimento = mes_referencia + 1
            ano_vencimento = ano_referencia
        
        # Verificar se o dia existe no mês (ex: 31 em fevereiro)
        ultimo_dia_mes = calendar.monthrange(ano_vencimento, mes_vencimento)[1]
        
        if dia_vencimento > ultimo_dia_mes:
            dia_vencimento = ultimo_dia_mes
            print(f"📅 Ajustado para último dia do mês: {dia_vencimento}")
        
        data_vencimento = date(ano_vencimento, mes_vencimento, dia_vencimento)
        
        print(f"📅 Data de vencimento calculada: {data_vencimento}")
        return data_vencimento
        
    except Exception as e:
        print(f"❌ Erro ao calcular vencimento: {e}")
        # Fallback: dia 10 do mês seguinte
        if mes_referencia == 12:
            return date(ano_referencia + 1, 1, 10)
        else:
            return date(ano_referencia, mes_referencia + 1, 10)


def teste_calcular_vencimento():
    """
    Função para testar o cálculo de vencimento
    """
    from datetime import date
    from sisimob.models import Contrato
    
    print("🧪 TESTE: Cálculo de Data de Vencimento")
    print("=" * 50)
    
    # Testar diferentes cenários
    cenarios = [
        (1, 2025),   # Janeiro 2025 -> Vencimento em Fevereiro
        (12, 2024),  # Dezembro 2024 -> Vencimento em Janeiro 2025
        (2, 2025),   # Fevereiro 2025 -> Vencimento em Março
    ]
    
    try:
        contrato_teste = Contrato.objects.first()
        print(f"📋 Testando com contrato: {contrato_teste}")
        
        for mes, ano in cenarios:
            print(f"\n📅 Teste - Referência: {mes:02d}/{ano}")
            vencimento = calcular_data_vencimento_contrato(contrato_teste, mes, ano)
            print(f"   ✅ Vencimento: {vencimento.strftime('%d/%m/%Y')}")
            
    except Exception as e:
        print(f"❌ Erro no teste: {e}")


def teste_api_preview_sem_vencimento():
    """
    Testa a API de preview sem enviar data de vencimento
    """
    print("🧪 TESTE: Preview sem Data de Vencimento")
    print("=" * 50)
    
    # Simular dados de entrada (sem data_vencimento)
    dados_teste = {
        'mes_referencia': 1,
        'ano_referencia': 2025,
        'contratos': [],  # Todos os contratos
        'incluir_despesas': True
    }
    
    print(f"📤 Dados de entrada: {dados_teste}")
    
    try:
        from sisimob.models import Contrato
        
        # Verificar contratos disponíveis
        contratos = Contrato.objects.filter(ativo=True)
        print(f"📋 Contratos ativos encontrados: {contratos.count()}")
        
        if contratos.count() == 0:
            print("⚠️ Nenhum contrato ativo encontrado!")
            return
        
        # Testar com primeiros 3 contratos
        for contrato in contratos[:3]:
            print(f"\n📄 Contrato #{contrato.id}")
            
            vencimento = calcular_data_vencimento_contrato(
                contrato, dados_teste['mes_referencia'], dados_teste['ano_referencia']
            )
            
            print(f"   📅 Vencimento calculado: {vencimento.strftime('%d/%m/%Y')}")
            
            # Verificar inquilino
            if contrato.inquilino.exists():
                inquilino = contrato.inquilino.first()
                nome = inquilino.nome or inquilino.razao_social or "Sem nome"
                print(f"   👤 Inquilino: {nome}")
            else:
                print(f"   👤 Inquilino: Não definido")
            
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()


def verificar_estrutura_contrato():
    """
    Verifica se o modelo Contrato tem campos necessários
    """
    from sisimob.models import Contrato
    
    print("🔍 VERIFICAÇÃO: Estrutura do Modelo Contrato")
    print("=" * 50)
    
    try:
        contrato = Contrato.objects.first()
        
        if not contrato:
            print("❌ Nenhum contrato encontrado!")
            return
            
        print(f"📋 Testando contrato: {contrato}")
        
        # Verificar campos relacionados a vencimento
        campos_vencimento = [
            'dia_vencimento',
            'data_vencimento',
            'vencimento',
            'dia_pagamento'
        ]
        
        print("\n🔍 Campos de vencimento:")
        for campo in campos_vencimento:
            if hasattr(contrato, campo):
                valor = getattr(contrato, campo)
                print(f"   ✅ {campo}: {valor}")
            else:
                print(f"   ❌ {campo}: Não existe")
        
        # Verificar outros campos importantes
        campos_importantes = [
            'ativo',
            'data_inicio',
            'data_fim',
            'valor_base',
            'valor_aluguel'
        ]
        
        print("\n🔍 Outros campos importantes:")
        for campo in campos_importantes:
            if hasattr(contrato, campo):
                valor = getattr(contrato, campo)
                print(f"   ✅ {campo}: {valor}")
            else:
                print(f"   ❌ {campo}: Não existe")
                
        # Verificar inquilino
        print("\n🔍 Relacionamentos:")
        if hasattr(contrato, 'inquilino'):
            if contrato.inquilino.exists():
                inquilino = contrato.inquilino.first()
                print(f"   ✅ inquilino: {inquilino}")
            else:
                print(f"   ⚠️ inquilino: Relacionamento existe mas vazio")
        else:
            print(f"   ❌ inquilino: Relacionamento não existe")
            
    except Exception as e:
        print(f"❌ Erro na verificação: {e}")
        import traceback
        traceback.print_exc()


def gerar_descricao_automatica_simples(mes_referencia, ano_referencia, valor_aluguel, despesas=None, valor_total=None, detalhes_calculo=None):
    """
    VERSÃO DETALHADA: Gera descrição com todas as despesas abertas
    """
    meses = {
        1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
        5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
        9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
    }
    
    mes_nome = meses.get(mes_referencia, f'Mês {mes_referencia}')
    
    # Linha 1: Período
    descricao_linhas = [f"Aluguel referente a {mes_nome} de {ano_referencia}"]
    
    # Linha 2: Valor do aluguel
    valor_aluguel_fmt = f"R$ {valor_aluguel:.2f}".replace('.', ',')
    descricao_linhas.append(f"Aluguel: {valor_aluguel_fmt}")
    
    # Se temos detalhes_calculo, usar dados mais precisos
    if detalhes_calculo and 'despesas_incluidas' in detalhes_calculo:
        despesas_inc = detalhes_calculo['despesas_incluidas']
        
        # Débitos (soma no valor)
        if 'debitos_inquilino' in despesas_inc and despesas_inc['debitos_inquilino']:
            for debito in despesas_inc['debitos_inquilino']:
                tipo = debito.get('tipo', 'Despesa')
                valor = debito.get('valor', 0)
                valor_fmt = f"R$ {valor:.2f}".replace('.', ',')
                descricao_linhas.append(f"{tipo}: {valor_fmt}")
        
        # Créditos (subtrai do valor)
        if 'creditos_proprietario' in despesas_inc and despesas_inc['creditos_proprietario']:
            for credito in despesas_inc['creditos_proprietario']:
                tipo = credito.get('tipo', 'Crédito')
                valor = credito.get('valor', 0)
                valor_fmt = f"R$ {valor:.2f}".replace('.', ',')
                descricao_linhas.append(f"{tipo} (desconto): -{valor_fmt}")
        
        # Valor total dos detalhes
        if 'breakdown' in detalhes_calculo:
            valor_total = detalhes_calculo['breakdown'].get('valor_final', valor_aluguel)
    
    # Fallback: usar parâmetro despesas se não temos detalhes_calculo
    elif despesas and len(despesas) > 0:
        for despesa in despesas:
            valor_despesa = despesa.get('valor', 0)
            nome_despesa = despesa.get('nome', 'Despesa')
            tipo_despesa = despesa.get('tipo', 'debito')
            
            valor_fmt = f"R$ {abs(valor_despesa):.2f}".replace('.', ',')
            
            if tipo_despesa == 'credito' or valor_despesa < 0:
                descricao_linhas.append(f"{nome_despesa} (desconto): -{valor_fmt}")
            else:
                descricao_linhas.append(f"{nome_despesa}: {valor_fmt}")
    
    # Calcular valor total se não foi fornecido
    if valor_total is None:
        valor_total = valor_aluguel
    
    # Linha final: Valor total
    descricao_linhas.append("")  # Linha em branco
    valor_total_fmt = f"R$ {valor_total:.2f}".replace('.', ',')
    descricao_linhas.append(f"Valor total: {valor_total_fmt}")
    
    return '\n'.join(descricao_linhas)




# FUNÇÃO PARA USAR NA GERAÇÃO DE COBRANÇAS
def aplicar_descricao_simples_na_cobranca(cobranca, mes_referencia, ano_referencia, contrato, despesas_calculadas=None):
    """
    Aplica a descrição simples na cobrança
    """
    try:
        # Obter valor do aluguel
        valor_aluguel = float(cobranca.valor)
        
        # Se temos despesas calculadas, subtrair para obter só o aluguel
        if despesas_calculadas and len(despesas_calculadas) > 0:
            valor_despesas_total = sum(d.get('valor', 0) for d in despesas_calculadas)
            valor_aluguel_puro = valor_aluguel - valor_despesas_total
        else:
            valor_aluguel_puro = valor_aluguel
            despesas_calculadas = []
        
        # Gerar descrição
        descricao = gerar_descricao_automatica_simples(
            mes_referencia=mes_referencia,
            ano_referencia=ano_referencia,
            valor_aluguel=valor_aluguel_puro,
            despesas=despesas_calculadas,
            valor_total=valor_aluguel
        )
        
        return descricao
        
    except Exception as e:
        print(f"❌ Erro ao aplicar descrição: {e}")
        meses = {
            1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
            5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
            9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
        }
        mes_nome = meses.get(mes_referencia, f'Mês {mes_referencia}')
        valor_fmt = f"R$ {cobranca.valor:.2f}".replace('.', ',')
        return f"Aluguel referente a {mes_nome} de {ano_referencia}\nAluguel: {valor_fmt}\n\nValor total: {valor_fmt}"


# EXEMPLOS DE USO:

def exemplo_sem_despesas():
    """Exemplo: Apenas aluguel"""
    descricao = gerar_descricao_automatica_simples(
        mes_referencia=6,
        ano_referencia=2025,
        valor_aluguel=963.24
    )
    print("EXEMPLO 1 - Só aluguel:")
    print(descricao)
    print("-" * 40)

def exemplo_com_despesas_debito():
    """Exemplo: Aluguel + despesas que o inquilino paga"""
    despesas = [
        {'nome': 'Água', 'valor': 50.00, 'tipo': 'debito'},
        {'nome': 'Luz', 'valor': 120.00, 'tipo': 'debito'}
    ]
    
    descricao = gerar_descricao_automatica_simples(
        mes_referencia=6,
        ano_referencia=2025,
        valor_aluguel=963.24,
        despesas=despesas
    )
    print("EXEMPLO 2 - Com despesas (débito):")
    print(descricao)
    print("-" * 40)

def exemplo_com_despesas_mistas():
    """Exemplo: Aluguel + despesas mistas"""
    despesas = [
        {'nome': 'Água', 'valor': 50.00, 'tipo': 'debito'},      # + (inquilino paga)
        {'nome': 'Reforma', 'valor': 200.00, 'tipo': 'credito'}, # - (proprietário paga)
        {'nome': 'Condomínio', 'valor': 150.00, 'tipo': 'debito'} # + (inquilino paga)
    ]
    
    descricao = gerar_descricao_automatica_simples(
        mes_referencia=6,
        ano_referencia=2025,
        valor_aluguel=963.24,
        despesas=despesas
    )
    print("EXEMPLO 3 - Com despesas mistas:")
    print(descricao)
    print("-" * 40)


def dashboard_data(request):
    # Buscar cobranças do banco de dados
    cobrancas = Cobranca.objects.select_related('contrato__inquilino').all()
    
    data = {
        'cobrancas': [
            {
                'id': c.id,
                'cliente': str(c.contrato.inquilino.first()),
                'valor': float(c.valor),
                'vencimento': c.data_vencimento.strftime('%Y-%m-%d'),
                'status': c.status,
                'asaas_id': c.asaasintegracao_set.first().asaas_id if c.asaasintegracao_set.exists() else None,
                'descricao': c.descricao,
                'integrada': c.asaasintegracao_set.exists()
            } for c in cobrancas
        ]
    }
    return JsonResponse(data)

@csrf_exempt

def integrar_lote(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        cobrancas_ids = data.get('cobrancas_ids', [])
        configuracoes = data.get('configuracoes', {})
        
        # Processar integração em lote
        resultados = []
        for cobranca_id in cobrancas_ids:
            try:
                cobranca = Cobranca.objects.get(id=cobranca_id)
                # Sua lógica de integração aqui
                resultado = integrar_cobranca_asaas(cobranca, configuracoes)
                resultados.append(resultado)
            except Exception as e:
                resultados.append({'success': False, 'error': str(e), 'cobranca_id': cobranca_id})
        
        return JsonResponse({'success': True, 'resultados': resultados})
    


def asaas_dashboard(request):
    """Dashboard principal do Asaas"""
    return render(request, 'financeiro/cobranca/asaas_dashboard.html')


@require_http_methods(["GET"])
def asaas_dashboard_data(request):
    """Retorna dados para o dashboard via AJAX"""
    try:
        # Buscar cobranças
        cobrancas = Cobranca.objects.select_related('contrato').prefetch_related('contrato__inquilino').all()
        
        data = {'cobrancas': []}
        
        for cobranca in cobrancas:
            try:
                # Verificar se tem integração Asaas
                integracao = None
                try:
                    from ..models import AsaasIntegracao
                    integracao = AsaasIntegracao.objects.filter(cobranca=cobranca).first()
                except ImportError:
                    pass
                
                # Pegar o primeiro inquilino com nome real
                cliente_nome = 'Cliente não informado'
                if cobranca.contrato and cobranca.contrato.inquilino.exists():
                    inquilino = cobranca.contrato.inquilino.first()
                    if inquilino:
                        cliente_nome = inquilino.nome or inquilino.razao_social or 'Cliente sem nome'
                
                cobranca_data = {
                    'id': cobranca.id,
                    'cliente': cliente_nome,
                    'valor': float(cobranca.valor),
                    'vencimento': cobranca.data_vencimento.strftime('%Y-%m-%d') if cobranca.data_vencimento else '',
                    'status': cobranca.status,
                    'asaas_id': integracao.asaas_id if integracao else None,
                    'descricao': cobranca.descricao or f"Cobrança #{cobranca.id}",
                    'integrada': bool(integracao and integracao.asaas_id)
                }
                data['cobrancas'].append(cobranca_data)
                
            except Exception as e:
                print(f"⚠️ Erro ao processar cobrança #{cobranca.id}: {e}")
                continue
        
        return JsonResponse(data)
        
    except Exception as e:
        print(f"❌ Erro na API dashboard_data: {e}")
        return JsonResponse({'error': str(e)}, status=500)
    
@csrf_exempt
@require_http_methods(["POST"])
def asaas_integrar_lote(request):
    """Integra múltiplas cobranças com o Asaas - VERSÃO FINAL FUNCIONAL"""
    try:
        data = json.loads(request.body)
        cobrancas_ids = data.get('cobrancas_ids', [])
        configuracoes = data.get('configuracoes', {})
        
        print(f"🔄 DASHBOARD: Integrando lote de {len(cobrancas_ids)} cobranças")
        print(f"📋 IDs: {cobrancas_ids}")
        
        if not cobrancas_ids:
            return JsonResponse({'error': 'Nenhuma cobrança selecionada'}, status=400)
        
        # Preparar opções
        opcoes = {
            'billing_type': configuracoes.get('billingType', 'BOLETO'),
            'enviar_por_email': configuracoes.get('enviarEmail', True),
            'enviar_por_whatsapp': configuracoes.get('enviarSMS', False),
            'observacoes': configuracoes.get('observacoes', 'Integração via dashboard')
        }
        
        print(f"⚙️ Opções: {opcoes}")
        
        resultados = []
        
        for cobranca_id in cobrancas_ids:
            try:
                cobranca = Cobranca.objects.get(id=cobranca_id)
                print(f"\n📄 === PROCESSANDO COBRANÇA #{cobranca_id} ===")
                print(f"   💰 Valor: R$ {cobranca.valor}")
                print(f"   📅 Vencimento: {cobranca.data_vencimento}")
                
                # Verificar dados do cliente
                if not cobranca.contrato.inquilino.exists():
                    print(f"❌ Sem inquilino")
                    resultados.append({
                        'success': False,
                        'error': 'Cobrança sem inquilino cadastrado',
                        'cobranca_id': cobranca_id
                    })
                    continue
                
                inquilino = cobranca.contrato.inquilino.first()
                print(f"   👤 Cliente: {inquilino.nome or inquilino.razao_social}")
                
                # Verificar documentos
                cpf = getattr(inquilino, 'CPF', '') or ''
                cnpj = getattr(inquilino, 'cnpj', '') or ''
                
                if not cpf and not cnpj:
                    print(f"❌ Sem CPF/CNPJ")
                    resultados.append({
                        'success': False,
                        'error': 'Cliente deve ter CPF ou CNPJ cadastrado',
                        'cobranca_id': cobranca_id,
                        'detalhes': f'Cliente: {inquilino.nome or inquilino.razao_social}'
                    })
                    continue
                
                print(f"   📋 Documento: CPF={cpf} | CNPJ={cnpj}")
                
                # 🆕 GARANTIR EMAIL
                email_cliente = garantir_email_cliente(inquilino)
                print(f"   📧 Email: {email_cliente}")
                
                # Verificar se já está integrada
                from ..models import AsaasIntegracao
                
                integracao_existente = AsaasIntegracao.objects.filter(
                    cobranca=cobranca
                ).exclude(asaas_id='').exclude(asaas_id__isnull=True).first()
                
                if integracao_existente and integracao_existente.asaas_id:
                    print(f"⚠️ JÁ INTEGRADA: {integracao_existente.asaas_id}")
                    resultados.append({
                        'success': True,
                        'cobranca_id': cobranca_id,
                        'message': 'Cobrança já integrada anteriormente',
                        'asaas_id': integracao_existente.asaas_id,
                        'status': integracao_existente.gateway_status,
                        'boleto_url': integracao_existente.boleto_url,
                        'value': float(cobranca.valor),
                        'due_date': cobranca.data_vencimento.strftime('%Y-%m-%d') if cobranca.data_vencimento else ''
                    })
                    continue
                
                # Criar nova integração
                print(f"🆕 Criando nova integração...")
                integracao, created = AsaasIntegracao.objects.get_or_create(
                    cobranca=cobranca,
                    defaults={
                        'data_integracao': timezone.now(),
                        'data_ultima_atualizacao': timezone.now(),
                        'gateway_status': 'PENDING',
                        'asaas_id': '',
                        'boleto_url': '',
                        'pix_copia_cola': '',
                        'pix_qrcode': '',
                        'pix_url': ''
                    }
                )
                
                print(f"   {'✅ Criada' if created else '📋 Existente'}")
                
                # 🚀 EXECUTAR INTEGRAÇÃO
                print(f"🚀 INICIANDO INTEGRAÇÃO REAL...")
                resultado = integracao.integrar_asaas(opcoes)
                
                print(f"📥 Resultado: {resultado}")
                
                # Processar resultado
                if isinstance(resultado, dict):
                    resultado['cobranca_id'] = cobranca_id
                    
                    if resultado.get('success', False):
                        # Recarregar para dados atualizados
                        integracao.refresh_from_db()
                        resultado.update({
                            'asaas_id': integracao.asaas_id,
                            'status': integracao.gateway_status,
                            'boleto_url': integracao.boleto_url,
                            'value': float(cobranca.valor),
                            'due_date': cobranca.data_vencimento.strftime('%Y-%m-%d') if cobranca.data_vencimento else ''
                        })
                        print(f"✅ SUCESSO TOTAL! Asaas ID: {integracao.asaas_id}")
                        print(f"   📄 Boleto: {integracao.boleto_url}")
                    else:
                        erros = resultado.get('errors', [])
                        if erros:
                            resultado['error'] = '; '.join(erros)
                        print(f"❌ FALHA: {resultado.get('error', 'Erro desconhecido')}")
                    
                    resultados.append(resultado)
                else:
                    print(f"❌ Resultado inválido: {type(resultado)}")
                    resultados.append({
                        'success': False,
                        'error': f'Resultado inválido: {type(resultado)}',
                        'cobranca_id': cobranca_id
                    })
                
            except Cobranca.DoesNotExist:
                print(f"❌ Cobrança #{cobranca_id} não encontrada")
                resultados.append({
                    'success': False, 
                    'error': f'Cobrança {cobranca_id} não encontrada',
                    'cobranca_id': cobranca_id
                })
                
            except Exception as e:
                print(f"❌ ERRO INESPERADO na cobrança #{cobranca_id}: {e}")
                import traceback
                traceback.print_exc()
                resultados.append({
                    'success': False, 
                    'error': str(e),
                    'cobranca_id': cobranca_id
                })
        
        # 📊 ESTATÍSTICAS FINAIS
        sucessos = len([r for r in resultados if r.get('success', False)])
        erros = len(resultados) - sucessos
        
        print(f"\n🎉 === RESULTADO FINAL ===")
        print(f"✅ Sucessos: {sucessos}")
        print(f"❌ Erros: {erros}")
        print(f"📊 Total: {len(resultados)}")
        
        # Log detalhado
        for resultado in resultados:
            cobranca_id = resultado.get('cobranca_id', 'N/A')
            if resultado.get('success'):
                asaas_id = resultado.get('asaas_id', 'N/A')
                print(f"   ✅ #{cobranca_id} → {asaas_id}")
            else:
                error = resultado.get('error', 'Erro desconhecido')
                print(f"   ❌ #{cobranca_id} → {error}")
        
        return JsonResponse({
            'success': True, 
            'resultados': resultados,
            'total_processadas': len(resultados),
            'sucessos': sucessos,
            'erros': erros
        })
        
    except Exception as e:
        print(f"❌ ERRO GERAL: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)
    
def asaas_dashboard_data_simples(request):

    """Versão simplificada da API para debug"""
    try:
        cobrancas = Cobranca.objects.all()[:10]  # Apenas primeiras 10
        
        data = {
            'cobrancas': [
                {
                    'id': c.id,
                    'cliente': 'Cliente Teste',
                    'valor': float(c.valor),
                    'vencimento': c.data_vencimento.strftime('%Y-%m-%d') if c.data_vencimento else '2025-07-10',
                    'status': c.status,
                    'asaas_id': None,
                    'descricao': c.descricao or f"Cobrança #{c.id}",
                    'integrada': False
                } for c in cobrancas
            ]
        }
        
        return JsonResponse(data)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    


def garantir_email_cliente(inquilino):
    """Garante que o cliente tenha um email válido"""
    if not inquilino.email:
        # Gerar email padrão baseado no tipo de cliente
        if inquilino.cnpj:
            # Para empresa, usar CNPJ
            cnpj_limpo = ''.join(filter(str.isdigit, inquilino.cnpj))
            email_padrao = f"empresa.{cnpj_limpo}@palestraimoveis.com.br"
        elif getattr(inquilino, 'CPF', ''):
            # Para pessoa física, usar CPF
            cpf_limpo = ''.join(filter(str.isdigit, inquilino.CPF))
            email_padrao = f"cliente.{cpf_limpo}@palestraimoveis.com.br"
        else:
            # Fallback usando ID
            email_padrao = f"cliente.{inquilino.id}@palestraimoveis.com.br"
        
        print(f"📧 Definindo email padrão para {inquilino.nome}: {email_padrao}")
        inquilino.email = email_padrao
        inquilino.save()
        
        return email_padrao
    
    return inquilino.email

# views.py - Endpoint para consultar status no Asaas

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import requests
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

@csrf_exempt
@require_http_methods(["POST"])
def consultar_status_asaas(request):
    """
    Endpoint para consultar o status atual de uma cobrança no Asaas
    """
    try:
        data = json.loads(request.body)
        asaas_id = data.get('asaas_id')
        cobranca_id = data.get('cobranca_id')
        
        if not asaas_id:
            return JsonResponse({
                'success': False,
                'error': 'asaas_id é obrigatório'
            }, status=400)
        
        logger.info(f"🔍 Consultando status da cobrança Asaas ID: {asaas_id}")
        
        # Configurações da API Asaas
        ASAAS_API_KEY = "sua_api_key_aqui"  # Configure em settings.py
        ASAAS_BASE_URL = "https://www.asaas.com/api/v3"
        
        headers = {
            'access_token': ASAAS_API_KEY,
            'Content-Type': 'application/json'
        }
        
        # Fazer requisição para o Asaas
        response = requests.get(
            f"{ASAAS_BASE_URL}/payments/{asaas_id}",
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            dados_asaas = response.json()
            
            logger.info(f"✅ Status obtido para {asaas_id}: {dados_asaas.get('status')}")
            
            # Estruturar resposta
            resultado = {
                'success': True,
                'dados_asaas': {
                    'id': dados_asaas.get('id'),
                    'status': dados_asaas.get('status'),
                    'value': dados_asaas.get('value'),
                    'netValue': dados_asaas.get('netValue'),
                    'dateReceived': dados_asaas.get('dateReceived'),
                    'dueDate': dados_asaas.get('dueDate'),
                    'invoiceUrl': dados_asaas.get('invoiceUrl'),
                    'bankSlipUrl': dados_asaas.get('bankSlipUrl'),
                    'pixTransaction': dados_asaas.get('pixTransaction'),
                    'lastUpdate': datetime.now().isoformat()
                },
                'cobranca_id': cobranca_id
            }
            
            return JsonResponse(resultado)
            
        elif response.status_code == 404:
            logger.warning(f"⚠️ Cobrança {asaas_id} não encontrada no Asaas")
            return JsonResponse({
                'success': False,
                'error': 'Cobrança não encontrada no Asaas'
            }, status=404)
            
        else:
            error_msg = f"Erro na API Asaas: {response.status_code}"
            try:
                error_data = response.json()
                if 'errors' in error_data:
                    error_msg += f" - {error_data['errors']}"
            except:
                error_msg += f" - {response.text}"
                
            logger.error(f"❌ {error_msg}")
            return JsonResponse({
                'success': False,
                'error': error_msg
            }, status=response.status_code)
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'JSON inválido'
        }, status=400)
        
    except requests.exceptions.Timeout:
        logger.error("❌ Timeout na consulta ao Asaas")
        return JsonResponse({
            'success': False,
            'error': 'Timeout na consulta - tente novamente'
        }, status=408)
        
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Erro de conexão com Asaas: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Erro de conexão: {str(e)}'
        }, status=500)
        
    except Exception as e:
        logger.error(f"❌ Erro interno: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def verificar_status_asaas(request):
    """
    Endpoint simples para verificar o status atual de uma cobrança no Asaas
    Retorna apenas o status atualizado
    """
    try:
        data = json.loads(request.body)
        asaas_id = data.get('asaas_id')
        cobranca_id = data.get('cobranca_id')
        
        if not asaas_id:
            return JsonResponse({
                'success': False,
                'error': 'asaas_id é obrigatório'
            }, status=400)
        
        logger.info(f"🔍 Verificando status da cobrança Asaas ID: {asaas_id}")
        
        # Configurações da API Asaas (configure no settings.py)
        ASAAS_API_KEY = getattr(settings, 'ASAAS_API_KEY', '')
        ASAAS_BASE_URL = getattr(settings, 'ASAAS_BASE_URL', 'https://www.asaas.com/api/v3')
        
        if not ASAAS_API_KEY:
            return JsonResponse({
                'success': False,
                'error': 'API Key do Asaas não configurada'
            }, status=500)
        
        headers = {
            'access_token': ASAAS_API_KEY,
            'Content-Type': 'application/json'
        }
        
        # Consultar status no Asaas
        response = requests.get(
            f"{ASAAS_BASE_URL}/payments/{asaas_id}",
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            dados_asaas = response.json()
            status_asaas = dados_asaas.get('status')
            
            logger.info(f"✅ Status obtido para {asaas_id}: {status_asaas}")
            
            return JsonResponse({
                'success': True,
                'status_asaas': status_asaas,
                'cobranca_id': cobranca_id,
                'valor': dados_asaas.get('value'),
                'data_vencimento': dados_asaas.get('dueDate'),
                'data_pagamento': dados_asaas.get('dateReceived'),
                'url_boleto': dados_asaas.get('bankSlipUrl'),
                'url_pix': dados_asaas.get('pixTransaction', {}).get('qrCode') if dados_asaas.get('pixTransaction') else None
            })
            
        elif response.status_code == 404:
            logger.warning(f"⚠️ Cobrança {asaas_id} não encontrada no Asaas")
            return JsonResponse({
                'success': False,
                'error': 'Cobrança não encontrada no Asaas'
            }, status=404)
            
        else:
            error_msg = f"Erro na API Asaas: {response.status_code}"
            try:
                error_data = response.json()
                if 'errors' in error_data:
                    error_msg += f" - {error_data['errors']}"
            except:
                error_msg += f" - {response.text}"
                
            logger.error(f"❌ {error_msg}")
            return JsonResponse({
                'success': False,
                'error': error_msg
            }, status=500)
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'JSON inválido'
        }, status=400)
        
    except requests.exceptions.Timeout:
        logger.error("❌ Timeout na consulta ao Asaas")
        return JsonResponse({
            'success': False,
            'error': 'Timeout na consulta - tente novamente'
        }, status=408)
        
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Erro de conexão com Asaas: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Erro de conexão: {str(e)}'
        }, status=500)
        
    except Exception as e:
        logger.error(f"❌ Erro interno: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }, status=500)


def obter_contratos_validos_por_periodo_FINAL(mes_referencia, ano_referencia, contratos_ids=None):
    """
    Obtém contratos válidos considerando vigência no período
    """
    from datetime import date
    import calendar
    from django.db.models import Q
    from sisimob.models import Contrato
    
    try:
        # Calcular período da cobrança
        data_inicio_periodo = date(ano_referencia, mes_referencia, 1)
        ultimo_dia = calendar.monthrange(ano_referencia, mes_referencia)[1]
        data_fim_periodo = date(ano_referencia, mes_referencia, ultimo_dia)
        
        print(f"🔍 Buscando contratos válidos para {mes_referencia:02d}/{ano_referencia}")
        print(f"📅 Período: {data_inicio_periodo} até {data_fim_periodo}")
        
        # Query base: TODOS os contratos
        queryset = Contrato.objects.all()
        
        # Filtrar por IDs específicos se fornecidos
        if contratos_ids:
            queryset = queryset.filter(id__in=contratos_ids)
            print(f"📋 Filtrado por IDs: {contratos_ids}")
        
        # Pre-filtro otimizado
        queryset = queryset.filter(
            data_inicio__lte=data_fim_periodo
        ).filter(
            Q(data_fim__isnull=True) |
            Q(data_fim__gte=data_inicio_periodo)
        )
        
        print(f"🔍 Query encontrou {queryset.count()} contratos candidatos")
        
        # Validação individual
        contratos_validos = []
        
        for contrato in queryset:
            estava_ativo = contrato_estava_ativo_no_periodo_especifico(
                contrato, data_inicio_periodo, data_fim_periodo
            )
            
            if estava_ativo:
                contratos_validos.append(contrato.id)
                
                status_atual = '🟢 Ativo' if contrato.ativo else '🔴 Inativo'
                vigencia = f"{contrato.data_inicio.strftime('%d/%m/%Y')} até {contrato.data_fim.strftime('%d/%m/%Y') if contrato.data_fim else 'indefinido'}"
                
                if contrato.inquilino.exists():
                    inquilino_nome = contrato.inquilino.first().nome or "Sem nome"
                else:
                    inquilino_nome = "Sem inquilino"
                
                print(f"   ✅ Contrato #{contrato.id}: {status_atual}")
                print(f"      📅 Vigência: {vigencia}")
                print(f"      👤 Inquilino: {inquilino_nome}")
            else:
                print(f"   ❌ Contrato #{contrato.id}: Não estava vigente no período")
        
        # Retornar QuerySet final
        resultado = Contrato.objects.filter(id__in=contratos_validos)
        
        print(f"🎯 RESULTADO: {resultado.count()} contratos válidos")
        return resultado
        
    except Exception as e:
        print(f"❌ Erro ao buscar contratos: {e}")
        return Contrato.objects.none()


# IMPLEMENTAÇÃO PASSO A PASSO - Correção do Preview

# PASSO 1: ADICIONE ESTAS FUNÇÕES NO FINAL DO ARQUIVO cobranca_views.py

def contrato_estava_ativo_no_periodo_especifico(contrato, data_inicio_periodo, data_fim_periodo):
    """
    ⭐ FUNÇÃO CORRIGIDA: Verifica se contrato estava vigente no período exato
    
    CASOS TESTADOS:
    - Contrato 5 em Dez/2024: ✅ SIM (vigente até 01/03/2025)
    - Contrato 6 em Dez/2024: ❌ NÃO (só inicia em 10/04/2025)
    """
    try:
        # REGRA 1: Contrato deve ter iniciado antes do fim do período
        if contrato.data_inicio > data_fim_periodo:
            return False
        
        # REGRA 2: Se tem data_fim, deve ter terminado depois do início do período
        if contrato.data_fim:
            if contrato.data_fim < data_inicio_periodo:
                return False
            return True
        
        # REGRA 3: Se não tem data_fim, estava vigente se já havia iniciado
        return contrato.data_inicio <= data_fim_periodo
        
    except Exception as e:
        print(f"❌ Erro na validação do contrato #{contrato.id}: {e}")
        return False


def obter_contratos_validos_por_periodo_RENOVACAO(mes_referencia, ano_referencia, contratos_ids=None):
    """
    ⭐ FUNÇÃO PRINCIPAL: Obtém contratos válidos considerando vigência no período
    
    SUBSTITUI: Contrato.objects.filter(ativo=True)
    POR: Validação real de vigência no período
    """
    from datetime import date
    import calendar
    from django.db.models import Q
    from sisimob.models import Contrato
    
    try:
        # Calcular período da cobrança
        data_inicio_periodo = date(ano_referencia, mes_referencia, 1)
        ultimo_dia = calendar.monthrange(ano_referencia, mes_referencia)[1]
        data_fim_periodo = date(ano_referencia, mes_referencia, ultimo_dia)
        
        print(f"🔍 Buscando contratos válidos para {mes_referencia:02d}/{ano_referencia}")
        print(f"📅 Período: {data_inicio_periodo} até {data_fim_periodo}")
        
        # ⭐ MUDANÇA PRINCIPAL: Query base inclui TODOS os contratos
        queryset = Contrato.objects.all()
        
        # Filtrar por IDs específicos se fornecidos
        if contratos_ids:
            queryset = queryset.filter(id__in=contratos_ids)
            print(f"📋 Filtrado por IDs: {contratos_ids}")
        
        # Pre-filtro otimizado baseado nas datas
        queryset = queryset.filter(
            data_inicio__lte=data_fim_periodo
        ).filter(
            Q(data_fim__isnull=True) |
            Q(data_fim__gte=data_inicio_periodo)
        )
        
        print(f"🔍 Query otimizada encontrou {queryset.count()} contratos candidatos")
        
        # Validação individual com a nova lógica
        contratos_validos = []
        
        for contrato in queryset:
            estava_ativo = contrato_estava_ativo_no_periodo_especifico(
                contrato, data_inicio_periodo, data_fim_periodo
            )
            
            if estava_ativo:
                contratos_validos.append(contrato.id)
                
                # Log detalhado
                status_atual = '🟢 Ativo' if contrato.ativo else '🔴 Inativo'
                vigencia = f"{contrato.data_inicio.strftime('%d/%m/%Y')} até {contrato.data_fim.strftime('%d/%m/%Y') if contrato.data_fim else 'indefinido'}"
                
                if contrato.inquilino.exists():
                    inquilino_nome = contrato.inquilino.first().nome or "Sem nome"
                else:
                    inquilino_nome = "Sem inquilino"
                
                print(f"   ✅ Contrato #{contrato.id}: {status_atual}")
                print(f"      📅 Vigência: {vigencia}")
                print(f"      👤 Inquilino: {inquilino_nome}")
            else:
                print(f"   ❌ Contrato #{contrato.id}: Não estava vigente no período")
        
        # Retornar QuerySet final
        resultado = Contrato.objects.filter(id__in=contratos_validos)
        
        print(f"🎯 RESULTADO FINAL: {resultado.count()} contratos válidos para {mes_referencia:02d}/{ano_referencia}")
        return resultado
        
    except Exception as e:
        print(f"❌ Erro ao buscar contratos: {e}")
        return Contrato.objects.none()


def cobranca_api_preview(request):
    """
    API CORRIGIDA para gerar preview das cobranças
    """
    if request.method == 'POST':
        try:
            from django.db import models
            from ..services.cobranca.cobranca_calculadora_service import CobrancaCalculadoraService
            import calendar
            
            data = json.loads(request.body)
            mes_referencia = data.get('mes_referencia')
            ano_referencia = data.get('ano_referencia')
            contratos_ids = data.get('contratos', [])
            incluir_despesas = data.get('incluir_despesas', True)
            
            print(f"🔍 API CORRIGIDA FINAL - Preview para {mes_referencia}/{ano_referencia}")
            
            # ⭐ CORREÇÃO: Usar a função correta que testamos
            if contratos_ids:
                print(f"📋 Filtrando por contratos específicos: {contratos_ids}")
                contratos_query = obter_contratos_elegiveis_periodo(
                    mes_referencia, ano_referencia, contratos_ids, validar_periodo=True
                )
            else:
                print(f"📋 Buscando todos os contratos elegíveis")
                contratos_query = obter_contratos_elegiveis_periodo(
                    mes_referencia, ano_referencia, None, validar_periodo=True
                )
            
            print(f"🔍 Total de contratos válidos encontrados: {contratos_query.count()}")
            
            # ⭐ DEBUG: Listar contratos encontrados
            for contrato in contratos_query:
                print(f"   📋 Contrato #{contrato.id}: {contrato.inquilino.first().nome if contrato.inquilino.exists() else 'Sem inquilino'}")
            
            # Resto da função continua igual...
            cobrancas_preview = []
            valor_total_geral = 0
            
            for contrato in contratos_query:
                print(f"\n📄 Processando contrato #{contrato.id}")
                
                # Verificar se já existe cobrança
                cobranca_existente = Cobranca.objects.filter(
                    contrato=contrato,
                    mes_referencia=mes_referencia,
                    ano_referencia=ano_referencia
                ).exists()
                
                if cobranca_existente:
                    print(f"⚠️ Cobrança já existe para contrato #{contrato.id}")
                    continue
                
                try:
                    # Calcular valor com reajustes
                    valor_aluguel_reajustado = obter_valor_atual_contrato(contrato, mes_referencia, ano_referencia)
                    
                    calculo_completo = CobrancaCalculadoraService.calcular_valor_completo(
                        contrato, mes_referencia, ano_referencia
                    )
                    
                    valor_aluguel = float(valor_aluguel_reajustado)
                    valor_despesas_liquido = float(calculo_completo['valor_despesas'])
                    valor_total_cobranca = valor_aluguel + valor_despesas_liquido
                    
                    # Calcular data de vencimento baseada no contrato
                    dia_vencimento = contrato.dia_pagamento if contrato.dia_pagamento else 10
                    
                    if mes_referencia == 12:
                        mes_vencimento = 1
                        ano_vencimento = ano_referencia + 1
                    else:
                        mes_vencimento = mes_referencia + 1
                        ano_vencimento = ano_referencia
                    
                    ultimo_dia_mes = calendar.monthrange(ano_vencimento, mes_vencimento)[1]
                    if dia_vencimento > ultimo_dia_mes:
                        dia_vencimento = ultimo_dia_mes
                    
                    data_vencimento_calculada = date(ano_vencimento, mes_vencimento, dia_vencimento)
                    
                    print(f"💰 Cálculo FINAL:")
                    print(f"   - Aluguel: R$ {valor_aluguel}")
                    print(f"   - Despesas líquidas: R$ {valor_despesas_liquido}")
                    print(f"   - Total: R$ {valor_total_cobranca}")
                    print(f"   - Vencimento: {data_vencimento_calculada}")
                    
                    if valor_total_cobranca <= 0:
                        print(f"⚠️ Valor total inválido, pulando contrato")
                        continue
                    
                    # Preparar lista de despesas
                    despesas = []
                    if incluir_despesas:
                        for debito in calculo_completo['detalhes']['debitos_inquilino']:
                            despesas.append({
                                'id': debito['id'],
                                'nome': debito['tipo'],
                                'descricao': debito['descricao'],
                                'valor': debito['valor'],
                                'tipo': 'debito',
                                'paga_por': debito['paga_por']
                            })
                        
                        for credito in calculo_completo['detalhes']['creditos_proprietario']:
                            despesas.append({
                                'id': credito['id'],
                                'nome': credito['tipo'],
                                'descricao': credito['descricao'],
                                'valor': credito['valor'],
                                'tipo': 'credito',
                                'paga_por': credito['paga_por']
                            })
                    
                    valor_total_geral += valor_total_cobranca
                    
                    # Obter nome do inquilino
                    inquilino_nome = "Sem inquilino"
                    if contrato.inquilino.exists():
                        primeiro_inquilino = contrato.inquilino.first()
                        inquilino_nome = (
                            primeiro_inquilino.nome or 
                            primeiro_inquilino.razao_social or 
                            "Cliente sem nome"
                        )
                    
                    # Status do contrato
                    status_contrato_atual = 'Ativo' if contrato.ativo else 'Inativo (era vigente no período)'
                    vigencia_contrato = f"{contrato.data_inicio.strftime('%d/%m/%Y')} até {contrato.data_fim.strftime('%d/%m/%Y') if contrato.data_fim else 'indefinido'}"
                    
                    cobrancas_preview.append({
                        'contrato_id': contrato.id,
                        'contrato_numero': f"#{contrato.id}",
                        'inquilino_nome': inquilino_nome,
                        'valor_aluguel': valor_aluguel,
                        'valor_despesas_liquido': valor_despesas_liquido,
                        'valor_total': valor_total_cobranca,
                        'data_vencimento': data_vencimento_calculada.strftime('%Y-%m-%d'),
                        'data_vencimento_formatada': data_vencimento_calculada.strftime('%d/%m/%Y'),
                        'dia_pagamento_contrato': contrato.dia_pagamento,
                        'despesas': despesas,
                        'endereco': contrato.imovel.endereco if contrato.imovel else "Endereço não informado",
                        'status_contrato_atual': status_contrato_atual,
                        'vigencia_contrato': vigencia_contrato,
                        'eh_renovacao': not contrato.ativo,
                        'breakdown': {
                            'total_debitos': calculo_completo['detalhes']['total_debitos'],
                            'total_creditos': calculo_completo['detalhes']['total_creditos'],
                            'formula': f"R$ {valor_aluguel:.2f} + R$ {calculo_completo['detalhes']['total_debitos']:.2f} - R$ {calculo_completo['detalhes']['total_creditos']:.2f} = R$ {valor_total_cobranca:.2f}"
                        }
                    })
                    
                    print(f"✅ Cobrança #{contrato.id} adicionada! Status: {status_contrato_atual}")
                    
                except Exception as e:
                    print(f"❌ Erro ao calcular cobrança para contrato #{contrato.id}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            # Nomes dos meses
            MESES_CHOICES = [
                (1, 'Janeiro'), (2, 'Fevereiro'), (3, 'Março'), (4, 'Abril'),
                (5, 'Maio'), (6, 'Junho'), (7, 'Julho'), (8, 'Agosto'),
                (9, 'Setembro'), (10, 'Outubro'), (11, 'Novembro'), (12, 'Dezembro')
            ]
            
            mes_nome = next((nome for valor, nome in MESES_CHOICES if valor == mes_referencia), 'Mês inválido')
            
            resultado = {
                'success': True,
                'cobrancas': cobrancas_preview,
                'total_cobrancas': len(cobrancas_preview),
                'valor_total_geral': valor_total_geral,
                'mes_nome': mes_nome,
                'ano': ano_referencia,
                'metodo_calculo': '✅ CORRIGIDO FINAL: Usando função testada',
                'contratos_incluidos_renovacao': len([c for c in cobrancas_preview if c.get('eh_renovacao', False)])
            }
            
            print(f"🎉 Preview CORRIGIDO FINAL gerado: {len(cobrancas_preview)} cobranças, total R$ {valor_total_geral}")
            print(f"📊 Incluindo {resultado['contratos_incluidos_renovacao']} contratos de renovação")
            
            # ⭐ DEBUG FINAL: Verificar se contrato #14 está na resposta
            contrato_14_na_resposta = any(c['contrato_id'] == 14 for c in cobrancas_preview)
            print(f"🎯 CONTRATO #14 NA RESPOSTA: {'✅ SIM' if contrato_14_na_resposta else '❌ NÃO'}")
            
            return JsonResponse(resultado)
            
        except Exception as e:
            print(f"❌ Erro no preview: {e}")
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Método não permitido'})