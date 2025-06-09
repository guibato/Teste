# financeiro/views/cobranca_views.py
"""
Views para gerenciamento de Cobranças - Refatoradas
===================================================
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.views.generic import ListView, CreateView, UpdateView, DetailView
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from datetime import date
from django.db.models import Q, Sum, Count, Case, When, DecimalField, F
from django.utils import timezone
from django.core.paginator import Paginator
from django.urls import reverse_lazy
from datetime import date, datetime, timedelta  # ← IMPORTANTE
from decimal import Decimal
import json
import traceback

from ..models import Cobranca
from ..forms.cobranca_forms import (
    CobrancaCreateForm, CobrancaUpdateForm, CobrancaFiltroForm,
    CobrancaIntegracaoAsaasForm, CobrancaMarcarPagaForm
)
from financeiro.services.cobranca.cobranca_consulta_service import CobrancaConsultaService
from financeiro.services.cobranca.cobranca_estatistica_service import CobrancaEstatisticaService
from financeiro.services.cobranca.cobranca_calculadora_service import CobrancaCalculadoraService
from financeiro.services.cobranca.asaas_integracao_service import AsaasIntegracaoService


class CobrancaListView(ListView):
    """
    View para listagem de cobranças com filtros e paginação otimizada
    """
    model = Cobranca
    template_name = 'financeiro/cobranca/cobranca_list.html'
    context_object_name = 'cobrancas'
    paginate_by = 20
    
    def get_queryset(self):
        """Aplica filtros usando o service"""
        filtros = self._extrair_filtros()
        return CobrancaConsultaService.filtrar_cobrancas(filtros)
    
    def get_context_data(self, **kwargs):
        """Adiciona dados extras ao contexto"""
        context = super().get_context_data(**kwargs)
        
        # Filtros atuais
        filtros_atuais = self._extrair_filtros()
        context.update({
            'filtro_status': filtros_atuais.get('status', 'pendente'),
            'filtro_mes': filtros_atuais.get('mes', ''),
            'filtro_ano': filtros_atuais.get('ano', ''),
            'filtro_contrato': filtros_atuais.get('contrato', ''),
            'filtro_inquilino': filtros_atuais.get('inquilino', ''),
        })
        
        # Estatísticas usando service
        estatisticas = CobrancaEstatisticaService.calcular_estatisticas(filtros_atuais)
        context.update(estatisticas)
        
        # Form de filtros
        context['form_filtros'] = CobrancaFiltroForm(initial=filtros_atuais)
        
        return context
    
    def _extrair_filtros(self):
        """Extrai filtros dos parâmetros GET"""
        return {
            'status': self.request.GET.get('status', 'pendente'),
            'mes': self.request.GET.get('mes_referencia'),
            'ano': self.request.GET.get('ano_referencia'),
            'contrato': self.request.GET.get('contrato', '').strip(),
            'inquilino': self.request.GET.get('inquilino', '').strip(),
        }


class CobrancaCreateView(CreateView):
    """
    View para criação de novas cobranças
    """
    model = Cobranca
    form_class = CobrancaCreateForm
    template_name = 'financeiro/cobranca/cobranca_form.html'
    success_url = reverse_lazy('financeiro:cobranca_list')
    
    def form_valid(self, form):
        """Processa formulário válido com logging"""
        try:
            cobranca = form.save()
            
            messages.success(
                self.request,
                f'Cobrança {cobranca.data_referencia_texto} criada com sucesso! '
                f'Valor: R$ {cobranca.valor_total:,.2f}'
            )
            
            # Log da ação
            self._log_acao('criacao', cobranca)
            
            # Redirecionar para detail se solicitado
            if 'save_and_view' in self.request.POST:
                return redirect('financeiro:cobranca_detail', pk=cobranca.pk)
            
            return redirect(self.success_url)
            
        except Exception as e:
            messages.error(
                self.request,
                f'Erro ao criar cobrança: {str(e)}'
            )
            return self.form_invalid(form)
    
    def form_invalid(self, form):
        """Trata formulário inválido"""
        messages.error(
            self.request,
            'Erro ao criar cobrança. Verifique os dados informados.'
        )
        return super().form_invalid(form)
    
    def get_context_data(self, **kwargs):
        """Adiciona dados ao contexto"""
        context = super().get_context_data(**kwargs)
        context.update({
            'titulo': 'Nova Cobrança',
            'botao_submit': 'Criar Cobrança',
            'show_preview': True,
        })
        return context
    
    def _log_acao(self, acao, cobranca):
        """Log de ações para auditoria"""
        # TODO: Implementar sistema de logs/auditoria
        pass


class CobrancaUpdateView(UpdateView):
    """
    View para edição de cobranças existentes
    """
    model = Cobranca
    form_class = CobrancaUpdateForm
    template_name = 'financeiro/cobranca/cobranca_form.html'
    success_url = reverse_lazy('financeiro:cobranca_list')
    
    def get_object(self, queryset=None):
        """Busca objeto com prefetch otimizado"""
        return get_object_or_404(
            Cobranca.objects.select_related('contrato').prefetch_related('asaas_integracao'),
            pk=self.kwargs['pk']
        )
    
    def form_valid(self, form):
        """Processa formulário válido"""
        try:
            cobranca_original = Cobranca.objects.get(pk=self.object.pk)
            cobranca = form.save()
            
            # Verificar se houve mudanças significativas
            mudancas = self._detectar_mudancas(cobranca_original, cobranca)
            
            messages.success(
                self.request,
                f'Cobrança {cobranca.data_referencia_texto} atualizada com sucesso!'
            )
            
            if mudancas:
                messages.info(
                    self.request,
                    f'Alterações detectadas: {", ".join(mudancas)}'
                )
            
            # Log da ação
            self._log_acao('edicao', cobranca, mudancas)
            
            return redirect('financeiro:cobranca_detail', pk=cobranca.pk)
            
        except Exception as e:
            messages.error(
                self.request,
                f'Erro ao atualizar cobrança: {str(e)}'
            )
            return self.form_invalid(form)
    
    def form_invalid(self, form):
        """Trata formulário inválido"""
        messages.error(
            self.request,
            'Erro ao atualizar cobrança. Verifique os dados informados.'
        )
        return super().form_invalid(form)
    
    def get_context_data(self, **kwargs):
        """Adiciona dados ao contexto"""
        context = super().get_context_data(**kwargs)
        
        # Verificar restrições de edição
        restricoes = self._verificar_restricoes_edicao()
        
        context.update({
            'titulo': f'Editar Cobrança - {self.object.data_referencia_texto}',
            'botao_submit': 'Salvar Alterações',
            'restricoes_edicao': restricoes,
            'ja_integrada': bool(getattr(self.object, 'asaas_integracao', None)),
        })
        return context
    
    def _detectar_mudancas(self, original, atual):
        """Detecta mudanças significativas"""
        mudancas = []
        
        campos_importantes = ['valor_aluguel', 'valor_total', 'data_vencimento', 'status']
        
        for campo in campos_importantes:
            valor_original = getattr(original, campo)
            valor_atual = getattr(atual, campo)
            
            if valor_original != valor_atual:
                mudancas.append(campo.replace('_', ' ').title())
        
        return mudancas
    
    def _verificar_restricoes_edicao(self):
        """Verifica restrições para edição"""
        restricoes = []
        
        if hasattr(self.object, 'asaas_integracao') and self.object.asaas_integracao:
            restricoes.append('Cobrança integrada com Asaas - alterações limitadas')
        
        if self.object.status == 'paga':
            restricoes.append('Cobrança já foi paga - alterações limitadas')
        
        return restricoes
    
    def _log_acao(self, acao, cobranca, mudancas=None):
        """Log de ações para auditoria"""
        # TODO: Implementar sistema de logs/auditoria
        pass


class CobrancaDetailView(DetailView):
    """
    View para visualização detalhada de uma cobrança
    """
    model = Cobranca
    template_name = 'financeiro/cobranca/cobranca_detail.html'
    context_object_name = 'cobranca'
    
    def get_object(self, queryset=None):
        """Busca objeto com related otimizado"""
        return get_object_or_404(
            Cobranca.objects.select_related('contrato')
                            .prefetch_related('asaas_integracao'),
            pk=self.kwargs['pk']
        )
    
    def get_context_data(self, **kwargs):
        """Adiciona informações detalhadas ao contexto"""
        context = super().get_context_data(**kwargs)
        
        # Detalhes financeiros
        context['detalhes_financeiros'] = self.object.get_detalhes_financeiros()
        
        # Status da cobrança
        context.update({
            'esta_atrasada': self.object.esta_atrasada,
            'dias_atraso': self.object.dias_atraso,
            'esta_quitada': self.object.is_quitada,
        })
        
        # Informações de integração Asaas
        asaas_integracao = getattr(self.object, 'asaas_integracao', None)
        context.update({
            'tem_integracao_asaas': bool(asaas_integracao and asaas_integracao.asaas_id),
            'pode_integrar_asaas': not asaas_integracao,
            'asaas_dados': asaas_integracao if asaas_integracao else None,
        })
        
        # Despesas relacionadas
        context['despesas_incluidas'] = self.object.get_despesas_cobranca()
        
        # Forms para ações rápidas
        context['form_marcar_paga'] = CobrancaMarcarPagaForm()
        
        # Ações disponíveis
        context['acoes_disponiveis'] = self._calcular_acoes_disponiveis()
        
        return context
    
    def _calcular_acoes_disponiveis(self):
        """Calcula quais ações estão disponíveis"""
        acoes = {
            'pode_editar': True,
            'pode_marcar_paga': self.object.status in ['pendente', 'atrasada'],
            'pode_cancelar': self.object.status not in ['paga', 'cancelada'],
            'pode_integrar_asaas': (
                not hasattr(self.object, 'asaas_integracao') or 
                not self.object.asaas_integracao
            ),
            'pode_reenviar': (
                hasattr(self.object, 'asaas_integracao') and 
                self.object.asaas_integracao and 
                self.object.asaas_integracao.asaas_id
            ),
        }
        return acoes


@require_http_methods(["GET", "POST"])
def cobranca_integrar_asaas(request, pk):
    """
    View para integrar cobrança com o Asaas
    """
    cobranca = get_object_or_404(Cobranca, pk=pk)
    
    # Verificar se pode ser integrada
    asaas_integracao, created = AsaasIntegracao.objects.get_or_create(
        cobranca=cobranca
    )
    
    pode_integrar, erros = asaas_integracao.pode_ser_integrada()
    
    if not pode_integrar:
        messages.error(request, f'Não é possível integrar: {"; ".join(erros)}')
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
                
                # Integrar usando service
                resultado = AsaasIntegracaoService.criar_cobranca(asaas_integracao, opcoes)
                
                if resultado['status'] == 'success':
                    messages.success(
                        request,
                        'Cobrança integrada com Asaas com sucesso! '
                        'Boleto e PIX foram gerados automaticamente.'
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
        'detalhes_financeiros': cobranca.get_detalhes_financeiros(),
    }
    
    return render(request, 'financeiro/cobranca/cobranca_integrar_asaas.html', context)


def cobranca_marcar_paga(request, pk):
    """
    View para marcar cobrança como paga - VERSÃO CORRIGIDA
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
            
            # Debug para ver os dados recebidos
            print(f"📝 Dados recebidos: data={data_pagamento}, valor={valor_pago}, metodo={metodo_pagamento}")
            
            # Validações
            if not data_pagamento:
                messages.error(request, 'Data de pagamento é obrigatória.')
                context = {'cobranca': cobranca, 'hoje': timezone.now().date()}
                return render(request, 'financeiro/cobranca/marcar_paga.html', context)
            
            if not valor_pago:
                messages.error(request, 'Valor pago é obrigatório.')
                context = {'cobranca': cobranca, 'hoje': timezone.now().date()}
                return render(request, 'financeiro/cobranca/marcar_paga.html', context)
            
            # Converter dados - AGORA COM IMPORT CORRETO
            try:
                data_pagamento_obj = datetime.strptime(data_pagamento, '%Y-%m-%d').date()
                valor_pago_decimal = Decimal(str(valor_pago))
                print(f"✅ Conversões OK: data={data_pagamento_obj}, valor={valor_pago_decimal}")
            except (ValueError, TypeError) as e:
                print(f"❌ Erro na conversão: {e}")
                messages.error(request, f'Dados inválidos: {str(e)}')
                context = {'cobranca': cobranca, 'hoje': timezone.now().date()}
                return render(request, 'financeiro/cobranca/marcar_paga.html', context)
            
            # Verificar se valor é positivo
            if valor_pago_decimal <= 0:
                messages.error(request, 'Valor pago deve ser maior que zero.')
                context = {'cobranca': cobranca, 'hoje': timezone.now().date()}
                return render(request, 'financeiro/cobranca/marcar_paga.html', context)
            
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
            
            messages.success(request, f'Cobrança #{cobranca.id} marcada como paga com sucesso!')
            return redirect('financeiro:cobranca_detail', pk=pk)
            
        except Exception as e:
            print(f"❌ Erro inesperado: {e}")
            traceback.print_exc()
            messages.error(request, f'Erro inesperado: {str(e)}')
            context = {'cobranca': cobranca, 'hoje': timezone.now().date()}
            return render(request, 'financeiro/cobranca/marcar_paga.html', context)
    
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


