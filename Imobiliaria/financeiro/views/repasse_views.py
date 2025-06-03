# financeiro/views/repasse_views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.db.models import Q, Sum, Count, Case, When, DecimalField, F
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.core.paginator import Paginator
from django.urls import reverse_lazy
from datetime import date, datetime, timedelta
from decimal import Decimal
import json

from ..models.repasse import Repasse, PoliticaRepasse, AgendamentoRepasse
from ..models.cobranca import Cobranca
from ..services.repasse_service import RepasseService
from ..forms.repasse_forms import RepasseForm, PoliticaRepasseForm, ProcessarRepasseForm


class RepasseListView(ListView):
    model = Repasse
    template_name = 'financeiro/repasses/lista_repasses.html'
    context_object_name = 'repasses'
    paginate_by = 20

    def get_queryset(self):
        queryset = Repasse.objects.select_related(
            'proprietario', 'contrato', 'cobranca'
        ).prefetch_related('contrato__imovel')

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
        
        # Estatísticas para cards - usando F() expressions para calcular valor_liquido
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


class RepasseDetailView(DetailView):
    model = Repasse
    template_name = 'financeiro/repasses/detalhe_repasse.html'
    context_object_name = 'repasse'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        repasse = self.get_object()
        
        # Histórico de movimentações relacionadas
        from ..models.movimento import MovimentoConta
        context['movimentos'] = MovimentoConta.objects.filter(
            proprietario=repasse.proprietario,
            contrato=repasse.contrato,
            data_referencia__year=repasse.ano_referencia,
            data_referencia__month=repasse.mes_referencia
        ).order_by('-data_criacao')
        
        return context



def processar_repasse_view(request, repasse_id):
    repasse = get_object_or_404(Repasse, id=repasse_id)
    
    if request.method == 'POST':
        form = ProcessarRepasseForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                success = repasse.efetivar_repasse(
                    metodo_pagamento=form.cleaned_data['metodo_pagamento'],
                    observacoes=form.cleaned_data['observacoes']
                )
                
                if success:
                    # Upload do comprovante se fornecido
                    if form.cleaned_data.get('comprovante'):
                        repasse.comprovante = form.cleaned_data['comprovante']
                        repasse.save(update_fields=['comprovante'])
                    
                    messages.success(request, f'Repasse efetuado com sucesso!')
                    
                    # Enviar notificação (implementar com Celery depois)
                    # send_repasse_notification.delay(repasse.id)
                    
                    return redirect('financeiro:repasse_detail', pk=repasse.id)
                else:
                    messages.error(request, 'Não foi possível efetivar o repasse.')
            except Exception as e:
                messages.error(request, f'Erro ao processar repasse: {str(e)}')
    else:
        form = ProcessarRepasseForm()

    return render(request, 'financeiro/repasses/processar_repasse.html', {
        'repasse': repasse,
        'form': form
    })



def cancelar_repasse_view(request, repasse_id):
    repasse = get_object_or_404(Repasse, id=repasse_id)
    
    if request.method == 'POST':
        motivo = request.POST.get('motivo', '')
        success = repasse.cancelar_repasse(motivo)
        
        if success:
            messages.success(request, 'Repasse cancelado com sucesso!')
        else:
            messages.error(request, 'Não foi possível cancelar o repasse.')
    
    return redirect('financeiro:repasse_detail', pk=repasse.id)


class PoliticaRepasseListView(ListView):
    model = PoliticaRepasse
    template_name = 'financeiro/repasses/configurar_politicas.html'
    context_object_name = 'politicas'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = PoliticaRepasseForm()
        return context


class PoliticaRepasseCreateView(CreateView):
    model = PoliticaRepasse
    form_class = PoliticaRepasseForm
    template_name = 'financeiro/repasses/politica_form.html'
    
    def form_valid(self, form):
        messages.success(self.request, 'Política de repasse criada com sucesso!')
        return super().form_valid(form)


