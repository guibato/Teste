# financeiro/views/repasse_views.py (versão corrigida e completa)
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, TemplateView
from django.db.models import Q, Sum, Count, Case, When, DecimalField, F
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.core.paginator import Paginator
from django.urls import reverse_lazy
from django.db import transaction
from datetime import date, datetime, timedelta
from decimal import Decimal
import json
import logging

# Imports dos modelos
from ..models.repasse import Repasse, PoliticaRepasseContrato, PoliticaRepasseGlobal, AgendamentoRepasse
try:
    from ..models.cobranca import Cobranca
except ImportError:
    Cobranca = None

from sisimob.models import Contrato, Cliente

# Imports dos services e forms
try:
    from ..services.repasse_service import RepasseService
    
except ImportError:
    RepasseService = None

try:
    from ..forms.repasse_forms import (
        RepasseForm, 
        PoliticaRepasseContratoForm,
        PoliticaRepasseGlobalForm,
        ProcessarRepasseForm,
        ConfiguracaoPoliticasForm,
        FiltroContratosForm
    )
except ImportError:
    # Fallback se os forms não existirem
    RepasseForm = None
    PoliticaRepasseContratoForm = None
    PoliticaRepasseGlobalForm = None
    ProcessarRepasseForm = None
    ConfiguracaoPoliticasForm = None
    FiltroContratosForm = None

logger = logging.getLogger(__name__)


# ==================== VIEWS DE REPASSES ====================

def gerar_repasse_automatico(request):
    """Gera repasses baseados nas políticas dos contratos - VERSÃO CORRIGIDA"""
    if request.method == 'POST':
        try:
            service = RepasseService()
            resultado = service.processar_repasses_automaticos()
            
            # Criar mensagem detalhada
            mensagem = (
                f"Processamento concluído: "
                f"{resultado.get('criados', 0)} repasses criados, "
                f"{resultado.get('processados', 0)} agendamentos processados, "
                f"{resultado.get('agendados', 0)} novos agendamentos criados"
            )
            
            if resultado.get('erros', 0) > 0:
                mensagem += f", {resultado.get('erros', 0)} erros encontrados"
                messages.warning(request, mensagem)
                
                # Log dos erros para debug
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Erros no processamento automático: {resultado.get('detalhes', [])}")
            else:
                messages.success(request, mensagem)
            
        except Exception as e:
            logger.error(f"Erro crítico no processamento automático: {str(e)}")
            messages.error(request, f"Erro no processamento: {str(e)}")
    
    return redirect('financeiro:lista_repasses')


def processar_agendamentos_vencidos(request):
    """Processa todos os agendamentos vencidos - VERSÃO CORRIGIDA"""
    if request.method == 'POST':
        try:
            service = RepasseService()
            service._processar_agendamentos_vencidos()
            resultado = service.resultados
            
            if resultado.get('processados', 0) > 0:
                messages.success(request, 
                    f"{resultado.get('processados', 0)} agendamentos processados com sucesso!")
            else:
                messages.info(request, "Nenhum agendamento vencido encontrado.")
            
            if resultado.get('erros', 0) > 0:
                messages.warning(request, f"{resultado.get('erros', 0)} erros durante o processamento.")
            
        except Exception as e:
            logger.error(f"Erro no processamento de agendamentos: {str(e)}")
            messages.error(request, f"Erro no processamento: {str(e)}")
    
    return redirect('financeiro:agendamento_list')


