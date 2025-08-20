# ================================================================
# minha_campanha.py - ARQUIVO COMPLETO COM .ENV
# ================================================================

import csv
import os
from envio_csv_standalone import SistemaCSVStandalone
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / '.env'  # Imobiliaria/.env
load_dotenv(env_path)

def enviar_mensagem_guilherme():
    """Campanha Guilherme - Sobrado Itapura"""
    
    print("🎯 CAMPANHA GUILHERME - SOBRADO ITAPURA")
    print("=" * 50)
    
    # 1. Criar o sistema
    sistema = SistemaCSVStandalone()
    
    # 2. Configurar Z-API com variáveis do .env
    instance_id = os.getenv('ZAPI_INSTANCE_ID', '')
    token = os.getenv('ZAPI_TOKEN', '') 
    client_token = os.getenv('ZAPI_CLIENT_TOKEN', '')
    
    # Verificar se as variáveis foram configuradas
    if not all([instance_id, token, client_token]):
        print("⚠️  Variáveis Z-API não configuradas no .env")
        print("📋 Configure no .env:")
        print("   ZAPI_INSTANCE_ID=sua_instance")
        print("   ZAPI_TOKEN=seu_token")
        print("   ZAPI_CLIENT_TOKEN=seu_client_token")
        print("\n🧪 Executando em modo DRY RUN por segurança")
        sistema.set_dry_run(True)
    else:
        print("✅ Credenciais Z-API encontradas no .env")
        sistema.configurar_zapi(instance_id, token, client_token)
        
        # ESCOLHER MODO: DRY RUN OU REAL
        modo_real = input("\n🚨 Deseja enviar mensagens REAIS? (s/N): ").lower()
        
        if modo_real == 's':
            sistema.set_dry_run(False)
            print("🚨 MODO REAL ATIVADO - Mensagens serão enviadas!")
            
            # Confirmação extra
            confirmacao = input("⚠️  Tem certeza? Digite 'CONFIRMO' para continuar: ")
            if confirmacao != 'CONFIRMO':
                print("❌ Operação cancelada por segurança")
                sistema.set_dry_run(True)
        else:
            sistema.set_dry_run(True)
            print("🧪 Mantendo modo DRY RUN (simulação)")
    
    # 3. Processar CSV
    print(f"\n📁 Processando arquivo CSV...")
    resultado = processar_csv_leads('leads.csv')
    
    if not resultado['sucesso']:
        print("❌ Erro ao processar CSV!")
        return None
    
    leads = resultado['leads']
    print(f"✅ {len(leads)} leads carregados")
    
    # Mostrar preview dos primeiros 3 leads
    if leads:
        print(f"\n👀 Preview dos primeiros 3 leads:")
        for i, lead in enumerate(leads[:3], 1):
            nome = lead.get('Nome', 'Sem nome')
            telefone = lead.get('Telefone', 'Sem telefone')
            print(f"   {i}. {nome} - {telefone}")
    
    # 4. Configurar campanha com SUA mensagem
    config_campanha = {
        'nome': 'Guilherme - Sobrado Comercial Rua Itapura',
        'campos': {
            'nome': 'Nome',
            'telefone': 'Telefone', 
            'email': 'Email',
            'campo1': 'Formulário',
            'campo2': 'Estágio'
        },
        'mensagem': """Olá! 
Vi que você se interessou pelo sobrado comercial na Rua Itapura.
Sou Guilherme e estou cuidando da locação do imóvel.
Posso te enviar algumas fotos extras e esclarecer suas dúvidas?
Quando seria um bom horário para conversarmos?

https://www.palestraimoveis.com.br/imovel/3779597/sobrado-comercial-locacao-sao-paulo-sp-vila-gomes-cardim"""
    }
    
    # 5. Última confirmação antes de executar
    print(f"\n📋 RESUMO DA CAMPANHA:")
    print(f"🎯 Nome: {config_campanha['nome']}")
    print(f"👥 Leads: {len(leads)}")
    print(f"📱 Canal: WhatsApp")
    print(f"🧪 Modo: {'REAL' if not sistema.dry_run else 'DRY RUN'}")
    
    if not sistema.dry_run:
        print(f"\n🚨 ATENÇÃO: Modo REAL ativo!")
        print(f"📱 Mensagens serão enviadas de verdade para {len(leads)} pessoas!")
        
        ultima_chance = input("\n⚠️  Última chance! Continuar? (s/N): ").lower()
        if ultima_chance != 's':
            print("❌ Operação cancelada")
            return None
    
    # 6. Executar campanha
    print(f"\n🚀 Iniciando envio...")
    resultado_campanha = sistema.executar_campanha(leads, config_campanha)
    
    # 7. Salvar relatórios
    arquivo_json, arquivo_csv = sistema.salvar_relatorio(resultado_campanha)
    
    # 8. Resumo final
    estatisticas = resultado_campanha['estatisticas']
    
    print(f"\n🎉 CAMPANHA CONCLUÍDA!")
    print(f"=" * 30)
    print(f"✅ Sucessos: {estatisticas['sucessos']}")
    print(f"❌ Falhas: {estatisticas['falhas']}")
    print(f"📈 Taxa: {estatisticas['taxa_sucesso']:.1f}%")
    print(f"📁 Relatórios:")
    print(f"   • JSON: {arquivo_json}")
    print(f"   • CSV: {arquivo_csv}")
    
    return resultado_campanha