class PoliticaRepasseUpdateView(UpdateView):
    model = PoliticaRepasse
    form_class = PoliticaRepasseForm
    template_name = 'financeiro/repasses/politica_form.html'
    
    def form_valid(self, form):
        messages.success(self.request, 'Política de repasse atualizada com sucesso!')
        return super().form_valid(form)



def extrato_proprietario_view(request, proprietario_id):
    from sisimob.models import Cliente
    proprietario = get_object_or_404(Cliente, id=proprietario_id)
    
    # Filtros de data
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    
    if not data_inicio:
        data_inicio = date.today() - timedelta(days=90)
    else:
        data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
    
    if not data_fim:
        data_fim = date.today()
    else:
        data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()

    # Buscar repasses no período
    repasses = Repasse.objects.filter(
        proprietario=proprietario,
        data_criacao__date__range=[data_inicio, data_fim]
    ).select_related('contrato', 'cobranca').order_by('-data_criacao')

    # Buscar movimentações
    from ..models.movimento import MovimentoConta
    movimentos = MovimentoConta.objects.filter(
        proprietario=proprietario,
        data_referencia__range=[data_inicio, data_fim]
    ).order_by('-data_referencia')

    # Estatísticas do período
    stats = repasses.aggregate(
        total_recebido=Sum(
            Case(
                When(status='efetuado', then=F('valor') - F('valor_desconto') - F('valor_taxa_admin')),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            )
        ),
        total_pendente=Sum(
            Case(
                When(status='pendente', then=F('valor') - F('valor_desconto') - F('valor_taxa_admin')),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            )
        ),
        quantidade_repasses=Count('id')
    )

    # Saldo atual (implementar SaldoProprietario depois)
    saldo_atual = Decimal('0.00')

    return render(request, 'financeiro/repasses/extrato_proprietario.html', {
        'proprietario': proprietario,
        'repasses': repasses,
        'movimentos': movimentos,
        'stats': stats,
        'saldo_atual': saldo_atual,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
    })



def dashboard_repasses_ajax(request):
    """View para dados do dashboard via AJAX"""
    
    # Dados para gráficos
    hoje = date.today()
    inicio_mes = hoje.replace(day=1)
    
    # Repasses por status
    status_data = Repasse.objects.filter(
        data_criacao__date__gte=inicio_mes
    ).values('status').annotate(
        total=Sum(F('valor') - F('valor_desconto') - F('valor_taxa_admin')),
        count=Count('id')
    )
    
    # Repasses por mês (últimos 6 meses)
    repasses_mensais = []
    for i in range(6):
        mes_atual = hoje.replace(day=1) - timedelta(days=i*30)
        mes_data = Repasse.objects.filter(
            ano_referencia=mes_atual.year,
            mes_referencia=mes_atual.month,
            status='efetuado'
        ).aggregate(
            total=Sum(F('valor') - F('valor_desconto') - F('valor_taxa_admin'))
        )
        
        repasses_mensais.append({
            'mes': f"{mes_atual.month}/{mes_atual.year}",
            'total': float(mes_data['total'] or 0)
        })
    
    # Próximos repasses (7 dias)
    proximos = Repasse.objects.filter(
        status='pendente',
        data_prevista__lte=hoje + timedelta(days=7)
    ).select_related('proprietario').order_by('data_prevista')[:10]
    
    return JsonResponse({
        'status_data': list(status_data),
        'repasses_mensais': repasses_mensais[::-1],  # Ordem cronológica
        'proximos_repasses': [{
            'id': r.id,
            'proprietario': r.proprietario.nome,
            'valor': float(r.valor_liquido),  # Usando a propriedade do modelo
            'data_prevista': r.data_prevista.strftime('%d/%m/%Y'),
            'dias_restantes': (r.data_prevista - hoje).days
        } for r in proximos]
    })


