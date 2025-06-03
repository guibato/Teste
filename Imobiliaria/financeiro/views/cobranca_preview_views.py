# financeiro/views/cobranca_preview_views.py
"""
Views para o fluxo de preview/revisão de cobranças
===============================================
"""

from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from datetime import date, timedelta
from decimal import Decimal
import json

from ..models import Cobranca, Despesa
from ..forms.cobranca_forms import CobrancaIntegracaoAsaasForm


def cobranca_preview_geracao(request):
    """
    Tela de preview para gerar cobranças - mostra o que seria gerado sem salvar
    """
    # Valores padrão
    hoje = date.today()
    mes_atual = hoje.month
    ano_atual = hoje.year
    
    # Próximo vencimento padrão (dia 10 do próximo mês)
    if hoje.month == 12:
        data_vencimento_padrao = date(hoje.year + 1, 1, 10)
    else:
        data_vencimento_padrao = date(hoje.year, hoje.month + 1, 10)
    
    context = {
        'mes_atual': mes_atual,
        'ano_atual': ano_atual,
        'data_vencimento_padrao': data_vencimento_padrao.isoformat(),
        'meses': [
            (1, 'Janeiro'), (2, 'Fevereiro'), (3, 'Março'), (4, 'Abril'),
            (5, 'Maio'), (6, 'Junho'), (7, 'Julho'), (8, 'Agosto'),
            (9, 'Setembro'), (10, 'Outubro'), (11, 'Novembro'), (12, 'Dezembro')
        ]
    }
    
    # Buscar contratos ativos para o formulário
    try:
        from sisimob.models import Contrato
        context['contratos_ativos'] = Contrato.objects.filter(ativo=True).order_by('tipo_contrato')
    except ImportError:
        context['contratos_ativos'] = []
    
    return render(request, 'financeiro/cobranca/cobranca_preview_geracao.html', context)