def processar_csv_leads(arquivo_csv):
    """Processa CSV com diferentes delimitadores"""
    
    delimitadores = [',', ';', '\t']
    
    for delim in delimitadores:
        try:
            print(f"🔄 Tentando delimitador: '{delim}'")
            
            with open(arquivo_csv, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter=delim)
                leads = list(reader)
                
                # Verificar se deu certo
                if len(leads) > 0 and len(reader.fieldnames) > 1:
                    print(f"✅ Sucesso com delimitador '{delim}'!")
                    print(f"📋 Colunas: {reader.fieldnames}")
                    
                    # Limpar BOM se existir
                    fieldnames_clean = []
                    for field in reader.fieldnames:
                        # Remover BOM Unicode
                        clean_field = field.replace('\ufeff', '').strip()
                        fieldnames_clean.append(clean_field)
                    
                    # Atualizar leads com campos limpos
                    leads_clean = []
                    for lead in leads:
                        lead_clean = {}
                        for old_key, value in lead.items():
                            new_key = old_key.replace('\ufeff', '').strip()
                            lead_clean[new_key] = value
                        leads_clean.append(lead_clean)
                    
                    return {
                        'sucesso': True,
                        'leads': leads_clean,
                        'colunas': fieldnames_clean,
                        'total': len(leads_clean)
                    }
                    
        except Exception as e:
            print(f"❌ Falhou com '{delim}': {e}")
            continue
    
    return {
        'sucesso': False,
        'erro': 'Não foi possível processar o CSV',
        'leads': [],
        'colunas': [],
        'total': 0
    }

def verificar_configuracao():
    """Verifica se tudo está configurado corretamente"""
    
    print("🔍 VERIFICANDO CONFIGURAÇÃO")
    print("=" * 30)
    
    # Verificar arquivo CSV
    if os.path.exists('leads.csv'):
        print("✅ Arquivo leads.csv encontrado")
    else:
        print("❌ Arquivo leads.csv não encontrado")
        return False
    
    # Verificar sistema
    try:
        from envio_csv_standalone import SistemaCSVStandalone
        print("✅ Sistema SistemaCSVStandalone disponível")
    except ImportError:
        print("❌ Arquivo envio_csv_standalone.py não encontrado")
        return False
    
    # Verificar variáveis .env
    instance_id = os.getenv('ZAPI_INSTANCE_ID', '')
    token = os.getenv('ZAPI_TOKEN', '')
    client_token = os.getenv('ZAPI_CLIENT_TOKEN', '')
    
    if all([instance_id, token, client_token]):
        print("✅ Variáveis Z-API configuradas no .env")
    else:
        print("⚠️  Variáveis Z-API não configuradas (usará dry run)")
    
    print("\n🎯 Configuração verificada!")
    return True

def menu_principal():
    """Menu principal do sistema"""
    
    print("""
🎯 SISTEMA DE ENVIO GUILHERME
============================

1. ✅ Verificar configuração
2. 🧪 Executar em modo DRY RUN (seguro)
3. 📱 Executar em modo REAL (cuidado!)
4. 📊 Sair

""")
    
    opcao = input("Escolha uma opção (1-4): ").strip()
    
    if opcao == '1':
        verificar_configuracao()
        input("\nPressione Enter para continuar...")
        menu_principal()
        
    elif opcao == '2':
        print("\n🧪 Executando em modo DRY RUN...")
        # Forçar dry run
        os.environ['FORCE_DRY_RUN'] = 'true'
        enviar_mensagem_guilherme()
        
    elif opcao == '3':
        print("\n🚨 Executando em modo REAL...")
        enviar_mensagem_guilherme()
        
    elif opcao == '4':
        print("👋 Até logo!")
        return
        
    else:
        print("❌ Opção inválida!")
        menu_principal()

# ================================================================
# VERSÃO SIMPLIFICADA PARA EXECUÇÃO DIRETA
# ================================================================

def executar_direto():
    """Execução direta sem menu"""
    
    # Verificar configuração primeiro
    if not verificar_configuracao():
        print("\n❌ Configuração incompleta!")
        return
    
    # Executar campanha
    enviar_mensagem_guilherme()

# ================================================================
# EXECUÇÃO PRINCIPAL
# ================================================================

if __name__ == "__main__":
    print("🎯 CAMPANHA GUILHERME - SOBRADO ITAPURA")
    print("Rua Itapura - Vila Gomes Cardim")
    print("=" * 50)
    
    # Escolher modo de execução
    modo = input("""
Escolha o modo de execução:

1. 📋 Menu completo (recomendado)
2. ⚡ Execução direta
3. 🧪 Só dry run

Digite sua escolha (1-3): """).strip()
    
    if modo == '1':
        menu_principal()
    elif modo == '2':
        executar_direto()
    elif modo == '3':
        print("\n🧪 Executando só em dry run...")
        os.environ['FORCE_DRY_RUN'] = 'true'
        executar_direto()
    else:
        print("❌ Opção inválida! Executando modo padrão...")
        executar_direto()