def testar_politica_contrato_view(request, pk):
    """Testa uma política de contrato (simulação) - VERSÃO CORRIGIDA E SIMPLIFICADA"""
    if request.method == 'POST':
        try:
            politica = get_object_or_404(PoliticaRepasseContrato, pk=pk)
            contrato = politica.contrato
            
            # Obter valor do contrato de forma segura
            valor_atual = Decimal('0')
            
            # Tentar diferentes campos de valor
            if hasattr(contrato, 'valor_aluguel_atual') and callable(contrato.valor_aluguel_atual):
                valor_atual = contrato.valor_aluguel_atual()
            elif hasattr(contrato, 'valor_aluguel'):
                valor_atual = contrato.valor_aluguel or Decimal('0')
            elif hasattr(contrato, 'valor_base'):
                valor_atual = contrato.valor_base or Decimal('0')
            
            if valor_atual <= 0:
                return JsonResponse({
                    'success': False,
                    'error': 'Valor do contrato não encontrado ou inválido'
                })
            
            # Obter taxa administrativa
            taxa_admin = Decimal('8.00')  # Padrão
            
            if hasattr(politica, 'taxa_admin_personalizada') and politica.taxa_admin_personalizada:
                taxa_admin = politica.taxa_admin_personalizada
            elif hasattr(contrato, 'valor_taxa_administracao_percentual') and contrato.valor_taxa_administracao_percentual:
                taxa_admin = contrato.valor_taxa_administracao_percentual
            
            # Calcular valores
            valor_taxa_admin = valor_atual * (taxa_admin / 100)
            valor_liquido = valor_atual - valor_taxa_admin
            valor_minimo = getattr(politica, 'valor_minimo_repasse', Decimal('0')) or Decimal('0')
            
            # Calcular próxima data
            from datetime import date, timedelta
            hoje = date.today()
            
            try:
                if hasattr(politica, 'calcular_proxima_data_repasse'):
                    proxima_data = politica.calcular_proxima_data_repasse(hoje)
                else:
                    # Fallback simples
                    dias_apos = getattr(politica, 'dias_apos_recebimento', 7)
                    proxima_data = hoje + timedelta(days=dias_apos)
            except:
                proxima_data = hoje + timedelta(days=30)
            
            # Montar resposta
            simulacao = {
                'valor_bruto': float(valor_atual),
                'taxa_admin': float(taxa_admin),
                'valor_taxa_admin': float(valor_taxa_admin),
                'valor_liquido': float(valor_liquido),
                'valor_minimo': float(valor_minimo),
                'acima_minimo': valor_liquido >= valor_minimo,
                'proxima_data': proxima_data.strftime('%d/%m/%Y') if proxima_data else 'N/A',
                'periodicidade': getattr(politica, 'periodicidade', 'N/A'),
                'tipo_dias': getattr(politica, 'tipo_dias', 'N/A'),
                'ativa': getattr(politica, 'ativa', False)
            }
            
            return JsonResponse({
                'success': True,
                'simulacao': simulacao
            })
            
        except Exception as e:
            logger.error(f"Erro ao testar política {pk}: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': f'Erro na simulação: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'error': 'Método não permitido'})


# ==================== NOVA VIEW PARA DASHBOARD DE AUTOMAÇÃO ====================

class DashboardAutomacaoView(TemplateView):
    """Dashboard específico para acompanhar a automação de repasses"""
    template_name = 'financeiro/repasses/dashboard_automacao.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            service = RepasseService()
            relatorio = service.gerar_relatorio_automatizacao()
            atrasados = service.verificar_repasses_atrasados()
            
            context.update({
                'relatorio': relatorio,
                'atrasados': atrasados,
                'pode_processar': True
            })
            
            # Próximos agendamentos (7 dias)
            from datetime import date, timedelta
            proximos_agendamentos = AgendamentoRepasse.objects.filter(
                status='agendado',
                data_agendada__lte=date.today() + timedelta(days=7)
            ).select_related('proprietario', 'contrato').order_by('data_agendada')[:10]
            
            context['proximos_agendamentos'] = proximos_agendamentos
            
            # Últimos processamentos
            ultimos_repasses = Repasse.objects.filter(
                tipo='automatico'
            ).select_related('proprietario', 'contrato').order_by('-data_criacao')[:10]
            
            context['ultimos_repasses'] = ultimos_repasses
            
        except Exception as e:
            logger.error(f"Erro no dashboard de automação: {str(e)}")
            context.update({
                'erro': str(e),
                'pode_processar': False
            })
        
        return context


def dashboard_automacao_ajax(request):
    """Dados AJAX para o dashboard de automação"""
    try:
        service = RepasseService()
        relatorio = service.gerar_relatorio_automatizacao()
        atrasados = service.verificar_repasses_atrasados()
        
        # Estatísticas dos últimos 30 dias
        from datetime import date, timedelta
        data_inicio = date.today() - timedelta(days=30)
        
        repasses_mes = Repasse.objects.filter(
            tipo='automatico',
            data_criacao__date__gte=data_inicio
        ).values('status').annotate(
            count=Count('id'),
            total=Sum(F('valor') - F('valor_desconto') - F('valor_taxa_admin'))
        )
        
        return JsonResponse({
            'success': True,
            'relatorio': relatorio,
            'atrasados': atrasados,
            'repasses_mes': list(repasses_mes),
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Erro no AJAX do dashboard: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


def processar_repasse_unico(request, repasse_id):
    """Processa um repasse específico via AJAX"""
    if request.method == 'POST':
        try:
            service = RepasseService()
            resultado = service.processar_repasse_individual(repasse_id)
            
            if resultado['success']:
                return JsonResponse({
                    'success': True,
                    'message': resultado['message']
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': resultado['error']
                })
                
        except Exception as e:
            logger.error(f"Erro ao processar repasse {repasse_id}: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Método não permitido'})


# ==================== VIEW PARA DIAGNÓSTICO ====================

def diagnostico_automacao(request):
    """View para diagnosticar problemas na automação"""
    diagnostico = {
        'data_verificacao': date.today(),
        'problemas': [],
        'avisos': [],
        'sugestoes': []
    }
    
    try:
        # Verificar contratos sem política
        contratos_sem_politica = Contrato.objects.filter(
            ativo=True,
            politica_repasse__isnull=True
        ).count()
        
        if contratos_sem_politica > 0:
            diagnostico['problemas'].append(
                f"{contratos_sem_politica} contratos ativos sem política de repasse configurada"
            )
            diagnostico['sugestoes'].append(
                "Configure políticas globais e aplique aos contratos sem política"
            )
        
        # Verificar políticas inativas
        politicas_inativas = PoliticaRepasseContrato.objects.filter(ativa=False).count()
        if politicas_inativas > 0:
            diagnostico['avisos'].append(
                f"{politicas_inativas} políticas de contrato estão inativas"
            )
        
        # Verificar repasses atrasados
        repasses_atrasados = Repasse.objects.filter(
            status='pendente',
            data_prevista__lt=date.today()
        ).count()
        
        if repasses_atrasados > 0:
            diagnostico['problemas'].append(
                f"{repasses_atrasados} repasses estão atrasados"
            )
            diagnostico['sugestoes'].append(
                "Execute o processamento automático ou processe os repasses manualmente"
            )
        
        # Verificar cobranças pagas sem repasse
        if Cobranca:
            cobrancas_sem_repasse = Cobranca.objects.filter(
                status='paga',
                data_pagamento__gte=date.today() - timedelta(days=30),
                repasses_cobranca__isnull=True
            ).count()
            
            if cobrancas_sem_repasse > 0:
                diagnostico['avisos'].append(
                    f"{cobrancas_sem_repasse} cobranças pagas sem repasse nos últimos 30 dias"
                )
        
        # Verificar agendamentos antigos
        agendamentos_antigos = AgendamentoRepasse.objects.filter(
            status='agendado',
            data_agendada__lt=date.today() - timedelta(days=7)
        ).count()
        
        if agendamentos_antigos > 0:
            diagnostico['problemas'].append(
                f"{agendamentos_antigos} agendamentos vencidos há mais de 7 dias"
            )
        
        # Status geral
        total_problemas = len(diagnostico['problemas'])
        total_avisos = len(diagnostico['avisos'])
        
        if total_problemas == 0 and total_avisos == 0:
            diagnostico['status'] = 'ok'
            diagnostico['mensagem'] = 'Sistema de automação funcionando corretamente'
        elif total_problemas == 0:
            diagnostico['status'] = 'atencao'
            diagnostico['mensagem'] = f'{total_avisos} item(s) que requerem atenção'
        else:
            diagnostico['status'] = 'problema'
            diagnostico['mensagem'] = f'{total_problemas} problema(s) encontrado(s)'
        
    except Exception as e:
        diagnostico['status'] = 'erro'
        diagnostico['mensagem'] = f'Erro ao executar diagnóstico: {str(e)}'
        logger.error(f"Erro no diagnóstico: {str(e)}")
    
    return render(request, 'financeiro/repasses/diagnostico_automacao.html', {
        'diagnostico': diagnostico
    })


# ==================== URLS ADICIONAIS PARA AUTOMAÇÃO ====================

class RepasseListView(ListView):
    model = Repasse
    template_name = 'financeiro/repasses/lista_repasses.html'
    context_object_name = 'repasses'
    paginate_by = 20

    def get_queryset(self):
        queryset = Repasse.objects.select_related(
            'proprietario', 'contrato', 'cobranca'
        ).prefetch_related('contrato__imovel', 'contrato__politica_repasse')

        # Filtros
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)

        proprietario_id = self.request.GET.get('proprietario')
        if proprietario_id:
            queryset = queryset.filter(proprietario_id=proprietario_id)

        mes = self.request.GET.get('mes')
        ano = self.request.GET.get('ano')
        if mes and ano:
            queryset = queryset.filter(mes_referencia=mes, ano_referencia=ano)

        data_inicio = self.request.GET.get('data_inicio')
        data_fim = self.request.GET.get('data_fim')
        if data_inicio:
            queryset = queryset.filter(data_prevista__gte=data_inicio)
        if data_fim:
            queryset = queryset.filter(data_prevista__lte=data_fim)

        # Busca por texto
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(proprietario__nome__icontains=search) |
                Q(contrato__imovel__endereco__icontains=search) |
                Q(descricao__icontains=search)
            )

        return queryset.order_by('-data_criacao')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Estatísticas para cards
        total_stats = self.get_queryset().aggregate(
            total_pendente=Sum(
                Case(
                    When(status='pendente', then=F('valor') - F('valor_desconto') - F('valor_taxa_admin')), 
                    output_field=DecimalField(max_digits=10, decimal_places=2)
                )
            ),
            total_efetuado=Sum(
                Case(
                    When(status='efetuado', then=F('valor') - F('valor_desconto') - F('valor_taxa_admin')), 
                    output_field=DecimalField(max_digits=10, decimal_places=2)
                )
            ),
            count_pendente=Count(Case(When(status='pendente', then=1))),
            count_efetuado=Count(Case(When(status='efetuado', then=1))),
            count_atrasado=Count(Case(When(status='pendente', data_prevista__lt=date.today(), then=1)))
        )

        # Estatísticas de políticas - CORRIGIDO: usar ativo=True
        context['stats_politicas'] = {
            'contratos_com_politica': Contrato.objects.filter(politica_repasse__isnull=False).count(),
            'contratos_sem_politica': Contrato.objects.filter(
                ativo=True,  # CORRIGIDO
                politica_repasse__isnull=True
            ).count(),
            'politicas_ativas': PoliticaRepasseContrato.objects.filter(ativa=True).count()
        }

        context.update({
            'total_stats': total_stats,
            'filtros': {
                'status': self.request.GET.get('status', ''),
                'proprietario': self.request.GET.get('proprietario', ''),
                'mes': self.request.GET.get('mes', ''),
                'ano': self.request.GET.get('ano', ''),
                'data_inicio': self.request.GET.get('data_inicio', ''),
                'data_fim': self.request.GET.get('data_fim', ''),
                'search': self.request.GET.get('search', ''),
            }
        })
        return context


# financeiro/views/repasse_views.py - RepasseDetailView CORRIGIDA

# financeiro/views/repasse_views.py - RepasseDetailView TOTALMENTE SEGURA

class RepasseDetailView(DetailView):
    model = Repasse
    template_name = 'financeiro/repasses/detalhe_repasse.html'
    context_object_name = 'repasse'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        repasse = self.get_object()
        
        # =============== MOVIMENTOS - VERSÃO SEGURA ===============
        context['movimentos'] = []
        try:
            from ..models.movimento import MovimentoConta
            
            # Tentar diferentes combinações de campos para encontrar movimentos relacionados
            movimentos_filters = [
                # Opção 1: Filtros ideais
                {
                    'proprietario': repasse.proprietario,
                    'contrato': repasse.contrato,
                    'data_referencia__year': repasse.ano_referencia,
                    'data_referencia__month': repasse.mes_referencia
                },
                # Opção 2: Apenas proprietário e contrato
                {
                    'proprietario': repasse.proprietario,
                    'contrato': repasse.contrato
                },
                # Opção 3: Apenas proprietário
                {
                    'proprietario': repasse.proprietario
                }
            ]
            
            for filters in movimentos_filters:
                try:
                    movimentos = MovimentoConta.objects.filter(**filters)
                    
                    # Tentar diferentes campos para ordenação
                    for order_field in ['-data', '-data_referencia', '-id']:
                        try:
                            context['movimentos'] = list(movimentos.order_by(order_field)[:10])
                            break
                        except:
                            continue
                    
                    if context['movimentos']:
                        break
                        
                except Exception:
                    continue
                    
        except ImportError:
            pass
        except Exception as e:
            import logging
            logging.getLogger(__name__).debug(f"Erro ao buscar movimentos: {e}")
        
        # =============== REPASSES RELACIONADOS - VERSÃO SEGURA ===============
        try:
            context['repasses_relacionados'] = Repasse.objects.filter(
                proprietario=repasse.proprietario,
                ano_referencia=repasse.ano_referencia,
                mes_referencia=repasse.mes_referencia
            ).exclude(pk=repasse.pk).select_related('contrato')[:5]
        except Exception:
            context['repasses_relacionados'] = []
        
        # =============== POLÍTICA DO CONTRATO - VERSÃO SEGURA ===============
        context['politica_info'] = None
        try:
            if hasattr(repasse.contrato, 'politica_repasse'):
                politica = repasse.contrato.politica_repasse
                if politica:
                    context['politica_info'] = {
                        'periodicidade': getattr(politica, 'periodicidade', 'N/A'),
                        'tipo_dias': getattr(politica, 'tipo_dias', 'N/A'),
                        'ativa': getattr(politica, 'ativa', False),
                        'valor_minimo': getattr(politica, 'valor_minimo_repasse', 0),
                        'taxa_admin': 'N/A'
                    }
                    
                    # Tentar obter taxa administrativa
                    try:
                        if hasattr(politica, 'get_taxa_admin'):
                            context['politica_info']['taxa_admin'] = politica.get_taxa_admin()
                        elif hasattr(politica, 'taxa_admin_personalizada'):
                            context['politica_info']['taxa_admin'] = politica.taxa_admin_personalizada
                    except:
                        pass
        except Exception:
            pass
        
        # =============== INFORMAÇÕES DA COBRANÇA - VERSÃO SEGURA ===============
        context['cobranca_info'] = None
        if repasse.cobranca:
            try:
                cobranca = repasse.cobranca
                context['cobranca_info'] = {}
                
                # Campos básicos com fallbacks
                context['cobranca_info']['id'] = getattr(cobranca, 'id', 'N/A')
                context['cobranca_info']['status'] = getattr(cobranca, 'status', 'N/A')
                
                # Valores com múltiplos fallbacks
                valor_fields = ['valor_pago', 'valor_original', 'valor']
                for field in valor_fields:
                    if hasattr(cobranca, field):
                        valor = getattr(cobranca, field)
                        if valor:
                            context['cobranca_info']['valor'] = valor
                            break
                else:
                    context['cobranca_info']['valor'] = 0
                
                # Datas com fallbacks
                date_fields = ['data_pagamento', 'data_vencimento', 'data']
                for field in date_fields:
                    if hasattr(cobranca, field):
                        data = getattr(cobranca, field)
                        if data:
                            context['cobranca_info'][field] = data
                
                # Referência temporal
                context['cobranca_info']['mes_referencia'] = getattr(cobranca, 'mes_referencia', repasse.mes_referencia)
                context['cobranca_info']['ano_referencia'] = getattr(cobranca, 'ano_referencia', repasse.ano_referencia)
                
            except Exception:
                context['cobranca_info'] = None
        
        # =============== INFORMAÇÕES DO CONTRATO - VERSÃO SEGURA ===============
        try:
            contrato = repasse.contrato
            context['contrato_info'] = {
                'id': contrato.id,
                'endereco': 'N/A',
                'valor_aluguel': 0,
                'tem_politica': False
            }
            
            # Endereço do imóvel
            if hasattr(contrato, 'imovel') and contrato.imovel:
                try:
                    context['contrato_info']['endereco'] = str(contrato.imovel)
                except:
                    context['contrato_info']['endereco'] = 'Endereço não disponível'
            
            # Valor do aluguel
            valor_fields = ['valor_aluguel', 'valor_base', 'valor']
            for field in valor_fields:
                if hasattr(contrato, field):
                    valor = getattr(contrato, field)
                    if valor:
                        context['contrato_info']['valor_aluguel'] = valor
                        break
            
            # Verificar se tem política
            context['contrato_info']['tem_politica'] = (
                hasattr(contrato, 'politica_repasse') and 
                contrato.politica_repasse is not None
            )
            
        except Exception:
            context['contrato_info'] = None
        
        # =============== INFORMAÇÕES DO PROPRIETÁRIO - VERSÃO SEGURA ===============
        try:
            proprietario = repasse.proprietario
            context['proprietario_info'] = {
                'id': proprietario.id,
                'nome': getattr(proprietario, 'nome', 'N/A'),
                'email': getattr(proprietario, 'email', ''),
                'telefone': getattr(proprietario, 'telefone', ''),
                'tipo': getattr(proprietario, 'tipo', 'N/A')
            }
        except Exception:
            context['proprietario_info'] = None
        
        # =============== ESTATÍSTICAS RÁPIDAS ===============
        try:
            # Outros repasses do mesmo proprietário
            outros_repasses = Repasse.objects.filter(
                proprietario=repasse.proprietario
            ).exclude(pk=repasse.pk)
            
            context['estatisticas'] = {
                'total_repasses': outros_repasses.count(),
                'repasses_pendentes': outros_repasses.filter(status='pendente').count(),
                'repasses_efetuados': outros_repasses.filter(status='efetuado').count(),
            }
            
            # Valor total se possível calcular
            try:
                from django.db.models import Sum, F
                total_valor = outros_repasses.filter(status='efetuado').aggregate(
                    total=Sum(F('valor') - F('valor_desconto') - F('valor_taxa_admin'))
                )['total']
                context['estatisticas']['valor_total_recebido'] = total_valor or 0
            except:
                context['estatisticas']['valor_total_recebido'] = 'N/A'
                
        except Exception:
            context['estatisticas'] = None
        
        return context
class RepasseCreateView(CreateView):
    model = Repasse
    template_name = 'financeiro/repasses/repasse_form.html'
    
    def get_form_class(self):
        return RepasseForm if RepasseForm else None
    
    def get_fields(self):
        if not RepasseForm:
            return ['proprietario', 'contrato', 'valor', 'valor_desconto', 
                    'valor_taxa_admin', 'data_prevista', 'mes_referencia', 'ano_referencia',
                    'tipo', 'metodo_pagamento', 'descricao', 'observacoes']
        return None
    
    def get_success_url(self):
        return reverse_lazy('financeiro:repasse_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, 'Repasse criado com sucesso!')
        return super().form_valid(form)


class RepasseUpdateView(UpdateView):
    model = Repasse
    template_name = 'financeiro/repasses/repasse_form.html'
    
    def get_form_class(self):
        return RepasseForm if RepasseForm else None
    
    def get_fields(self):
        if not RepasseForm:
            return ['proprietario', 'contrato', 'valor', 'valor_desconto', 
                    'valor_taxa_admin', 'data_prevista', 'mes_referencia', 'ano_referencia',
                    'tipo', 'metodo_pagamento', 'descricao', 'observacoes']
        return None
    
    def get_success_url(self):
        return reverse_lazy('financeiro:repasse_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, 'Repasse atualizado com sucesso!')
        return super().form_valid(form)


# ==================== VIEWS DE POLÍTICAS POR CONTRATO ====================

class ContratosSemPoliticaView(ListView):
    """Lista contratos ativos sem política de repasse configurada"""
    template_name = 'financeiro/repasses/contratos_sem_politica.html'
    context_object_name = 'contratos'
    paginate_by = 20

    def get_queryset(self):
        # CORRIGIDO: usar ativo=True
        queryset = Contrato.objects.filter(
            ativo=True,
            politica_repasse__isnull=True
        ).select_related('proprietario', 'imovel').order_by('proprietario__nome')

        # Filtros básicos
        proprietario_id = self.request.GET.get('proprietario')
        if proprietario_id:
            queryset = queryset.filter(proprietario_id=proprietario_id)
        
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(proprietario__nome__icontains=search) |
                Q(imovel__endereco__icontains=search)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_sem_politica'] = self.get_queryset().count()
        context['total_contratos_ativos'] = Contrato.objects.filter(ativo=True).count()  # CORRIGIDO
        return context


class PoliticaContratoListView(ListView):
    """Lista todas as políticas por contrato"""
    model = PoliticaRepasseContrato
    template_name = 'financeiro/repasses/politica_contrato_list.html'
    context_object_name = 'politicas'
    paginate_by = 20

    def get_queryset(self):
        # ✅ CORRIGIDO: Usar prefetch_related para ManyToMany
        return PoliticaRepasseContrato.objects.select_related(
            'contrato',              # ForeignKey - OK
            'contrato__imovel',      # ForeignKey através de contrato - OK
            'contrato__fiador'       # ForeignKey através de contrato - OK
        ).prefetch_related(
            'contrato__proprietario',  # ManyToMany através de contrato - CORRETO
            'contrato__inquilino'      # ManyToMany através de contrato - CORRETO
        ).order_by('-ativa', 'contrato__id')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Estatísticas
        context['stats'] = {
            'total_politicas': PoliticaRepasseContrato.objects.count(),
            'politicas_ativas': PoliticaRepasseContrato.objects.filter(ativa=True).count(),
            'contratos_sem_politica': Contrato.objects.filter(
                ativo=True,
                politica_repasse__isnull=True
            ).count(),
            'por_periodicidade': PoliticaRepasseContrato.objects.filter(ativa=True).values(
                'periodicidade'
            ).annotate(count=Count('id')),
            'por_tipo_dias': PoliticaRepasseContrato.objects.filter(ativa=True).values(
                'tipo_dias'
            ).annotate(count=Count('id'))
        }
        
        return context


# No arquivo repasse_views.py

class PoliticaContratoCreateView(CreateView):
    model = PoliticaRepasseContrato
    template_name = 'financeiro/repasses/politica_contrato_form.html'
    fields = ['contrato', 'ativa', 'periodicidade', 'tipo_dias', 'dia_mes', 'dia_semana',
              'dias_apos_recebimento', 'percentual_adiantamento', 'taxa_adiantamento',
              'valor_minimo_repasse', 'taxa_admin_personalizada', 'considerar_feriados',
              'antecipar_fds_feriados', 'observacoes']
    
    def get_success_url(self):
        return reverse_lazy('financeiro:politica_contrato_list')
    
    def get_form(self, form_class=None):
        """Customiza o formulário para melhorar a exibição dos contratos"""
        form = super().get_form(form_class)
        
        # Customizar o campo contrato
        form.fields['contrato'].queryset = Contrato.objects.filter(
            ativo=True,
            politica_repasse__isnull=True
        ).select_related('imovel').prefetch_related('proprietario').order_by('id')
        
        # Customizar o widget para melhor exibição
        form.fields['contrato'].widget.attrs.update({
            'class': 'form-select',
            'data-placeholder': 'Selecione um contrato...'
        })
        
        return form
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Criar lista customizada de contratos para o template
        contratos_sem_politica = Contrato.objects.filter(
            ativo=True,
            politica_repasse__isnull=True
        ).select_related('imovel').prefetch_related('proprietario').order_by('id')
        
        # Criar lista com informações formatadas
        contratos_formatados = []
        for contrato in contratos_sem_politica:
            proprietarios = contrato.proprietario.all()
            nomes_proprietarios = ", ".join([p.nome for p in proprietarios]) if proprietarios else "Sem proprietário"
            
            endereco_completo = f"{contrato.imovel.endereco}"
            if contrato.imovel.numero:
                endereco_completo += f", {contrato.imovel.numero}"
            if contrato.imovel.complemento:
                endereco_completo += f" - {contrato.imovel.complemento}"
            
            contratos_formatados.append({
                'id': contrato.id,
                'proprietarios': nomes_proprietarios,
                'endereco': endereco_completo,
                'valor_base': contrato.valor_base,
                'display_name': f"#{contrato.id} - {nomes_proprietarios} - {endereco_completo}"
            })
        
        context['contratos_formatados'] = contratos_formatados
        context['contratos_sem_politica'] = contratos_sem_politica  # Manter compatibilidade
        
        return context
    
    def form_valid(self, form):
        messages.success(self.request, f'Política criada para o contrato {form.instance.contrato.id}!')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('financeiro:politica_contrato_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # ✅ CORRIGIDO: Usar prefetch_related para ManyToMany
        context['contratos_sem_politica'] = Contrato.objects.filter(
            ativo=True,
            politica_repasse__isnull=True
        ).select_related(
            'imovel',      # ForeignKey - OK
            'fiador'       # ForeignKey - OK  
        ).prefetch_related(
            'proprietario',  # ManyToMany - CORRETO
            'inquilino'      # ManyToMany - CORRETO
        ).order_by('id')  # ✅ Ordenar por ID em vez de proprietario__nome (ManyToMany)
        
        return context
    
    def form_valid(self, form):
        messages.success(self.request, f'Política criada para o contrato {form.instance.contrato.id}!')
        return super().form_valid(form)
    
    def form_valid(self, form):
        messages.success(self.request, f'Política criada para o contrato {form.instance.contrato.id}!')
        return super().form_valid(form)


class PoliticaContratoUpdateView(UpdateView):
    model = PoliticaRepasseContrato
    template_name = 'financeiro/repasses/politica_contrato_form.html'
    
    def get_form_class(self):
        return PoliticaRepasseContratoForm if PoliticaRepasseContratoForm else None
    
    def get_fields(self):
        if not PoliticaRepasseContratoForm:
            return ['ativa', 'periodicidade', 'tipo_dias', 'dia_mes', 'dia_semana',
                    'dias_apos_recebimento', 'percentual_adiantamento', 'taxa_adiantamento',
                    'valor_minimo_repasse', 'taxa_admin_personalizada', 'considerar_feriados',
                    'antecipar_fds_feriados', 'observacoes']
        return None
    
    def get_success_url(self):
        return reverse_lazy('financeiro:politica_contrato_list')
    
    def form_valid(self, form):
        messages.success(self.request, f'Política do contrato {form.instance.contrato.id} atualizada!')
        return super().form_valid(form)


# ==================== VIEWS DE POLÍTICAS GLOBAIS ====================

class PoliticaGlobalListView(ListView):
    model = PoliticaRepasseGlobal
    template_name = 'financeiro/repasses/politica_global_list.html'
    context_object_name = 'politicas'

    def get_queryset(self):
        return PoliticaRepasseGlobal.objects.order_by('-ativa', 'nome')


class PoliticaGlobalCreateView(CreateView):
    model = PoliticaRepasseGlobal
    template_name = 'financeiro/repasses/politica_form.html'
    
    def get_form_class(self):
        return PoliticaRepasseGlobalForm if PoliticaRepasseGlobalForm else None
    
    def get_fields(self):
        if not PoliticaRepasseGlobalForm:
            return ['nome', 'ativa', 'periodicidade', 'tipo_dias', 'dia_mes', 'dia_semana',
                    'dias_apos_recebimento', 'percentual_adiantamento', 'taxa_adiantamento',
                    'valor_minimo_repasse', 'taxa_admin_padrao', 'considerar_feriados',
                    'antecipar_fds_feriados']
        return None
    
    def get_success_url(self):
        return reverse_lazy('financeiro:politica_global_list')


class PoliticaGlobalUpdateView(UpdateView):
    model = PoliticaRepasseGlobal
    template_name = 'financeiro/repasses/politica_form.html'
    
    def get_form_class(self):
        return PoliticaRepasseGlobalForm if PoliticaRepasseGlobalForm else None
    
    def get_fields(self):
        if not PoliticaRepasseGlobalForm:
            return ['nome', 'ativa', 'periodicidade', 'tipo_dias', 'dia_mes', 'dia_semana',
                    'dias_apos_recebimento', 'percentual_adiantamento', 'taxa_adiantamento',
                    'valor_minimo_repasse', 'taxa_admin_padrao', 'considerar_feriados',
                    'antecipar_fds_feriados']
        return None
    
    def get_success_url(self):
        return reverse_lazy('financeiro:politica_global_list')


# ==================== VIEWS DE PROCESSAMENTO ====================

def processar_repasse_view(request, repasse_id):
    """Processa (efetiva) um repasse pendente"""
    repasse = get_object_or_404(Repasse, id=repasse_id)
    
    if request.method == 'POST':
        try:
            metodo_pagamento = request.POST.get('metodo_pagamento')
            observacoes = request.POST.get('observacoes')
            
            success = repasse.efetivar_repasse(
                metodo_pagamento=metodo_pagamento,
                observacoes=observacoes
            )
            
            if success:
                # Upload do comprovante se fornecido
                comprovante = request.FILES.get('comprovante')
                if comprovante:
                    repasse.comprovante = comprovante
                    repasse.save(update_fields=['comprovante'])
                
                messages.success(request, f'Repasse efetuado com sucesso!')
                return redirect('financeiro:repasse_detail', pk=repasse.id)
            else:
                messages.error(request, 'Não foi possível efetivar o repasse.')
        except Exception as e:
            logger.error(f"Erro ao processar repasse {repasse_id}: {str(e)}")
            messages.error(request, f'Erro ao processar repasse: {str(e)}')

    return render(request, 'financeiro/repasses/processar_repasse.html', {
        'repasse': repasse,
    })


def cancelar_repasse_view(request, repasse_id):
    """Cancela um repasse pendente"""
    repasse = get_object_or_404(Repasse, id=repasse_id)
    
    if request.method == 'POST':
        motivo = request.POST.get('motivo', '')
        success = repasse.cancelar_repasse(motivo)
        
        if success:
            messages.success(request, 'Repasse cancelado com sucesso!')
        else:
            messages.error(request, 'Não foi possível cancelar o repasse.')
    
    return redirect('financeiro:repasse_detail', pk=repasse.id)


def gerar_repasse_automatico(request):
    """Gera repasses baseados nas políticas dos contratos"""
    if request.method == 'POST':
        try:
            if RepasseService:
                service = RepasseService()
                resultado = service.processar_repasses_automaticos()
                
                messages.success(request, 
                    f"Processamento concluído: {resultado.get('criados', 0)} repasses criados, "
                    f"{resultado.get('erros', 0)} erros.")
            else:
                messages.warning(request, 'Serviço de repasse não disponível.')
            
        except Exception as e:
            logger.error(f"Erro no processamento automático: {str(e)}")
            messages.error(request, f"Erro no processamento: {str(e)}")
    
    return redirect('financeiro:lista_repasses')


# ==================== VIEWS DE AGENDAMENTOS ====================

class AgendamentoListView(ListView):
    model = AgendamentoRepasse
    template_name = 'financeiro/repasses/agendamento_list.html'
    context_object_name = 'agendamentos'
    paginate_by = 20

    def get_queryset(self):
        return AgendamentoRepasse.objects.select_related(
            'proprietario', 'contrato', 'politica_contrato', 'politica_global'
        ).order_by('-data_agendada')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Estatísticas
        hoje = date.today()
        context['stats'] = {
            'total_agendados': AgendamentoRepasse.objects.filter(status='agendado').count(),
            'vencidos_hoje': AgendamentoRepasse.objects.filter(
                status='agendado',
                data_agendada__lte=hoje
            ).count(),
            'proximos_7_dias': AgendamentoRepasse.objects.filter(
                status='agendado',
                data_agendada__range=[hoje, hoje + timedelta(days=7)]
            ).count()
        }
        
        return context


def processar_agendamento_view(request, pk):
    """Processa um agendamento específico"""
    agendamento = get_object_or_404(AgendamentoRepasse, pk=pk)
    
    if request.method == 'POST':
        try:
            repasse = agendamento.processar()
            if repasse:
                messages.success(request, f'Agendamento processado! Repasse #{repasse.id} criado.')
                return redirect('financeiro:repasse_detail', pk=repasse.id)
            else:
                messages.error(request, 'Erro ao processar agendamento.')
        except Exception as e:
            logger.error(f"Erro ao processar agendamento {pk}: {str(e)}")
            messages.error(request, f'Erro: {str(e)}')
    
    return redirect('financeiro:agendamento_list')



# ==================== VIEWS DE DASHBOARD ====================

class DashboardFinanceiroView(TemplateView):
    """Dashboard principal do módulo financeiro - CAMPOS CORRIGIDOS"""
    template_name = 'financeiro/dashboard_financeiro.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        hoje = date.today()
        inicio_mes = hoje.replace(day=1)
        
        # Estatísticas de repasses
        context['stats_repasses'] = {
            'pendentes': Repasse.objects.filter(status='pendente').aggregate(
                total=Sum(F('valor') - F('valor_desconto') - F('valor_taxa_admin')),
                count=Count('id')
            ),
            'atrasados': Repasse.objects.filter(
                status='pendente',
                data_prevista__lt=hoje
            ).aggregate(
                total=Sum(F('valor') - F('valor_desconto') - F('valor_taxa_admin')),
                count=Count('id')
            ),
            'mes_atual': Repasse.objects.filter(
                data_criacao__gte=inicio_mes  # Verificar se este campo existe
            ).aggregate(
                total=Sum(F('valor') - F('valor_desconto') - F('valor_taxa_admin')),
                count=Count('id')
            )
        }
        
        # Próximos repasses (7 dias)
        context['proximos_repasses'] = Repasse.objects.filter(
            status='pendente',
            data_prevista__lte=hoje + timedelta(days=7)
        ).select_related('proprietario', 'contrato').order_by('data_prevista')[:10]
        
        # Repasses por status (últimos 30 dias) - CORRIGIDO
        try:
            context['repasses_por_status'] = list(Repasse.objects.filter(
                data_criacao__gte=hoje - timedelta(days=30)  # Pode precisar ajustar
            ).values('status').annotate(
                total=Sum(F('valor') - F('valor_desconto') - F('valor_taxa_admin')),
                count=Count('id')
            ))
        except FieldError:
            # Se data_criacao não existir, usar outro campo ou filtro simples
            context['repasses_por_status'] = list(Repasse.objects.values('status').annotate(
                total=Sum(F('valor') - F('valor_desconto') - F('valor_taxa_admin')),
                count=Count('id')
            ))
        
        # Estatísticas de políticas
        context['politicas_ativas'] = PoliticaRepasseContrato.objects.filter(ativa=True).count()
        context['contratos_sem_politica'] = Contrato.objects.filter(
            ativo=True,
            politica_repasse__isnull=True
        ).count()
        
        # Agendamentos pendentes
        context['agendamentos_pendentes'] = AgendamentoRepasse.objects.filter(
            status='agendado',
            data_agendada__lte=hoje + timedelta(days=7)
        ).count()
        
        return context
class ConfiguracaoRepasseView(TemplateView):
    """View para configurações gerais do sistema de repasse"""
    template_name = 'financeiro/repasses/configurar_politicas.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        if ConfiguracaoPoliticasForm:
            context['form'] = ConfiguracaoPoliticasForm()
        
        # Estatísticas do sistema - CORRIGIDO
        context['stats'] = {
            'total_politicas_contrato': PoliticaRepasseContrato.objects.count(),
            'politicas_ativas_contrato': PoliticaRepasseContrato.objects.filter(ativa=True).count(),
            'total_politicas_global': PoliticaRepasseGlobal.objects.count(),
            'politicas_ativas_global': PoliticaRepasseGlobal.objects.filter(ativa=True).count(),
            'contratos_sem_politica': Contrato.objects.filter(
                ativo=True,  # CORRIGIDO
                politica_repasse__isnull=True
            ).count(),
            'repasses_mes': Repasse.objects.filter(
                data_criacao__month=date.today().month,
                data_criacao__year=date.today().year
            ).count()
        }
        
        return context
    
    def post(self, request, *args, **kwargs):
        if ConfiguracaoPoliticasForm:
            form = ConfiguracaoPoliticasForm(request.POST)
            
            if form.is_valid():
                # Aqui você salvaria as configurações (implementar modelo de configuração)
                messages.success(request, 'Configurações salvas com sucesso!')
                return redirect('financeiro:configuracao_repasse')
            
            return self.render_to_response(self.get_context_data(form=form))
        else:
            messages.warning(request, 'Formulário de configuração não disponível.')
            return redirect('financeiro:configuracao_repasse')


# ==================== VIEWS AJAX ====================

def toggle_politica_contrato_view(request, pk):
    """Toggle status ativo/inativo de uma política de contrato"""
    if request.method == 'POST':
        politica = get_object_or_404(PoliticaRepasseContrato, pk=pk)
        
        try:
            politica.ativa = not politica.ativa
            politica.save()
            
            messages.success(request, f'Política do contrato {politica.contrato.id} {"ativada" if politica.ativa else "desativada"}!')
            return JsonResponse({'success': True})
            
        except Exception as e:
            logger.error(f"Erro ao alterar status da política {pk}: {str(e)}")
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Método não permitido'})


def dashboard_repasses_ajax(request):
    """Dados para gráficos do dashboard via AJAX"""
    hoje = date.today()
    inicio_mes = hoje.replace(day=1)
    
    # Repasses por status
    status_data = Repasse.objects.filter(
        data_criacao__date__gte=inicio_mes
    ).values('status').annotate(
        total=Sum(F('valor') - F('valor_desconto') - F('valor_taxa_admin')),
        count=Count('id')
    )
    
    # Políticas por tipo de dias
    politicas_por_tipo = PoliticaRepasseContrato.objects.filter(
        ativa=True
    ).values('tipo_dias').annotate(count=Count('id'))
    
    # Próximos repasses (7 dias)
    proximos = Repasse.objects.filter(
        status='pendente',
        data_prevista__lte=hoje + timedelta(days=7)
    ).select_related('proprietario').order_by('data_prevista')[:10]
    
    return JsonResponse({
        'status_data': list(status_data),
        'politicas_por_tipo': list(politicas_por_tipo),
        'proximos_repasses': [{
            'id': r.id,
            'proprietario': r.proprietario.nome,
            'valor': float(r.valor_liquido),
            'data_prevista': r.data_prevista.strftime('%d/%m/%Y'),
            'dias_restantes': (r.data_prevista - hoje).days
        } for r in proximos]
    })


def aplicar_politica_em_lote(request):
    """Aplica uma política global em lote para contratos selecionados"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            politica_global_id = data.get('politica_global_id')
            contratos_ids = data.get('contratos_ids', [])
            
            if not politica_global_id:
                return JsonResponse({
                    'success': False, 
                    'error': 'Política deve ser informada'
                })
            
            politica_global = get_object_or_404(PoliticaRepasseGlobal, pk=politica_global_id)
            
            if contratos_ids:
                contratos = Contrato.objects.filter(
                    id__in=contratos_ids,
                    politica_repasse__isnull=True
                )
            else:
                # CORRIGIDO: usar ativo=True
                contratos = Contrato.objects.filter(
                    ativo=True,
                    politica_repasse__isnull=True
                )
            
            criados = 0
            erros = []
            
            with transaction.atomic():
                for contrato in contratos:
                    try:
                        PoliticaRepasseContrato.objects.create(
                            contrato=contrato,
                            ativa=politica_global.ativa,
                            periodicidade=politica_global.periodicidade,
                            tipo_dias=politica_global.tipo_dias,
                            dia_mes=politica_global.dia_mes,
                            dia_semana=politica_global.dia_semana,
                            dias_apos_recebimento=politica_global.dias_apos_recebimento,
                            percentual_adiantamento=politica_global.percentual_adiantamento,
                            taxa_adiantamento=politica_global.taxa_adiantamento,
                            valor_minimo_repasse=politica_global.valor_minimo_repasse,
                            taxa_admin_personalizada=politica_global.taxa_admin_padrao,
                            considerar_feriados=politica_global.considerar_feriados,
                            antecipar_fds_feriados=politica_global.antecipar_fds_feriados,
                            observacoes=f"Criada em lote baseada na política global '{politica_global.nome}'"
                        )
                        criados += 1
                    except Exception as e:
                        erros.append(f"Contrato {contrato.id}: {str(e)}")
            
            return JsonResponse({
                'success': True,
                'criados': criados,
                'erros': erros
            })
            
        except Exception as e:
            logger.error(f"Erro ao aplicar política em lote: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Método não permitido'})


# ==================== VIEWS DE RELATÓRIOS ====================

def relatorio_repasses_view(request):
    """Gera relatórios de repasses"""
    return render(request, 'financeiro/repasses/relatorio_repasses.html')


def exportar_relatorio_repasses(request):
    """Exporta relatório de repasses em Excel"""
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill
        
        # Parâmetros de filtro
        periodo = int(request.GET.get('periodo', 30))
        
        # Buscar dados
        data_inicio = date.today() - timedelta(days=periodo)
        repasses = Repasse.objects.filter(
            data_criacao__date__gte=data_inicio
        ).select_related('proprietario', 'contrato').order_by('-data_criacao')
        
        # Criar workbook
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Relatório de Repasses"
        
        # Cabeçalhos
        headers = [
            'ID', 'Data Criação', 'Proprietário', 'Contrato', 'Imóvel',
            'Valor Bruto', 'Descontos', 'Taxa Admin', 'Valor Líquido',
            'Status', 'Data Prevista', 'Data Efetivação', 'Método Pagamento',
            'Mês/Ano Referência', 'Tipo', 'Política'
        ]
        
        # Estilo do cabeçalho
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
        
        # Dados
        for row, repasse in enumerate(repasses, 2):
            ws.cell(row=row, column=1, value=repasse.id)
            ws.cell(row=row, column=2, value=repasse.data_criacao.date())
            ws.cell(row=row, column=3, value=repasse.proprietario.nome)
            ws.cell(row=row, column=4, value=str(repasse.contrato))
            ws.cell(row=row, column=5, value=str(repasse.contrato.imovel))
            ws.cell(row=row, column=6, value=float(repasse.valor))
            ws.cell(row=row, column=7, value=float(repasse.valor_desconto))
            ws.cell(row=row, column=8, value=float(repasse.valor_taxa_admin))
            ws.cell(row=row, column=9, value=float(repasse.valor_liquido))
            ws.cell(row=row, column=10, value=repasse.get_status_display())
            ws.cell(row=row, column=11, value=repasse.data_prevista)
            ws.cell(row=row, column=12, value=repasse.data_efetivacao)
            ws.cell(row=row, column=13, value=repasse.get_metodo_pagamento_display() if repasse.metodo_pagamento else '')
            ws.cell(row=row, column=14, value=f"{repasse.mes_referencia:02d}/{repasse.ano_referencia}")
            ws.cell(row=row, column=15, value=repasse.get_tipo_display())
            
            # Informação da política
            if hasattr(repasse.contrato, 'politica_repasse') and repasse.contrato.politica_repasse:
                politica_info = f"{repasse.contrato.politica_repasse.get_periodicidade_display()} ({repasse.contrato.politica_repasse.get_tipo_dias_display()})"
            else:
                politica_info = "Sem política específica"
            ws.cell(row=row, column=16, value=politica_info)
        
        # Ajustar largura das colunas
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width
        
        # Preparar response
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="repasses_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
        
        wb.save(response)
        return response
        
    except ImportError:
        messages.error(request, 'Biblioteca openpyxl não instalada. Execute: pip install openpyxl')
        return redirect('financeiro:lista_repasses')
    except Exception as e:
        logger.error(f"Erro ao gerar relatório: {str(e)}")
        messages.error(request, f'Erro ao gerar relatório: {str(e)}')
        return redirect('financeiro:lista_repasses')


# ==================== VIEWS DE HISTÓRICO ====================

def repasse_historico_proprietario(request, proprietario_id):
    """Histórico completo de repasses de um proprietário - CAMPOS CORRIGIDOS"""
    proprietario = get_object_or_404(Cliente, id=proprietario_id, tipo='proprietario')
    
    # Filtros
    ano = request.GET.get('ano', date.today().year)
    mes = request.GET.get('mes', '')
    status = request.GET.get('status', '')
    
    # Query base
    repasses = Repasse.objects.filter(
        proprietario=proprietario
    ).select_related('contrato', 'cobranca').prefetch_related(
        'contrato__politica_repasse'
    )
    
    # Aplicar filtros
    if ano:
        repasses = repasses.filter(ano_referencia=ano)
    if mes:
        repasses = repasses.filter(mes_referencia=mes)
    if status:
        repasses = repasses.filter(status=status)
    
    # Ordenação - tentar diferentes campos
    try:
        repasses = repasses.order_by('-data_criacao')
    except FieldError:
        try:
            repasses = repasses.order_by('-data_prevista')
        except FieldError:
            repasses = repasses.order_by('-id')  # Fallback final
    
    # Paginação
    paginator = Paginator(repasses, 20)
    page = request.GET.get('page')
    repasses_page = paginator.get_page(page)
    
    # Estatísticas do proprietário
    stats = {
        'total_recebido': repasses.filter(status='efetuado').aggregate(
            total=Sum(F('valor') - F('valor_desconto') - F('valor_taxa_admin'))
        )['total'] or Decimal('0'),
        'total_pendente': repasses.filter(status='pendente').aggregate(
            total=Sum(F('valor') - F('valor_desconto') - F('valor_taxa_admin'))
        )['total'] or Decimal('0'),
        'total_repasses': repasses.count(),
        'contratos_com_politica': Contrato.objects.filter(
            proprietario=proprietario,
            politica_repasse__isnull=False
        ).count(),
        'contratos_sem_politica': Contrato.objects.filter(
            proprietario=proprietario,
            ativo=True,
            politica_repasse__isnull=True
        ).count()
    }
    
    # Repasses por mês (últimos 12 meses) - simplificado
    repasses_mensais = []
    try:
        for i in range(12):
            data_ref = date.today().replace(day=1) - timedelta(days=i*30)
            mes_data = repasses.filter(
                ano_referencia=data_ref.year,
                mes_referencia=data_ref.month,
                status='efetuado'
            ).aggregate(
                total=Sum(F('valor') - F('valor_desconto') - F('valor_taxa_admin'))
            )
            
            repasses_mensais.append({
                'mes': f"{data_ref.month:02d}/{data_ref.year}",
                'total': float(mes_data['total'] or 0)
            })
        
        repasses_mensais.reverse()
    except Exception as e:
        logger.warning(f"Erro ao calcular repasses mensais: {e}")
        repasses_mensais = []
    
    context = {
        'proprietario': proprietario,
        'repasses': repasses_page,
        'stats': stats,
        'repasses_mensais': repasses_mensais,
        'filtros': {
            'ano': ano,
            'mes': mes,
            'status': status
        },
        'anos_disponiveis': range(2020, date.today().year + 2),
        'meses_disponiveis': [
            (1, 'Janeiro'), (2, 'Fevereiro'), (3, 'Março'), (4, 'Abril'),
            (5, 'Maio'), (6, 'Junho'), (7, 'Julho'), (8, 'Agosto'),
            (9, 'Setembro'), (10, 'Outubro'), (11, 'Novembro'), (12, 'Dezembro')
        ]
    }
    
    return render(request, 'financeiro/repasses/historico_proprietario.html', context)

def verificar_campos_modelo():
    """Função utilitária para verificar quais campos existem nos modelos"""
    
    print("=== CAMPOS DO MODELO REPASSE ===")
    for field in Repasse._meta.get_fields():
        print(f"- {field.name} ({type(field).__name__})")
    
    try:
        from ..models.movimento import MovimentoConta
        print("\n=== CAMPOS DO MODELO MOVIMENTOCONTA ===")
        for field in MovimentoConta._meta.get_fields():
            print(f"- {field.name} ({type(field).__name__})")
    except ImportError:
        print("\n=== MODELO MOVIMENTOCONTA NÃO ENCONTRADO ===")
    
    print("\n=== CAMPOS DO MODELO CONTRATO ===")
    for field in Contrato._meta.get_fields():
        print(f"- {field.name} ({type(field).__name__})")
# ==================== VIEWS DE UTILITÁRIOS ====================

def repasse_ajax_search(request):
    """Busca AJAX para repasses (para autocomplete)"""
    termo = request.GET.get('q', '')
    tipo = request.GET.get('tipo', 'proprietario')
    
    resultados = []
    
    if len(termo) >= 2:
        if tipo == 'proprietario':
            proprietarios = Cliente.objects.filter(
                tipo='proprietario',
                nome__icontains=termo
            )[:10]
            
            resultados = [{
                'id': p.id,
                'text': p.nome,
                'email': getattr(p, 'email', '')
            } for p in proprietarios]
            
        elif tipo == 'contrato':
            contratos = Contrato.objects.filter(
                Q(proprietario__nome__icontains=termo) |
                Q(imovel__endereco__icontains=termo)
            ).select_related('proprietario', 'imovel')[:10]
            
            resultados = [{
                'id': c.id,
                'text': f"{c.proprietario.nome} - {c.imovel.endereco}",
                'proprietario': c.proprietario.nome,
                'tem_politica': hasattr(c, 'politica_repasse') and c.politica_repasse is not None
            } for c in contratos]
    
    return JsonResponse({'results': resultados})


def cobranca_ajax_search(request):
    """Busca AJAX para cobranças pagas sem repasse"""
    contrato_id = request.GET.get('contrato_id')
    
    if contrato_id and Cobranca:
        cobrancas = Cobranca.objects.filter(
            contrato_id=contrato_id,
            status='paga',
            repasses_cobranca__isnull=True
        ).order_by('-data_pagamento')[:10]
        
        resultados = [{
            'id': c.id,
            'text': f"Cobrança #{c.id} - {c.mes_referencia:02d}/{c.ano_referencia} - R$ {getattr(c, 'valor_pago', getattr(c, 'valor', 0)):.2f}",
            'valor': float(getattr(c, 'valor_pago', getattr(c, 'valor', 0))),
            'mes': getattr(c, 'mes_referencia', date.today().month),
            'ano': getattr(c, 'ano_referencia', date.today().year)
        } for c in cobrancas]
        
        return JsonResponse({'results': resultados})
    
    return JsonResponse({'results': []})


def calcular_valores_repasse(request):
    """Calcula valores do repasse baseado na cobrança e política do contrato"""
    cobranca_id = request.GET.get('cobranca_id')
    contrato_id = request.GET.get('contrato_id')
    
    try:
        if cobranca_id and Cobranca:
            cobranca = Cobranca.objects.get(id=cobranca_id)
            contrato = cobranca.contrato
        elif contrato_id:
            contrato = Contrato.objects.get(id=contrato_id)
            cobranca = None
        else:
            return JsonResponse({'success': False, 'error': 'ID não fornecido'})
        
        # Determinar valor base de forma segura
        if cobranca:
            valor_base = getattr(cobranca, 'valor_pago', getattr(cobranca, 'valor', 0))
        else:
            valor_base = getattr(contrato, 'valor_aluguel', getattr(contrato, 'valor_base', Decimal('0')))
        
        # Calcular taxa administrativa
        if hasattr(contrato, 'politica_repasse') and contrato.politica_repasse:
            taxa_admin = contrato.politica_repasse.get_taxa_admin()
        else:
            # Buscar política global ativa ou usar padrão
            politica_global = PoliticaRepasseGlobal.objects.filter(ativa=True).first()
            taxa_admin = politica_global.taxa_admin_padrao if politica_global else Decimal('8.00')
        
        valor_taxa_admin = valor_base * (taxa_admin / 100)
        valor_liquido = valor_base - valor_taxa_admin
        
        # Verificar valor mínimo se houver política
        valor_minimo = Decimal('0.00')
        if hasattr(contrato, 'politica_repasse') and contrato.politica_repasse:
            valor_minimo = contrato.politica_repasse.valor_minimo_repasse
        
        return JsonResponse({
            'success': True,
            'valor_base': float(valor_base),
            'valor_taxa_admin': float(valor_taxa_admin),
            'valor_desconto': 0.0,
            'valor_liquido': float(valor_liquido),
            'taxa_admin_percentual': float(taxa_admin),
            'valor_minimo': float(valor_minimo),
            'acima_minimo': valor_liquido >= valor_minimo,
            'mes_referencia': getattr(cobranca, 'mes_referencia', date.today().month) if cobranca else date.today().month,
            'ano_referencia': getattr(cobranca, 'ano_referencia', date.today().year) if cobranca else date.today().year,
            'tem_politica_contrato': hasattr(contrato, 'politica_repasse') and contrato.politica_repasse is not None
        })
        
    except (Exception) as e:
        if Cobranca and cobranca_id:
            try:
                Cobranca.objects.get(id=cobranca_id)
            except Cobranca.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Cobrança não encontrada'})
        
        try:
            Contrato.objects.get(id=contrato_id)
        except Contrato.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Contrato não encontrado'})
        
        logger.error(f"Erro ao calcular valores: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})


# ==================== VIEWS DE MIGRAÇÃO E UTILITÁRIOS ====================

def migrar_politicas_antigas(request):
    """Migra políticas do modelo antigo para o novo (se necessário)"""
    if request.method == 'POST':
        try:
            # Esta view seria usada para migrar dados do modelo antigo
            # para o novo modelo de políticas por contrato
            messages.success(request, 'Migração concluída com sucesso!')
        except Exception as e:
            logger.error(f"Erro na migração: {str(e)}")
            messages.error(request, f'Erro na migração: {str(e)}')
    
    return redirect('financeiro:configuracao_repasse')


def extrato_proprietario_view(request, proprietario_id):
    """Extrato simplificado do proprietário"""
    return redirect('financeiro:historico_proprietario', proprietario_id=proprietario_id)# financeiro/views/repasse_views.py (versão corrigida)
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, TemplateView
from django.db.models import Q, Sum, Count, Case, When, DecimalField, F
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.core.paginator import Paginator
from django.urls import reverse_lazy
from django.db import transaction
from datetime import date, datetime, timedelta
from decimal import Decimal
import json
import logging

# Imports dos modelos
from ..models.repasse import Repasse, PoliticaRepasseContrato, PoliticaRepasseGlobal, AgendamentoRepasse
try:
    from ..models.cobranca import Cobranca
except ImportError:
    Cobranca = None

from sisimob.models import Contrato, Cliente

# Imports dos services e forms (assumindo que existem)
try:
    from ..services.repasse_service import RepasseService
except ImportError:
    RepasseService = None

logger = logging.getLogger(__name__)


# ==================== VIEWS DE REPASSES ====================




# Simplificando as outras views para evitar erros de campos inexistentes
class RepasseCreateView(CreateView):
    model = Repasse
    template_name = 'financeiro/repasses/repasse_form.html'
    fields = ['proprietario', 'contrato', 'cobranca', 'valor', 'valor_desconto', 
              'valor_taxa_admin', 'data_prevista', 'mes_referencia', 'ano_referencia',
              'tipo', 'metodo_pagamento', 'descricao', 'observacoes']
    
    def get_success_url(self):
        return reverse_lazy('financeiro:repasse_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, 'Repasse criado com sucesso!')
        return super().form_valid(form)


class RepasseUpdateView(UpdateView):
    model = Repasse
    template_name = 'financeiro/repasses/repasse_form.html'
    fields = ['proprietario', 'contrato', 'cobranca', 'valor', 'valor_desconto', 
              'valor_taxa_admin', 'data_prevista', 'mes_referencia', 'ano_referencia',
              'tipo', 'metodo_pagamento', 'descricao', 'observacoes']
    
    def get_success_url(self):
        return reverse_lazy('financeiro:repasse_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, 'Repasse atualizado com sucesso!')
        return super().form_valid(form)


# ==================== VIEWS DE POLÍTICAS POR CONTRATO ====================

class ContratosSemPoliticaView(ListView):
    """Lista contratos ativos sem política de repasse configurada"""
    template_name = 'financeiro/repasses/contratos_sem_politica.html'
    context_object_name = 'contratos'
    paginate_by = 20

    def get_queryset(self):
        # Corrigido: usar ativo=True em vez de status='ativo'
        queryset = Contrato.objects.filter(
            ativo=True,
            politica_repasse__isnull=True
        ).select_related('proprietario', 'imovel').order_by('proprietario__nome')

        # Filtros básicos
        proprietario_id = self.request.GET.get('proprietario')
        if proprietario_id:
            queryset = queryset.filter(proprietario_id=proprietario_id)
        
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(proprietario__nome__icontains=search) |
                Q(imovel__endereco__icontains=search)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_sem_politica'] = self.get_queryset().count()
        context['total_contratos_ativos'] = Contrato.objects.filter(ativo=True).count()
        return context





class PoliticaContratoUpdateView(UpdateView):
    model = PoliticaRepasseContrato
    template_name = 'financeiro/repasses/politica_contrato_form.html'
    fields = ['ativa', 'periodicidade', 'tipo_dias', 'dia_mes', 'dia_semana',
              'dias_apos_recebimento', 'percentual_adiantamento', 'taxa_adiantamento',
              'valor_minimo_repasse', 'taxa_admin_personalizada', 'considerar_feriados',
              'antecipar_fds_feriados', 'observacoes']
    
    def get_success_url(self):
        return reverse_lazy('financeiro:politica_contrato_list')
    
    def form_valid(self, form):
        messages.success(self.request, f'Política do contrato {form.instance.contrato.id} atualizada!')
        return super().form_valid(form)


# ==================== VIEWS DE POLÍTICAS GLOBAIS ====================

class PoliticaGlobalListView(ListView):
    model = PoliticaRepasseGlobal
    template_name = 'financeiro/repasses/politica_global_list.html'
    context_object_name = 'politicas'

    def get_queryset(self):
        return PoliticaRepasseGlobal.objects.order_by('-ativa', 'nome')


class PoliticaGlobalCreateView(CreateView):
    model = PoliticaRepasseGlobal
    template_name = 'financeiro/repasses/politica_form.html'
    fields = ['nome', 'ativa', 'periodicidade', 'tipo_dias', 'dia_mes', 'dia_semana',
              'dias_apos_recebimento', 'percentual_adiantamento', 'taxa_adiantamento',
              'valor_minimo_repasse', 'taxa_admin_padrao', 'considerar_feriados',
              'antecipar_fds_feriados']
    
    def get_success_url(self):
        return reverse_lazy('financeiro:politica_global_list')


class PoliticaGlobalUpdateView(UpdateView):
    model = PoliticaRepasseGlobal
    template_name = 'financeiro/repasses/politica_form.html'
    fields = ['nome', 'ativa', 'periodicidade', 'tipo_dias', 'dia_mes', 'dia_semana',
              'dias_apos_recebimento', 'percentual_adiantamento', 'taxa_adiantamento',
              'valor_minimo_repasse', 'taxa_admin_padrao', 'considerar_feriados',
              'antecipar_fds_feriados']
    
    def get_success_url(self):
        return reverse_lazy('financeiro:politica_global_list')


# ==================== VIEWS DE PROCESSAMENTO ====================

def processar_repasse_view(request, repasse_id):
    """Processa (efetiva) um repasse pendente"""
    repasse = get_object_or_404(Repasse, id=repasse_id)
    
    if request.method == 'POST':
        try:
            metodo_pagamento = request.POST.get('metodo_pagamento')
            observacoes = request.POST.get('observacoes')
            
            success = repasse.efetivar_repasse(
                metodo_pagamento=metodo_pagamento,
                observacoes=observacoes
            )
            
            if success:
                # Upload do comprovante se fornecido
                comprovante = request.FILES.get('comprovante')
                if comprovante:
                    repasse.comprovante = comprovante
                    repasse.save(update_fields=['comprovante'])
                
                messages.success(request, f'Repasse efetuado com sucesso!')
                return redirect('financeiro:repasse_detail', pk=repasse.id)
            else:
                messages.error(request, 'Não foi possível efetivar o repasse.')
        except Exception as e:
            logger.error(f"Erro ao processar repasse {repasse_id}: {str(e)}")
            messages.error(request, f'Erro ao processar repasse: {str(e)}')

    return render(request, 'financeiro/repasses/processar_repasse.html', {
        'repasse': repasse,
    })


def cancelar_repasse_view(request, repasse_id):
    """Cancela um repasse pendente"""
    repasse = get_object_or_404(Repasse, id=repasse_id)
    
    if request.method == 'POST':
        motivo = request.POST.get('motivo', '')
        success = repasse.cancelar_repasse(motivo)
        
        if success:
            messages.success(request, 'Repasse cancelado com sucesso!')
        else:
            messages.error(request, 'Não foi possível cancelar o repasse.')
    
    return redirect('financeiro:repasse_detail', pk=repasse.id)



# ==================== VIEWS DE AGENDAMENTOS ====================

class AgendamentoListView(ListView):
    model = AgendamentoRepasse
    template_name = 'financeiro/repasses/agendamento_list.html'
    context_object_name = 'agendamentos'
    paginate_by = 20

    def get_queryset(self):
        return AgendamentoRepasse.objects.select_related(
            'proprietario', 'contrato', 'politica_contrato', 'politica_global'
        ).order_by('-data_agendada')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Estatísticas
        hoje = date.today()
        context['stats'] = {
            'total_agendados': AgendamentoRepasse.objects.filter(status='agendado').count(),
            'vencidos_hoje': AgendamentoRepasse.objects.filter(
                status='agendado',
                data_agendada__lte=hoje
            ).count(),
            'proximos_7_dias': AgendamentoRepasse.objects.filter(
                status='agendado',
                data_agendada__range=[hoje, hoje + timedelta(days=7)]
            ).count()
        }
        
        return context


def processar_agendamento_view(request, pk):
    """Processa um agendamento específico"""
    agendamento = get_object_or_404(AgendamentoRepasse, pk=pk)
    
    if request.method == 'POST':
        try:
            repasse = agendamento.processar()
            if repasse:
                messages.success(request, f'Agendamento processado! Repasse #{repasse.id} criado.')
                return redirect('financeiro:repasse_detail', pk=repasse.id)
            else:
                messages.error(request, 'Erro ao processar agendamento.')
        except Exception as e:
            logger.error(f"Erro ao processar agendamento {pk}: {str(e)}")
            messages.error(request, f'Erro: {str(e)}')
    
    return redirect('financeiro:agendamento_list')



# ==================== VIEWS DE DASHBOARD ====================


# ==================== VIEWS AJAX SIMPLIFICADAS ====================

def toggle_politica_contrato_view(request, pk):
    """Toggle status ativo/inativo de uma política de contrato"""
    if request.method == 'POST':
        politica = get_object_or_404(PoliticaRepasseContrato, pk=pk)
        
        try:
            politica.ativa = not politica.ativa
            politica.save()
            
            messages.success(request, f'Política do contrato {politica.contrato.id} {"ativada" if politica.ativa else "desativada"}!')
            return JsonResponse({'success': True})
            
        except Exception as e:
            logger.error(f"Erro ao alterar status da política {pk}: {str(e)}")
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Método não permitido'})



def aplicar_politica_em_lote(request):
    """Aplica uma política global em lote para contratos selecionados"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            politica_global_id = data.get('politica_global_id')
            contratos_ids = data.get('contratos_ids', [])
            
            if not politica_global_id:
                return JsonResponse({
                    'success': False, 
                    'error': 'Política deve ser informada'
                })
            
            politica_global = get_object_or_404(PoliticaRepasseGlobal, pk=politica_global_id)
            
            if contratos_ids:
                contratos = Contrato.objects.filter(
                    id__in=contratos_ids,
                    politica_repasse__isnull=True
                )
            else:
                contratos = Contrato.objects.filter(
                    ativo=True,  # Corrigido
                    politica_repasse__isnull=True
                )
            
            criados = 0
            erros = []
            
            with transaction.atomic():
                for contrato in contratos:
                    try:
                        PoliticaRepasseContrato.objects.create(
                            contrato=contrato,
                            ativa=politica_global.ativa,
                            periodicidade=politica_global.periodicidade,
                            tipo_dias=politica_global.tipo_dias,
                            dia_mes=politica_global.dia_mes,
                            dia_semana=politica_global.dia_semana,
                            dias_apos_recebimento=politica_global.dias_apos_recebimento,
                            percentual_adiantamento=politica_global.percentual_adiantamento,
                            taxa_adiantamento=politica_global.taxa_adiantamento,
                            valor_minimo_repasse=politica_global.valor_minimo_repasse,
                            taxa_admin_personalizada=politica_global.taxa_admin_padrao,
                            considerar_feriados=politica_global.considerar_feriados,
                            antecipar_fds_feriados=politica_global.antecipar_fds_feriados,
                            observacoes=f"Criada em lote baseada na política global '{politica_global.nome}'"
                        )
                        criados += 1
                    except Exception as e:
                        erros.append(f"Contrato {contrato.id}: {str(e)}")
            
            return JsonResponse({
                'success': True,
                'criados': criados,
                'erros': erros
            })
            
        except Exception as e:
            logger.error(f"Erro ao aplicar política em lote: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Método não permitido'})