def cobranca_gerar_lote(request):
    """
    View para gerar cobranças em lote (método tradicional)
    """
    from financeiro.services.cobranca.cobranca_criador_service import CobrancaCriadorService
    from ..forms.cobranca_forms import CobrancaLoteForm
    
    if request.method == 'POST':
        form = CobrancaLoteForm(request.POST)
        contratos_selecionados = request.POST.getlist('contratos')
        
        if form.is_valid() and contratos_selecionados:
            try:
                # Preparar dados para criação em lote
                dados_base = {
                    'mes_referencia': form.cleaned_data['mes_referencia'],
                    'ano_referencia': form.cleaned_data['ano_referencia'],
                    'data_vencimento': form.cleaned_data['data_vencimento'],
                    'incluir_despesas': form.cleaned_data['incluir_despesas_automatico'],
                    'gerar_descricao_automatica': form.cleaned_data['gerar_descricao_automatica'],
                }
                
                lista_dados = []
                for contrato_id in contratos_selecionados:
                    dados_cobranca = dados_base.copy()
                    dados_cobranca['contrato_id'] = int(contrato_id)
                    lista_dados.append(dados_cobranca)
                
                # Criar cobranças usando service
                resultado = CobrancaCriadorService.criar_cobrancas_lote(lista_dados)
                
                if resultado['success']:
                    messages.success(
                        request,
                        f'{resultado["cobrancas_criadas"]} cobranças criadas com sucesso!'
                    )
                    
                    if resultado['erros']:
                        messages.warning(
                            request,
                            f'Alguns erros ocorreram: {"; ".join(resultado["erros"][:3])}'
                        )
                else:
                    messages.error(
                        request,
                        f'Erro ao criar cobranças: {"; ".join(resultado["erros"][:3])}'
                    )
                    
            except Exception as e:
                messages.error(request, f'Erro inesperado: {str(e)}')
        else:
            messages.error(request, 'Dados inválidos ou nenhum contrato selecionado.')
    else:
        form = CobrancaLoteForm()
    
    # Buscar contratos ativos para o formulário
    try:
        from sisimob.models import Contrato
        contratos_ativos = Contrato.objects.select_related(
        'imovel',      # ForeignKey ✅
        'fiador'       # ForeignKey ✅
    ).prefetch_related(
        'inquilino',   # ManyToManyField ✅
        'proprietario' # ManyToManyField ✅
    ).filter(ativo=True)
    except ImportError:
        contratos_ativos = []
    
    context = {
        'form': form,
        'contratos_ativos': contratos_ativos,
    }
    
    return render(request, 'financeiro/cobranca/cobranca_gerar_lote.html', context)


