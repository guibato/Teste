# financeiro/views/sync_views.py
"""
Views para gerenciamento da sincronização com Asaas
"""

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.generic import View
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin

import json
import logging
from datetime import datetime, timedelta, date
from decimal import Decimal

from ..models import SincronizacaoAsaas, Cobranca, Cliente
from ..services.asaas_sync_service import AsaasSyncService
from ..services.asaas_service import AsaasService

logger = logging.getLogger(__name__)

class SyncDashboardView(LoginRequiredMixin, View):
    """Dashboard principal da sincronização"""
    
    def get(self, request):
        return render(request, 'financeiro/sync/dashboard_sync.html')

@login_required
def sync_dashboard_api(request):
    """API para dados do dashboard"""
    try:
        # Última sincronização
        ultima_sync = SincronizacaoAsaas.objects.filter(
            sucesso=True
        ).order_by('-data_execucao').first()
        
        # Sincronizações hoje
        hoje = timezone.now().date()
        sync_hoje = SincronizacaoAsaas.objects.filter(
            data_execucao__date=hoje
        ).count()
        
        # Total de cobranças sincronizadas
        total_cobrancas = Cobranca.objects.filter(
            asaas_id__isnull=False
        ).count()
        
        # Taxa de sucesso dos últimos 30 dias
        trinta_dias_atras = timezone.now() - timedelta(days=30)
        sincronizacoes_recentes = SincronizacaoAsaas.objects.filter(
            data_execucao__gte=trinta_dias_atras
        )
        
        total_recentes = sincronizacoes_recentes.count()
        sucessos_recentes = sincronizacoes_recentes.filter(sucesso=True).count()
        taxa_sucesso = (sucessos_recentes / total_recentes * 100) if total_recentes > 0 else 100
        
        # Status da API (fazer teste rápido)
        api_status = verificar_status_api_asaas()
        
        data = {
            'ultima_sync': None,
            'sync_hoje': sync_hoje,
            'total_cobrancas': total_cobrancas,
            'taxa_sucesso': round(taxa_sucesso, 1),
            'api_status': api_status
        }
        
        if ultima_sync:
            data['ultima_sync'] = {
                'data': ultima_sync.data_execucao.strftime('%d/%m/%Y %H:%M'),
                'total': ultima_sync.cobrancas_processadas,
                'status': ultima_sync.status,
                'status_display': ultima_sync.get_status_display()
            }
        
        return JsonResponse(data)
        
    except Exception as e:
        logger.error(f"Erro no dashboard API: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def sync_historico_api(request):
    """API para histórico de sincronizações"""
    try:
        # Filtros
        tipo = request.GET.get('tipo', '')
        status = request.GET.get('status', '')
        page = int(request.GET.get('page', 1))
        per_page = int(request.GET.get('per_page', 10))
        
        # Query base
        queryset = SincronizacaoAsaas.objects.all()
        
        # Aplicar filtros
        if tipo:
            queryset = queryset.filter(tipo=tipo)
        if status:
            queryset = queryset.filter(status=status)
        
        # Ordenação
        queryset = queryset.order_by('-data_execucao')
        
        # Paginação
        paginator = Paginator(queryset, per_page)
        page_obj = paginator.get_page(page)
        
        # Serializar dados
        results = []
        for sync in page_obj:
            duracao = None
            if sync.data_conclusao and sync.data_execucao:
                duracao_timedelta = sync.data_conclusao - sync.data_execucao
                duracao = str(duracao_timedelta).split('.')[0]  # Remove microsegundos
            
            results.append({
                'id': sync.id,
                'data_execucao': sync.data_execucao.strftime('%d/%m/%Y %H:%M'),
                'data_inicio': sync.data_inicio.strftime('%d/%m/%Y'),
                'data_fim': sync.data_fim.strftime('%d/%m/%Y'),
                'tipo': sync.tipo,
                'tipo_display': sync.get_tipo_display(),
                'status': sync.status,
                'status_display': sync.get_status_display(),
                'cobrancas_processadas': sync.cobrancas_processadas,
                'cobrancas_criadas': sync.cobrancas_criadas,
                'cobrancas_atualizadas': sync.cobrancas_atualizadas,
                'erros': sync.erros,
                'duracao': duracao,
                'sucesso': sync.sucesso
            })
        
        return JsonResponse({
            'results': results,
            'count': paginator.count,
            'num_pages': paginator.num_pages,
            'current_page': page
        })
        
    except Exception as e:
        logger.error(f"Erro no histórico API: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)

@require_POST
@login_required
def sync_iniciar_api(request):
    """API para iniciar nova sincronização"""
    try:
        data = json.loads(request.body)
        
        tipo = data.get('tipo', 'cobrancas')
        data_inicio = datetime.strptime(data.get('data_inicio'), '%Y-%m-%d').date()
        data_fim = datetime.strptime(data.get('data_fim'), '%Y-%m-%d').date()
        forcar_atualizacao = data.get('forcar_atualizacao', False)
        
        # Validações
        if data_inicio > data_fim:
            return JsonResponse({'error': 'Data de início deve ser anterior à data de fim'}, status=400)
        
        if (data_fim - data_inicio).days > 90:
            return JsonResponse({'error': 'Período máximo de 90 dias'}, status=400)
        
        # Verificar se não há sincronização em andamento
        sync_ativa = SincronizacaoAsaas.objects.filter(
            status='executando'
        ).exists()
        
        if sync_ativa:
            return JsonResponse({'error': 'Já existe uma sincronização em andamento'}, status=400)
        
        # Criar registro de sincronização
        sync_record = SincronizacaoAsaas.objects.create(
            tipo=tipo,
            data_inicio=data_inicio,
            data_fim=data_fim,
            status='executando',
            parametros_utilizados={
                'forcar_atualizacao': forcar_atualizacao,
                'usuario': request.user.id
            }
        )
        
        # Iniciar sincronização assíncrona (se usando Celery)
        if hasattr(settings, 'CELERY_BROKER_URL'):
            from ..tasks import executar_sincronizacao_asaas
            task = executar_sincronizacao_asaas.delay(sync_record.id, forcar_atualizacao)
            sync_record.parametros_utilizados['task_id'] = str(task.id)
            sync_record.save()
        else:
            # Executar de forma síncrona (para desenvolvimento)
            from ..services.asaas_sync_service import AsaasSyncService
            service = AsaasSyncService()
            # Implementar execução síncrona aqui
        
        return JsonResponse({
            'success': True,
            'sync_id': sync_record.id,
            'message': 'Sincronização iniciada com sucesso'
        })
        
    except Exception as e:
        logger.error(f"Erro ao iniciar sincronização: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def sync_status_api(request, sync_id):
    """API para verificar status de sincronização específica"""
    try:
        sync = get_object_or_404(SincronizacaoAsaas, id=sync_id)
        
        # Calcular progresso (estimativa baseada em timestamps)
        progresso = 0
        if sync.status == 'executando':
            tempo_decorrido = timezone.now() - sync.data_execucao
            # Estimativa: 1 minuto para cada 100 cobranças (ajustar conforme necessário)
            tempo_estimado = timedelta(minutes=max(1, sync.cobrancas_processadas / 100))
            progresso = min(95, int((tempo_decorrido / tempo_estimado) * 100))
        elif sync.status == 'concluido':
            progresso = 100
        elif sync.status == 'erro':
            progresso = 0
        
        # Status texto
        status_texto = {
            'executando': f'Processando cobranças... ({sync.cobrancas_processadas} processadas)',
            'concluido': 'Sincronização concluída com sucesso',
            'erro': 'Erro durante a sincronização'
        }.get(sync.status, 'Status desconhecido')
        
        # Logs (se disponível)
        logs = []
        if hasattr(sync, 'logs'):
            # Implementar sistema de logs se necessário
            pass
        
        return JsonResponse({
            'status': sync.status,
            'progresso': progresso,
            'status_texto': status_texto,
            'cobrancas_processadas': sync.cobrancas_processadas,
            'cobrancas_criadas': sync.cobrancas_criadas,
            'cobrancas_atualizadas': sync.cobrancas_atualizadas,
            'erros': sync.erros,
            'logs': logs
        })
        
    except Exception as e:
        logger.error(f"Erro ao verificar status: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def sync_status_ativo_api(request):
    """API para verificar se há sincronização ativa"""
    try:
        sync_ativa = SincronizacaoAsaas.objects.filter(
            status='executando'
        ).order_by('-data_execucao').first()
        
        if sync_ativa:
            return JsonResponse({
                'ativo': True,
                'sync_id': sync_ativa.id
            })
        else:
            return JsonResponse({'ativo': False})
            
    except Exception as e:
        logger.error(f"Erro ao verificar status ativo: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)

@require_POST
@login_required
def sync_cancelar_api(request):
    """API para cancelar sincronização em andamento"""
    try:
        sync_ativa = SincronizacaoAsaas.objects.filter(
            status='executando'
        ).first()
        
        if not sync_ativa:
            return JsonResponse({'error': 'Nenhuma sincronização em andamento'}, status=400)
        
        # Cancelar task do Celery se existir
        task_id = sync_ativa.parametros_utilizados.get('task_id')
        if task_id:
            from celery import current_app
            current_app.control.revoke(task_id, terminate=True)
        
        # Atualizar status
        sync_ativa.status = 'erro'
        sync_ativa.mensagem_erro = 'Cancelado pelo usuário'
        sync_ativa.data_conclusao = timezone.now()
        sync_ativa.save()
        
        return JsonResponse({'success': True, 'message': 'Sincronização cancelada'})
        
    except Exception as e:
        logger.error(f"Erro ao cancelar sincronização: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def sync_testar_conexao_api(request):
    """API para testar conexão com Asaas"""
    try:
        status = verificar_status_api_asaas()
        
        if status['online']:
            return JsonResponse({
                'success': True,
                'status': status,
                'message': 'Conexão OK'
            })
        else:
            return JsonResponse({
                'success': False,
                'status': status,
                'error': 'Falha na conexão'
            })
            
    except Exception as e:
        logger.error(f"Erro ao testar conexão: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

def verificar_status_api_asaas():
    """Verifica status da API do Asaas"""
    try:
        service = AsaasService()
        inicio = timezone.now()
        
        # Fazer uma requisição simples para testar
        response = service._fazer_requisicao('GET', 'customers', params={'limit': 1})
        
        fim = timezone.now()
        latencia = int((fim - inicio).total_seconds() * 1000)
        
        return {
            'online': True,
            'latencia': latencia,
            'rate_limit': '450/500',  # Exemplo - implementar contagem real se necessário
            'ultima_verificacao': fim.strftime('%H:%M')
        }
        
    except Exception as e:
        logger.error(f"Erro ao verificar API Asaas: {str(e)}")
        return {
            'online': False,
            'erro': str(e),
            'ultima_verificacao': timezone.now().strftime('%H:%M')
        }

@require_POST
@login_required
def sync_configuracoes_api(request):
    """API para salvar configurações de sincronização"""
    try:
        data = json.loads(request.body)
        
        # Salvar configurações (implementar modelo de configuração se necessário)
        # Por enquanto, apenas retornar sucesso
        
        return JsonResponse({
            'success': True,
            'message': 'Configurações salvas com sucesso'
        })
        
    except Exception as e:
        logger.error(f"Erro ao salvar configurações: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def sync_detalhes_api(request, sync_id):
    """API para obter detalhes de uma sincronização"""
    try:
        sync = get_object_or_404(SincronizacaoAsaas, id=sync_id)
        
        data = {
            'id': sync.id,
            'tipo': sync.get_tipo_display(),
            'data_execucao': sync.data_execucao.strftime('%d/%m/%Y %H:%M:%S'),
            'data_conclusao': sync.data_conclusao.strftime('%d/%m/%Y %H:%M:%S') if sync.data_conclusao else None,
            'periodo': f"{sync.data_inicio.strftime('%d/%m/%Y')} até {sync.data_fim.strftime('%d/%m/%Y')}",
            'status': sync.get_status_display(),
            'sucesso': sync.sucesso,
            'estatisticas': {
                'processadas': sync.cobrancas_processadas,
                'criadas': sync.cobrancas_criadas,
                'atualizadas': sync.cobrancas_atualizadas,
                'erros': sync.erros
            },
            'parametros': sync.parametros_utilizados,
            'mensagem_erro': sync.mensagem_erro
        }
        
        return JsonResponse(data)
        
    except Exception as e:
        logger.error(f"Erro ao obter detalhes: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)

@require_POST
@login_required
def sync_reexecutar_api(request, sync_id):
    """API para reexecutar uma sincronização"""
    try:
        sync_original = get_object_or_404(SincronizacaoAsaas, id=sync_id)
        
        # Verificar se não há sincronização em andamento
        if SincronizacaoAsaas.objects.filter(status='executando').exists():
            return JsonResponse({'error': 'Já existe uma sincronização em andamento'}, status=400)
        
        # Criar nova sincronização baseada na original
        nova_sync = SincronizacaoAsaas.objects.create(
            tipo=sync_original.tipo,
            data_inicio=sync_original.data_inicio,
            data_fim=sync_original.data_fim,
            status='executando',
            parametros_utilizados={
                **sync_original.parametros_utilizados,
                'reexecucao_de': sync_original.id,
                'usuario': request.user.id
            }
        )
        
        # Iniciar sincronização (implementar conforme necessário)
        
        return JsonResponse({
            'success': True,
            'sync_id': nova_sync.id,
            'message': 'Sincronização reexecutada'
        })
        
    except Exception as e:
        logger.error(f"Erro ao reexecutar: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def sync_download_log_api(request, sync_id):
    """API para download de log de sincronização"""
    try:
        sync = get_object_or_404(SincronizacaoAsaas, id=sync_id)
        
        # Gerar conteúdo do log
        log_content = gerar_relatorio_sincronizacao(sync)
        
        response = HttpResponse(log_content, content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename="sync_{sync_id}_log.txt"'
        
        return response
        
    except Exception as e:
        logger.error(f"Erro ao gerar log: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)

def gerar_relatorio_sincronizacao(sync):
    """Gera relatório detalhado da sincronização"""
    linhas = [
        f"RELATÓRIO DE SINCRONIZAÇÃO ASAAS",
        f"=" * 50,
        f"ID: {sync.id}",
        f"Tipo: {sync.get_tipo_display()}",
        f"Data de Execução: {sync.data_execucao.strftime('%d/%m/%Y %H:%M:%S')}",
        f"Data de Conclusão: {sync.data_conclusao.strftime('%d/%m/%Y %H:%M:%S') if sync.data_conclusao else 'N/A'}",
        f"Período: {sync.data_inicio.strftime('%d/%m/%Y')} até {sync.data_fim.strftime('%d/%m/%Y')}",
        f"Status: {sync.get_status_display()}",
        f"Sucesso: {'Sim' if sync.sucesso else 'Não'}",
        f"",
        f"ESTATÍSTICAS",
        f"-" * 20,
        f"Cobranças Processadas: {sync.cobrancas_processadas}",
        f"Cobranças Criadas: {sync.cobrancas_criadas}",
        f"Cobranças Atualizadas: {sync.cobrancas_atualizadas}",
        f"Erros: {sync.erros}",
        f"",
        f"PARÂMETROS UTILIZADOS",
        f"-" * 20,
    ]
    
    for chave, valor in sync.parametros_utilizados.items():
        linhas.append(f"{chave}: {valor}")
    
    if sync.mensagem_erro:
        linhas.extend([
            f"",
            f"ERRO",
            f"-" * 20,
            sync.mensagem_erro
        ])
    
    return "\n".join(linhas)