def cobranca_api_preview(request):
    """
    API para buscar preview das cobranças que seriam geradas
    """
    print("=== INÍCIO DEBUG API PREVIEW ===")
    
    if request.method != 'POST':
        print("❌ Método não é POST")
        return JsonResponse({'success': False, 'error': 'Método não permitido'})
    
    try:
        print("📨 Lendo dados do request...")
        data = json.loads(request.body)
        print(f"📊 Dados recebidos: {data}")
        
        mes_referencia = int(data.get('mes_referencia'))
        ano_referencia = int(data.get('ano_referencia'))
        data_vencimento = data.get('data_vencimento')
        contratos_ids = data.get('contratos', [])
        incluir_despesas = data.get('incluir_despesas', True)
        
        print(f"🗓️ Período: {mes_referencia}/{ano_referencia}")
        print(f"📅 Vencimento: {data_vencimento}")
        print(f"📋 Contratos IDs: {contratos_ids}")
        print(f"💰 Incluir despesas: {incluir_despesas}")
        
        # Validar dados
        if not (1 <= mes_referencia <= 12):
            print("❌ Mês inválido")
            return JsonResponse({'success': False, 'error': 'Mês inválido'})
        
        if not (2020 <= ano_referencia <= 2030):
            print("❌ Ano inválido")
            return JsonResponse({'success': False, 'error': 'Ano inválido'})
        
        # Buscar contratos
        try:
            from sisimob.models import Contrato
            print("🔍 Importando modelo Contrato...")
            
            if contratos_ids:
                print(f"📝 Filtrando por IDs: {contratos_ids}")
                contratos = Contrato.objects.filter(
                    id__in=contratos_ids,
                    ativo=True
                )
            else:
                print("📝 Buscando todos os contratos ativos...")
                contratos = Contrato.objects.filter(ativo=True)
            
            print(f"📊 Encontrados {contratos.count()} contratos")
            
            if contratos.count() == 0:
                print("⚠️ Nenhum contrato encontrado!")
                return JsonResponse({
                    'success': True,
                    'cobrancas': [],
                    'total_cobrancas': 0,
                    'valor_total_geral': 0,
                    'mes_nome': 'Teste',
                    'ano': ano_referencia
                })
            
            preview_cobrancas = []
            total_geral = Decimal('0.00')
            
            for i, contrato in enumerate(contratos[:5]):  # Limitar a 5 para debug
                print(f"\n🔄 Processando contrato {i+1}/{min(contratos.count(), 5)}")
                print(f"📄 Contrato ID: {contrato.pk}")
                print(f"📄 Tipo: {contrato.tipo_contrato}")
                print(f"💵 Valor base: {contrato.valor_base}")
                
                # Verificar inquilino
                try:
                    inquilinos = contrato.inquilino.all()
                    print(f"👤 Inquilinos encontrados: {inquilinos.count()}")
                    
                    if inquilinos.exists():
                        inquilino = inquilinos.first()
                        inquilino_nome = inquilino.nome
                        inquilino_email = inquilino.email or ''
                        print(f"👤 Inquilino: {inquilino_nome}")
                    else:
                        inquilino_nome = 'Sem inquilino'
                        inquilino_email = ''
                        print("👤 Sem inquilino associado")
                        
                except Exception as e:
                    print(f"❌ Erro ao buscar inquilino: {e}")
                    inquilino_nome = 'Erro ao buscar inquilino'
                    inquilino_email = ''
                
                # Verificar se já existe cobrança para este período
                print(f"🔍 Verificando cobranças existentes...")
                cobranca_existente = Cobranca.objects.filter(
                    contrato=contrato,
                    mes_referencia=mes_referencia,
                    ano_referencia=ano_referencia
                ).exists()
                
                if cobranca_existente:
                    print(f"⚠️ Cobrança já existe para contrato {contrato.pk} - PULANDO")
                    continue
                
                print(f"✅ Contrato {contrato.pk} elegível para cobrança")
                
                # Calcular valor do aluguel
                valor_aluguel = contrato.valor_base or Decimal('0.00')
                valor_total = valor_aluguel
                despesas_detalhes = []
                
                print(f"💰 Valor aluguel: R$ {valor_aluguel}")
                
                # Gerar descrição automática simples
                descricao = f"Aluguel referente a {mes_referencia}/{ano_referencia}\nValor: R$ {valor_aluguel}"
                
                preview_cobranca = {
                    'contrato_id': contrato.pk,
                    'contrato_numero': contrato.tipo_contrato or f"Contrato {contrato.pk}",
                    'inquilino_nome': inquilino_nome,
                    'inquilino_email': inquilino_email,
                    'imovel_endereco': str(contrato.imovel) if contrato.imovel else 'Sem endereço',
                    'valor_aluguel': float(valor_aluguel),
                    'valor_total': float(valor_total),
                    'despesas': despesas_detalhes,
                    'descricao': descricao,
                    'pode_gerar': True,
                    'motivo_bloqueio': ''
                }
                
                print(f"✅ Preview criado: {preview_cobranca['contrato_numero']} - R$ {valor_total}")
                
                preview_cobrancas.append(preview_cobranca)
                total_geral += valor_total
            
            print(f"\n📊 RESUMO FINAL:")
            print(f"📄 Total de cobranças no preview: {len(preview_cobrancas)}")
            print(f"💰 Valor total geral: R$ {total_geral}")
            
            meses_dict = {
                1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
                5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
                9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
            }
            
            resultado = {
                'success': True,
                'cobrancas': preview_cobrancas,
                'total_cobrancas': len(preview_cobrancas),
                'valor_total_geral': float(total_geral),
                'mes_nome': meses_dict.get(mes_referencia, f'Mês {mes_referencia}'),
                'ano': ano_referencia
            }
            
            print(f"✅ Retornando resultado: {len(preview_cobrancas)} cobranças")
            print("=== FIM DEBUG API PREVIEW ===")
            
            return JsonResponse(resultado)
            
        except ImportError as e:
            print(f"❌ Erro de importação: {e}")
            return JsonResponse({'success': False, 'error': f'Modelo Contrato não encontrado: {e}'})
            
    except (ValueError, TypeError, json.JSONDecodeError) as e:
        print(f"❌ Erro de dados: {e}")
        return JsonResponse({'success': False, 'error': f'Dados inválidos: {str(e)}'})
    except Exception as e:
        print(f"❌ Erro geral: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': f'Erro interno: {str(e)}'})


def cobranca_gerar_selecionadas(request):
    """
    Gera as cobranças selecionadas no preview
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método não permitido'})
    
    try:
        data = json.loads(request.body)
        mes_referencia = int(data.get('mes_referencia'))
        ano_referencia = int(data.get('ano_referencia'))
        data_vencimento = date.fromisoformat(data.get('data_vencimento'))
        cobrancas_selecionadas = data.get('cobrancas_selecionadas', [])
        incluir_despesas = data.get('incluir_despesas', True)
        gerar_descricao_automatica = data.get('gerar_descricao_automatica', True)
        
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
                    # Verificar se já existe cobrança
                    if Cobranca.objects.filter(
                        contrato=contrato,
                        mes_referencia=mes_referencia,
                        ano_referencia=ano_referencia
                    ).exists():
                        erros.append(f'Cobrança já existe para {contrato}')
                        continue
                    
                    # Calcular valores
                    valor_aluguel = contrato.valor_base or Decimal('0.00')
                    valor_total = valor_aluguel
                    
                    # Criar cobrança
                    cobranca = Cobranca.objects.create(
                        contrato=contrato,
                        inquilino=contrato.inquilino,
                        mes_referencia=mes_referencia,
                        ano_referencia=ano_referencia,
                        valor_aluguel=valor_aluguel,
                        data_vencimento=data_vencimento,
                        status='pendente'
                    )
                    
                    # Calcular valor total incluindo despesas
                    if incluir_despesas:
                        cobranca.atualizar_valor_total()
                    else:
                        cobranca.valor_total = valor_aluguel
                        cobranca.save()
                    
                    # Gerar descrição automática
                    if gerar_descricao_automatica:
                        cobranca.descricao = cobranca.gerar_descricao_automatica()
                        cobranca.save()
                    
                    cobrancas_criadas.append({
                        'id': cobranca.pk,
                        'contrato': str(contrato),
                        'valor_total': float(cobranca.valor_total)
                    })
                    
                except Exception as e:
                    erros.append(f'Erro ao criar cobrança para {contrato}: {str(e)}')
            
            return JsonResponse({
                'success': True,
                'cobrancas_criadas': len(cobrancas_criadas),
                'detalhes': cobrancas_criadas,
                'erros': erros
            })
            
        except ImportError:
            return JsonResponse({'success': False, 'error': 'Modelo Contrato não encontrado'})
            
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Erro interno: {str(e)}'})


def cobranca_revisao_integracao(request):
    """
    Tela de revisão das cobranças criadas com opção de integração em lote
    """
    # Buscar cobranças pendentes recém-criadas
    cobrancas_pendentes = Cobranca.objects.filter(
        status='pendente',
        integrada_asaas=False
    ).select_related('contrato', 'inquilino').order_by('-data_criacao')[:20]
    
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
            status='pendente',
            integrada_asaas=False
        )
        
        integracoes_sucesso = 0
        integracoes_erro = 0
        erros_detalhados = []
        
        for cobranca in cobrancas:
            try:
                resultado = cobranca.gerar_cobranca_gateway()
                
                if resultado['status'] == 'success':
                    integracoes_sucesso += 1
                else:
                    integracoes_erro += 1
                    erros_detalhados.extend(resultado.get('erros', []))
                    
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
        f"Aluguel referente a {mes_nome} de {ano_referencia}",
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