@require_http_methods(["GET"])
def cobranca_api_despesas_contrato(request, contrato_id):
    """
    API para buscar despesas de um contrato (AJAX)
    """
    try:
        from sisimob.models import Contrato
        contrato = get_object_or_404(Contrato, pk=contrato_id)
        
        # Usar service para buscar despesas
        mes = int(request.GET.get('mes', date.today().month))
        ano = int(request.GET.get('ano', date.today().year))
        
        despesas = CobrancaCalculadoraService.buscar_despesas_periodo(contrato, mes, ano)
        valor_aluguel = CobrancaCalculadoraService.calcular_valor_aluguel(contrato, mes, ano)
        
        despesas_data = []
        for despesa in despesas:
            despesas_data.append({
                'id': despesa.pk,
                'tipo_nome': getattr(despesa.tipo, 'nome', 'Despesa') if hasattr(despesa, 'tipo') else 'Despesa',
                'descricao': getattr(despesa, 'descricao', '') or 'Sem descrição',
                'valor_parcela': float(despesa.calcular_valor_parcela()),
                'periodicidade': getattr(despesa, 'periodicidade', 'Mensal'),
                'ativa_em_data': True,  # Já filtrado pelo service
            })
        
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
@method_decorator(cache_page(60 * 5), name='dispatch')  # Cache por 5 minutos
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
        
        # Calcular estatísticas usando service
        stats = CobrancaEstatisticaService.calcular_estatisticas(filtros)
        
        # Converter Decimal para float para JSON
        for key, value in stats.items():
            if hasattr(value, 'quantize'):  # É um Decimal
                stats[key] = float(value)
        
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
        import json
        
        dados_webhook = json.loads(request.body)
        asaas_id = dados_webhook.get('payment', {}).get('id')
        
        if not asaas_id:
            return JsonResponse({'status': 'error', 'message': 'ID do pagamento não encontrado'})
        
        # Buscar integração
        try:
            asaas_integracao = AsaasIntegracao.objects.get(asaas_id=asaas_id)
        except AsaasIntegracao.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Cobrança não encontrada'})
        
        # Processar webhook usando service
        resultado = AsaasIntegracaoService.processar_webhook(asaas_integracao, dados_webhook)
        
        return JsonResponse(resultado)
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Erro ao processar webhook: {str(e)}'
        })


