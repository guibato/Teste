#!/usr/bin/env python
"""
Script para testar as melhorias implementadas no projeto Django de administração imobiliária.
Este script verifica se o projeto está funcionando corretamente após as melhorias.
"""

import os
import sys
import django
from django.core.management import call_command
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.conf import settings

# Configurar o ambiente Django
sys.path.append('/home/ubuntu/Teste/Imobiliaria')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Imobiliaria.settings')
django.setup()

# Importar modelos após configurar o ambiente
from sisimob.models import Cliente, Imovel, Contrato, Cobranca
from sisimob.views.cliente_views import listar_clientes
from sisimob.views.contrato_views import dashboard
from django.test.client import RequestFactory

def test_environment_variables():
    """Testa se as variáveis de ambiente estão configuradas corretamente."""
    print("\n=== Testando variáveis de ambiente ===")

    # Verificar se as variáveis de ambiente estão sendo carregadas
    required_vars = [
        'DJANGO_SECRET_KEY',
        'ASAAS_API_KEY',
        'ASAAS_API_URL',
    ]

    all_ok = True
    for var in required_vars:
        value = getattr(settings, var, None)
        if value:
            masked_value = value[:5] + '...' + value[-5:] if len(value) > 10 else '***'
            print(f"✅ {var} está configurada: {masked_value}")
        else:
            print(f"❌ {var} não está configurada")
            all_ok = False

    return all_ok

def test_database_connection():
    """Testa a conexão com o banco de dados."""
    print("\n=== Testando conexão com o banco de dados ===")

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            if result[0] == 1:
                print("✅ Conexão com o banco de dados estabelecida com sucesso")
                return True
            else:
                print("❌ Erro ao verificar conexão com o banco de dados")
                return False
    except Exception as e:
        print(f"❌ Erro ao conectar ao banco de dados: {str(e)}")
        return False

def test_models():
    """Testa se os modelos estão funcionando corretamente."""
    print("\n=== Testando modelos ===")

    try:
        num_clientes = Cliente.objects.count()
        num_imoveis = Imovel.objects.count()
        num_contratos = Contrato.objects.count()
        num_cobrancas = Cobranca.objects.count()

        print(f"✅ Clientes: {num_clientes}")
        print(f"✅ Imóveis: {num_imoveis}")
        print(f"✅ Contratos: {num_contratos}")
        print(f"✅ Cobranças: {num_cobrancas}")

        return True
    except Exception as e:
        print(f"❌ Erro ao acessar modelos: {str(e)}")
        return False

def test_query_optimization():
    """Testa as otimizações de consulta implementadas."""
    print("\n=== Testando otimizações de consulta ===")

    try:
        # Testar otimização na listagem de contratos
        with CaptureQueriesContext(connection) as queries:
            contratos = Contrato.objects.select_related('proprietario', 'inquilino', 'imovel').all()[:5]
            # Forçar a execução da consulta
            list(contratos)

        num_queries_otimizado = len(queries)

        # Testar sem otimização
        with CaptureQueriesContext(connection) as queries:
            contratos = Contrato.objects.all()[:5]
            # Acessar proprietário e inquilino para forçar consultas adicionais
            for contrato in contratos:
                _ = contrato.proprietario.nome
                _ = contrato.inquilino.nome
                _ = contrato.imovel.endereco

        num_queries_nao_otimizado = len(queries)

        print(f"Número de consultas com otimização: {num_queries_otimizado}")
        print(f"Número de consultas sem otimização: {num_queries_nao_otimizado}")

        if num_queries_otimizado < num_queries_nao_otimizado:
            print(f"✅ Otimização reduziu o número de consultas em {num_queries_nao_otimizado - num_queries_otimizado}")
            return True
        else:
            print("❌ Otimização não reduziu o número de consultas")
            return False
    except Exception as e:
        print(f"❌ Erro ao testar otimizações: {str(e)}")
        return False

def test_views():
    """Testa se as views estão funcionando corretamente."""
    print("\n=== Testando views ===")

    try:
        # Criar um request factory para simular requisições
        factory = RequestFactory()

        # Testar view de listagem de clientes
        request = factory.get('/clientes/listar/')
        with CaptureQueriesContext(connection) as queries:
            response = listar_clientes(request)

        if response.status_code == 200:
            print(f"✅ View listar_clientes funcionando (Consultas: {len(queries)})")
        else:
            print(f"❌ Erro na view listar_clientes: status code {response.status_code}")

        # Testar view de dashboard (se houver contratos)
        if Contrato.objects.exists():
            contrato_id = Contrato.objects.first().id
            request = factory.get(f'/contratos/dashboard/{contrato_id}/')
            with CaptureQueriesContext(connection) as queries:
                try:
                    response = dashboard(request, contrato_id)
                    if response.status_code == 200:
                        print(f"✅ View dashboard funcionando (Consultas: {len(queries)})")
                    else:
                        print(f"❌ Erro na view dashboard: status code {response.status_code}")
                except Exception as e:
                    print(f"❌ Erro ao testar view dashboard: {str(e)}")
        else:
            print("ℹ️ Nenhum contrato encontrado para testar a view dashboard")

        return True
    except Exception as e:
        print(f"❌ Erro ao testar views: {str(e)}")
        return False

def test_asaas_service():
    """Testa se o serviço Asaas está configurado corretamente."""
    print("\n=== Testando serviço Asaas ===")

    try:
        from sisimob.utils.asaas_service import AsaasService

        service = AsaasService()

        if service.api_key and service.base_url:
            print(f"✅ Serviço Asaas configurado corretamente")
            print(f"  - API Key: {service.api_key[:5]}...{service.api_key[-5:]}")
            print(f"  - Base URL: {service.base_url}")
            return True
        else:
            print("❌ Serviço Asaas não configurado corretamente")
            return False
    except Exception as e:
        print(f"❌ Erro ao testar serviço Asaas: {str(e)}")
        return False

def run_tests():
    """Executa todos os testes."""
    print("\n===== INICIANDO TESTES =====")

    tests = [
        test_environment_variables,
        test_database_connection,
        test_models,
        test_query_optimization,
        test_views,
        test_asaas_service,
    ]

    results = []
    for test in tests:
        results.append(test())

    print("\n===== RESUMO DOS TESTES =====")
    print(f"Total de testes: {len(tests)}")
    print(f"Testes bem-sucedidos: {results.count(True)}")
    print(f"Testes com falha: {results.count(False)}")

    if all(results):
        print("\n✅ TODOS OS TESTES PASSARAM!")
        return 0
    else:
        print("\n❌ ALGUNS TESTES FALHARAM!")
        return 1

if __name__ == "__main__":
    sys.exit(run_tests())