class RepasseCreateView(CreateView):
    model = Repasse
    form_class = RepasseForm
    template_name = 'financeiro/repasses/repasse_form.html'
    
    def get_success_url(self):
        return reverse_lazy('financeiro:repasse_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, 'Repasse criado com sucesso!')
        return super().form_valid(form)


class RepasseUpdateView(UpdateView):
    model = Repasse
    form_class = RepasseForm
    template_name = 'financeiro/repasses/repasse_form.html'
    
    def get_success_url(self):
        return reverse_lazy('financeiro:repasse_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, 'Repasse atualizado com sucesso!')
        return super().form_valid(form)


class AgendamentoListView(ListView):
    model = AgendamentoRepasse
    template_name = 'financeiro/repasses/agendamento_list.html'
    context_object_name = 'agendamentos'
    paginate_by = 20

    def get_queryset(self):
        return AgendamentoRepasse.objects.select_related(
            'proprietario', 'contrato', 'politica'
        ).order_by('-data_agendada')



def processar_agendamento_view(request, pk):
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
            messages.error(request, f'Erro: {str(e)}')
    
    return redirect('financeiro:agendamento_list')



def gerar_repasse_automatico(request):
    """Gerar repasses baseados nas políticas ativas"""
    if request.method == 'POST':
        try:
            service = RepasseService()
            resultado = service.processar_repasses_automaticos()
            
            messages.success(request, 
                f"Processamento concluído: {resultado['criados']} repasses criados, "
                f"{resultado['erros']} erros.")
            
        except Exception as e:
            messages.error(request, f"Erro no processamento: {str(e)}")
    
    return redirect('financeiro:repasse_list')



def dashboard_financeiro_view(request):
    """View principal do dashboard financeiro"""
    return render(request, 'financeiro/dashboard_financeiro.html')



def exportar_relatorio_repasses(request):
    """Exporta relatório de repasses em Excel"""
    try:
        import openpyxl
        from django.http import HttpResponse
        from openpyxl.styles import Font, PatternFill
        from datetime import datetime
        
        # Parâmetros de filtro
        periodo = int(request.GET.get('periodo', 30))
        formato = request.GET.get('formato', 'excel')
        
        # Buscar dados
        data_inicio = date.today() - timedelta(days=periodo)
        repasses = Repasse.objects.filter(
            data_criacao__date__gte=data_inicio
        ).select_related('proprietario', 'contrato').order_by('-data_criacao')
        
        if formato == 'excel':
            # Criar workbook
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Relatório de Repasses"
            
            # Cabeçalhos
            headers = [
                'ID', 'Proprietário', 'Imóvel', 'Valor Bruto', 'Descontos', 
                'Taxa Admin', 'Valor Líquido', 'Status', 'Data Prevista', 
                'Data Efetivação', 'Método Pagamento', 'Mês/Ano Ref'
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
                ws.cell(row=row, column=2, value=repasse.proprietario.nome)
                ws.cell(row=row, column=3, value=str(repasse.contrato.imovel))
                ws.cell(row=row, column=4, value=float(repasse.valor))
                ws.cell(row=row, column=5, value=float(repasse.valor_desconto))
                ws.cell(row=row, column=6, value=float(repasse.valor_taxa_admin))
                ws.cell(row=row, column=7, value=float(repasse.valor_liquido))
                ws.cell(row=row, column=8, value=repasse.get_status_display())
                ws.cell(row=row, column=9, value=repasse.data_prevista)
                ws.cell(row=row, column=10, value=repasse.data_efetivacao)
                ws.cell(row=row, column=11, value=repasse.get_metodo_pagamento_display() if repasse.metodo_pagamento else '')
                ws.cell(row=row, column=12, value=f"{repasse.mes_referencia:02d}/{repasse.ano_referencia}")
            
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
        return redirect('financeiro:repasse_list')
    except Exception as e:
        messages.error(request, f'Erro ao gerar relatório: {str(e)}')
        return redirect('financeiro:repasse_list')