# === FUNÇÕES DE COMPATIBILIDADE ===
# Mantidas para compatibilidade com código existente

def gerar_cobrancas_manualmente(ids_contratos, mes, ano):
    """Função de compatibilidade - usar CobrancaCriadorService"""
    from ..services.cobranca_criador_service import CobrancaCriadorService
    
    dados_base = {
        'mes_referencia': int(mes),
        'ano_referencia': int(ano),
        'data_vencimento': date.today(),  # Ajustar conforme necessário
        'incluir_despesas': True,
        'gerar_descricao_automatica': True,
    }
    
    lista_dados = []
    for contrato_id in ids_contratos:
        dados_cobranca = dados_base.copy()
        dados_cobranca['contrato_id'] = contrato_id
        lista_dados.append(dados_cobranca)
    
    resultado = CobrancaCriadorService.criar_cobrancas_lote(lista_dados)
    return resultado['cobrancas_criadas']


def listar_cobrancas_ordenadas():
    """Função de compatibilidade"""
    return CobrancaConsultaService.filtrar_cobrancas({})


def marcar_cobranca_como_paga(cobranca_id, data_pagamento):
    """Função de compatibilidade"""
    cobranca = get_object_or_404(Cobranca, pk=cobranca_id)
    cobranca.marcar_como_paga(data_pagamento)
    return cobranca