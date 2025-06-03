# financeiro/views/cobranca_views.py
"""
Views para gerenciamento de Cobranças
====================================
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.views.generic import ListView, CreateView, UpdateView, DetailView
from django.urls import reverse_lazy
from django.db.models import Q, Sum, Count
from django.http import JsonResponse
from datetime import date, timedelta
from decimal import Decimal

from ..models import Cobranca, Despesa
from ..forms.cobranca_forms import CobrancaForm, CobrancaIntegracaoAsaasForm


class CobrancaListView(ListView):
    """
    View para listagem de cobranças com filtros e paginação
    """
    model = Cobranca
    template_name = 'financeiro/cobranca/cobranca_list.html'
    context_object_name = 'cobrancas'
    paginate_by = 20
    
    def get_queryset(self):
        """Aplica filtros na queryset baseado nos parâmetros GET"""
        queryset = Cobranca.objects.select_related('contrato', 'inquilino').all()
        
        # Filtro por status
        status = self.request.GET.get('status', 'pendente')
        if status == 'pendente':
            queryset = queryset.filter(status='pendente')
        elif status == 'paga':
            queryset = queryset.filter(status='paga')
        elif status == 'atrasada':
            queryset = queryset.filter(status='atrasada')
        elif status == 'cancelada':
            queryset = queryset.filter(status='cancelada')
        
        # Filtro por mês de referência
        mes_referencia = self.request.GET.get('mes_referencia')
        if mes_referencia:
            try:
                queryset = queryset.filter(mes_referencia=int(mes_referencia))
            except ValueError:
                pass
        
        # Filtro por ano de referência
        ano_referencia = self.request.GET.get('ano_referencia')
        if ano_referencia:
            try:
                queryset = queryset.filter(ano_referencia=int(ano_referencia))
            except ValueError:
                pass
        
        # Filtro por contrato
        contrato_busca = self.request.GET.get('contrato', '').strip()
        if contrato_busca:
            queryset = queryset.filter(
                Q(contrato__numero_contrato__icontains=contrato_busca) |
                Q(contrato__imovel__endereco__icontains=contrato_busca)
            )
        
        # Filtro por inquilino
        inquilino_busca = self.request.GET.get('inquilino', '').strip()
        if inquilino_busca:
            queryset = queryset.filter(
                Q(inquilino__nome__icontains=inquilino_busca) |
                Q(inquilino__email__icontains=inquilino_busca)
            )
        
        return queryset.order_by('-ano_referencia', '-mes_referencia', '-data_vencimento')
    
    def get_context_data(self, **kwargs):
        """Adiciona dados extras ao contexto do template"""
        context = super().get_context_data(**kwargs)
        
        # Mantém os filtros no contexto
        context['filtro_status'] = self.request.GET.get('status', 'pendente')
        context['filtro_mes'] = self.request.GET.get('mes_referencia', '')
        context['filtro_ano'] = self.request.GET.get('ano_referencia', '')
        context['filtro_contrato'] = self.request.GET.get('contrato', '')
        context['filtro_inquilino'] = self.request.GET.get('inquilino', '')
        
        # Estatísticas gerais
        context['total_cobrancas'] = Cobranca.objects.count()
        context['cobrancas_pendentes'] = Cobranca.objects.filter(status='pendente').count()
        context['cobrancas_pagas'] = Cobranca.objects.filter(status='paga').count()
        context['cobrancas_atrasadas'] = Cobranca.objects.filter(status='atrasada').count()
        
        # Valores financeiros
        valores = Cobranca.objects.aggregate(
            total_pendente=Sum('valor_total', filter=Q(status='pendente')),
            total_pago=Sum('valor_total', filter=Q(status='paga')),
            total_atrasado=Sum('valor_total', filter=Q(status='atrasada'))
        )
        context.update({
            'valor_total_pendente': valores['total_pendente'] or Decimal('0.00'),
            'valor_total_pago': valores['total_pago'] or Decimal('0.00'),
            'valor_total_atrasado': valores['total_atrasado'] or Decimal('0.00'),
        })
        
        return context


class CobrancaCreateView(CreateView):
    """
    View para criação de novas cobranças
    """
    model = Cobranca
    form_class = CobrancaForm
    template_name = 'financeiro/cobranca/cobranca_form.html'
    success_url = reverse_lazy('financeiro:cobranca_list')
    
    def form_valid(self, form):
        """Processa o formulário válido e calcula valores automaticamente"""
        # Calcular valores antes de salvar
        cobranca = form.save(commit=False)
        
        # Atualizar valor total baseado nas despesas
        cobranca.valor_total = cobranca.calcular_valor_total()
        
        # Gerar descrição automática se solicitado
        if form.cleaned_data.get('gerar_descricao_automatica', True):
            cobranca.descricao = cobranca.gerar_descricao_automatica()
        
        # Salvar a cobrança
        cobranca.save()
        
        # Mensagem de sucesso
        messages.success(
            self.request,
            f'Cobrança {cobranca.mes_referencia}/{cobranca.ano_referencia} '
            f'criada com sucesso! Valor: R$ {cobranca.valor_total:,.2f}'
        )
        
        return redirect(self.success_url)
    
    def form_invalid(self, form):
        """Adiciona mensagem de erro quando o formulário é inválido"""
        messages.error(
            self.request,
            'Erro ao criar cobrança. Verifique os dados informados.'
        )
        return super().form_invalid(form)
    
    def get_context_data(self, **kwargs):
        """Adiciona título da página ao contexto"""
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nova Cobrança'
        context['botao_submit'] = 'Criar Cobrança'
        
        # Contratos disponíveis para pré-popular
        try:
            from sisimob.models import Contrato
            context['contratos_ativos'] = Contrato.objects.filter(ativo=True)[:10]
        except ImportError:
            context['contratos_ativos'] = []
        
        return context


class CobrancaUpdateView(UpdateView):
    """
    View para edição de cobranças existentes
    """
    model = Cobranca
    form_class = CobrancaForm
    template_name = 'financeiro/cobranca/cobranca_form.html'
    success_url = reverse_lazy('financeiro:cobranca_list')
    
    def form_valid(self, form):
        """Processa o formulário válido e recalcula valores"""
        cobranca = form.save(commit=False)
        
        # Recalcular valor total
        cobranca.valor_total = cobranca.calcular_valor_total()
        
        # Atualizar descrição se solicitado
        if form.cleaned_data.get('gerar_descricao_automatica', False):
            cobranca.descricao = cobranca.gerar_descricao_automatica()
        
        cobranca.save()
        
        messages.success(
            self.request,
            f'Cobrança {cobranca.mes_referencia}/{cobranca.ano_referencia} atualizada com sucesso!'
        )
        
        return redirect(self.success_url)
    
    def form_invalid(self, form):
        """Adiciona mensagem de erro quando o formulário é inválido"""
        messages.error(
            self.request,
            'Erro ao atualizar cobrança. Verifique os dados informados.'
        )
        return super().form_invalid(form)
    
    def get_context_data(self, **kwargs):
        """Adiciona título da página ao contexto"""
        context = super().get_context_data(**kwargs)
        context['titulo'] = f'Editar Cobrança - {self.object.mes_referencia}/{self.object.ano_referencia}'
        context['botao_submit'] = 'Salvar Alterações'
        
        # Verificar se cobrança já foi integrada com Asaas
        context['ja_integrada'] = bool(self.object.asaas_id)
        
        return context


class CobrancaDetailView(DetailView):
    """
    View para visualização detalhada de uma cobrança
    """
    model = Cobranca
    template_name = 'financeiro/cobranca/cobranca_detail.html'
    context_object_name = 'cobranca'
    
    def get_context_data(self, **kwargs):
        """Adiciona informações detalhadas ao contexto"""
        context = super().get_context_data(**kwargs)
        
        # Detalhes financeiros
        context['detalhes_financeiros'] = self.object.get_detalhes_financeiros()
        
        # Status da cobrança
        context['esta_atrasada'] = self.object.esta_atrasada
        context['dias_atraso'] = self.object.dias_atraso
        context['esta_quitada'] = self.object.is_quitada()
        
        # Informações de integração Asaas
        context['tem_integracao_asaas'] = bool(self.object.asaas_id)
        context['pode_integrar_asaas'] = self.object.pode_ser_integrada()[0]
        
        # Despesas relacionadas
        context['despesas_incluidas'] = self.object.get_despesas_cobranca()
        
        return context


def cobranca_integrar_asaas(request, pk):
    """
    View para integrar cobrança com o Asaas
    """
    cobranca = get_object_or_404(Cobranca, pk=pk)
    
    # Verificar se pode ser integrada
    pode_integrar, erros = cobranca.pode_ser_integrada()
    
    if not pode_integrar:
        messages.error(request, f'Não é possível integrar: {", ".join(erros)}')
        return redirect('financeiro:cobranca_detail', pk=pk)
    
    if request.method == 'POST':
        form = CobrancaIntegracaoAsaasForm(request.POST)
        
        if form.is_valid():
            try:
                # Integrar com Asaas
                resultado = cobranca.gerar_cobranca_gateway()
                
                if resultado['status'] == 'success':
                    messages.success(
                        request,
                        'Cobrança integrada com Asaas com sucesso! '
                        'Boleto e PIX foram gerados automaticamente.'
                    )
                else:
                    messages.error(
                        request,
                        f'Erro na integração: {", ".join(resultado.get("erros", ["Erro desconhecido"]))}'
                    )
                    
            except Exception as e:
                messages.error(request, f'Erro inesperado: {str(e)}')
                
            return redirect('financeiro:cobranca_detail', pk=pk)
    else:
        form = CobrancaIntegracaoAsaasForm()
    
    context = {
        'cobranca': cobranca,
        'form': form,
        'titulo': f'Integrar com Asaas - {cobranca.mes_referencia}/{cobranca.ano_referencia}'
    }
    
    return render(request, 'financeiro/cobranca/cobranca_integrar_asaas.html', context)


def cobranca_marcar_paga(request, pk):
    """
    View para marcar cobrança como paga
    """
    cobranca = get_object_or_404(Cobranca, pk=pk)
    
    if cobranca.status == 'paga':
        messages.warning(request, 'Esta cobrança já está marcada como paga.')
        return redirect('financeiro:cobranca_detail', pk=pk)
    
    if request.method == 'POST':
        data_pagamento = request.POST.get('data_pagamento')
        
        try:
            if data_pagamento:
                from datetime import datetime
                data_pagamento = datetime.strptime(data_pagamento, '%Y-%m-%d').date()
            else:
                data_pagamento = date.today()
            
            # Marcar como paga
            cobranca.marcar_como_paga(data_pagamento)
            
            messages.success(
                request,
                f'Cobrança marcada como paga! '
                f'Repasse automático criado para o proprietário.'
            )
            
        except Exception as e:
            messages.error(request, f'Erro ao marcar como paga: {str(e)}')
    
    return redirect('financeiro:cobranca_detail', pk=pk)


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
    
    # Cancelar cobrança
    cobranca.status = 'cancelada'
    cobranca.save()
    
    messages.success(request, 'Cobrança cancelada com sucesso!')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': 'Cobrança cancelada'})
    
    return redirect('financeiro:cobranca_list')


def cobranca_gerar_lote(request):
    """
    View para gerar cobranças em lote
    """
    if request.method == 'POST':
        mes_referencia = request.POST.get('mes_referencia')
        ano_referencia = request.POST.get('ano_referencia')
        data_vencimento = request.POST.get('data_vencimento')
        contratos_selecionados = request.POST.getlist('contratos')
        
        try:
            mes_referencia = int(mes_referencia)
            ano_referencia = int(ano_referencia)
            data_vencimento = date.fromisoformat(data_vencimento)
            
            cobrancas_criadas = 0
            erros = []
            
            # Importar modelo de contrato
            try:
                from sisimob.models import Contrato
                
                contratos = Contrato.objects.filter(
                    id__in=contratos_selecionados,
                    ativo=True
                )
                
                for contrato in contratos:
                    # Verificar se já existe cobrança
                    if Cobranca.objects.filter(
                        contrato=contrato,
                        mes_referencia=mes_referencia,
                        ano_referencia=ano_referencia
                    ).exists():
                        erros.append(f'Cobrança já existe para {contrato}')
                        continue
                    
                    try:
                        # Criar cobrança
                        cobranca = Cobranca.objects.create(
                            contrato=contrato,
                            inquilino=contrato.inquilino,
                            mes_referencia=mes_referencia,
                            ano_referencia=ano_referencia,
                            valor_aluguel=contrato.valor_aluguel or Decimal('0.00'),
                            data_vencimento=data_vencimento,
                            status='pendente'
                        )
                        
                        # Calcular valor total incluindo despesas
                        cobranca.atualizar_valor_total()
                        
                        # Gerar descrição automática
                        cobranca.descricao = cobranca.gerar_descricao_automatica()
                        cobranca.save()
                        
                        cobrancas_criadas += 1
                        
                    except Exception as e:
                        erros.append(f'Erro ao criar cobrança para {contrato}: {str(e)}')
                
                # Mensagens de resultado
                if cobrancas_criadas > 0:
                    messages.success(
                        request,
                        f'{cobrancas_criadas} cobranças criadas com sucesso!'
                    )
                
                if erros:
                    messages.warning(
                        request,
                        f'Alguns erros ocorreram: {"; ".join(erros[:5])}'
                    )
                    
            except ImportError:
                messages.error(request, 'Erro ao importar modelo de Contrato')
                
        except (ValueError, TypeError) as e:
            messages.error(request, f'Dados inválidos: {str(e)}')
    
    # Buscar contratos ativos para o formulário
    try:
        from sisimob.models import Contrato
        contratos_ativos = Contrato.objects.filter(ativo=True).order_by('numero_contrato')
    except ImportError:
        contratos_ativos = []
    
    context = {
        'contratos_ativos': contratos_ativos,
        'mes_atual': date.today().month,
        'ano_atual': date.today().year,
    }
    
    return render(request, 'financeiro/cobranca/cobranca_gerar_lote.html', context)


def cobranca_api_despesas_contrato(request, contrato_id):
    """
    API para buscar despesas de um contrato (AJAX)
    """
    try:
        from sisimob.models import Contrato
        contrato = get_object_or_404(Contrato, pk=contrato_id)
        
        # Buscar despesas ativas pagas pelo inquilino
        despesas = Despesa.objects.filter(
            contrato=contrato,
            is_ativa=True,
            paga_por='inquilino'
        ).order_by('tipo__nome')
        
        despesas_data = []
        for despesa in despesas:
            despesas_data.append({
                'id': despesa.pk,
                'tipo_nome': despesa.tipo.nome,
                'descricao': despesa.descricao or despesa.get_descricao_padrao(),
                'valor_parcela': float(despesa.calcular_valor_parcela()),
                'periodicidade': despesa.get_periodicidade_display(),
                'ativa_em_data': despesa.parcela_ativa_em_data()
            })
        
        return JsonResponse({
            'success': True,
            'despesas': despesas_data,
            'valor_aluguel': float(contrato.valor_aluguel or 0),
            'inquilino_nome': contrato.inquilino.nome if contrato.inquilino else ''
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })