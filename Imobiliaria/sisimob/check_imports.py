# Salve este arquivo como check_imports.py e execute para verificar o ambiente
import os
import sys
import importlib

def check_path_and_imports():
    print("=== VERIFICAÇÃO DE IMPORTAÇÕES E CAMINHOS ===")
    print(f"Diretório atual: {os.getcwd()}")
    print(f"Python path: {sys.path}")
    
    # Verificar os diretórios
    try:
        sisimob_dir = os.path.join(os.getcwd(), 'sisimob')
        print(f"Diretório sisimob existe: {os.path.exists(sisimob_dir)}")
        
        utils_dir = os.path.join(sisimob_dir, 'utils')
        print(f"Diretório utils existe: {os.path.exists(utils_dir)}")
        
        asaas_file = os.path.join(utils_dir, 'cobrancas_asaas.py')
        print(f"Arquivo cobrancas_asaas.py existe: {os.path.exists(asaas_file)}")
    except Exception as e:
        print(f"Erro ao verificar diretórios: {e}")
    
    # Tentar importar
    modules_to_check = [
        'sisimob',
        'sisimob.utils',
        'sisimob.utils.cobrancas_asaas',
        'utils',
        'utils.cobrancas_asaas'
    ]
    
    for module in modules_to_check:
        try:
            imported = importlib.import_module(module)
            print(f"✅ Módulo {module} importado com sucesso")
            
            if module.endswith('cobrancas_asaas'):
                print(f"Funções no módulo: {dir(imported)}")
                if hasattr(imported, 'gerar_cobranca'):
                    print("✅ Função gerar_cobranca encontrada!")
                else:
                    print("❌ Função gerar_cobranca NÃO encontrada!")
        except ImportError as e:
            print(f"❌ Erro ao importar {module}: {e}")
    
    print("=== FIM DA VERIFICAÇÃO ===")

if __name__ == "__main__":
    check_path_and_imports()