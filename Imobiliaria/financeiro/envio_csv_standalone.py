# ================================================================
# SISTEMA CSV STANDALONE - TOTALMENTE INDEPENDENTE
# Crie um novo arquivo: envio_csv_standalone.py
# ================================================================

import csv
import io
import json
import os
import requests
import random
import uuid
from datetime import datetime
from pathlib import Path

class SistemaCSVStandalone:
    """Sistema independente para envio de mensagens via CSV"""
    
    def __init__(self):
        # Configurações Z-API (pode vir de .env ou ser configurado aqui)
        self.zapi_instance_id = os.getenv('ZAPI_INSTANCE_ID', 'SUA_INSTANCE_ID')
        self.zapi_token = os.getenv('ZAPI_TOKEN', 'SEU_TOKEN')
        self.zapi_client_token = os.getenv('ZAPI_CLIENT_TOKEN', 'SEU_CLIENT_TOKEN')
        
        # Modo dry run por padrão
        self.dry_run = True
        
        # Logs próprios
        self.logs = []
        
        print("🎯 Sistema CSV Standalone Iniciado")
        print(f"🧪 Modo: {'DRY RUN (simulação)' if self.dry_run else 'REAL'}")
    
    def set_dry_run(self, ativo=True):
        """Ativa/desativa modo dry run"""
        self.dry_run = ativo
        modo = "DRY RUN (simulação)" if ativo else "REAL"
        print(f"🔧 Modo alterado para: {modo}")
    
    def configurar_zapi(self, instance_id, token, client_token):
        """Configura credenciais Z-API"""
        self.zapi_instance_id = instance_id
        self.zapi_token = token
        self.zapi_client_token = client_token
        print("✅ Credenciais Z-API configuradas")
    
    def processar_csv(self, arquivo_path):
        """Processa arquivo CSV e retorna leads"""
        
        try:
            print(f"📁 Processando: {arquivo_path}")
            
            with open(arquivo_path, 'r', encoding='utf-8') as arquivo:
                # Detectar delimitador automaticamente
                sample = arquivo.read(1024)
                arquivo.seek(0)
                
                sniffer = csv.Sniffer()
                delimiter = sniffer.sniff(sample).delimiter
                
                print(f"🔍 Delimitador detectado: '{delimiter}'")
                
                # Ler CSV
                reader = csv.DictReader(arquivo, delimiter=delimiter)
                leads = list(reader)
                
                print(f"✅ {len(leads)} leads processados")
                print(f"📋 Colunas: {list(reader.fieldnames) if reader.fieldnames else 'N/A'}")
                
                return {
                    'sucesso': True,
                    'leads': leads,
                    'colunas': list(reader.fieldnames) if reader.fieldnames else [],
                    'total': len(leads)
                }
                
        except Exception as e:
            print(f"❌ Erro ao processar CSV: {e}")
            return {
                'sucesso': False,
                'erro': str(e),
                'leads': [],
                'colunas': [],
                'total': 0
            }
    
    def validar_telefone(self, telefone):
        """Valida telefone brasileiro"""
        if not telefone:
            return False
        
        # Limpar telefone
        numero = ''.join(filter(str.isdigit, str(telefone)))
        
        # Adicionar código do país se necessário
        if not numero.startswith('55'):
            numero = '55' + numero
        
        # Validar tamanho (11 dígitos + 55 = 13 total)
        return len(numero) >= 12
    
    def formatar_telefone_zapi(self, telefone):
        """Formata telefone para Z-API"""
        if not telefone:
            return None
        
        numero = ''.join(filter(str.isdigit, str(telefone)))
        
        if not numero.startswith('55'):
            numero = '55' + numero
        
        return numero if len(numero) >= 12 else None
    
    def personalizar_mensagem(self, template, lead, config_campos):
        """Personaliza mensagem com dados do lead"""
        
        # Extrair dados baseado na configuração
        nome = lead.get(config_campos.get('nome', 'Nome'), 'Lead')
        telefone = lead.get(config_campos.get('telefone', 'Telefone'), '')
        email = lead.get(config_campos.get('email', 'Email'), '')
        campo1 = lead.get(config_campos.get('campo1', ''), '')
        campo2 = lead.get(config_campos.get('campo2', ''), '')
        
        # Processar nome
        primeiro_nome = nome.split()[0] if nome and ' ' in nome else nome
        
        # Substituições
        substituicoes = {
            '{nome}': nome,
            '{primeiro_nome}': primeiro_nome,
            '{email}': email,
            '{telefone}': telefone,
            '{campo1}': campo1,
            '{campo2}': campo2,
            '{data_atual}': datetime.now().strftime('%d/%m/%Y'),
            '{hora_atual}': datetime.now().strftime('%H:%M'),
            '{data_completa}': datetime.now().strftime('%d/%m/%Y às %H:%M'),
        }
        
        # Aplicar substituições
        mensagem_final = template
        for placeholder, valor in substituicoes.items():
            mensagem_final = mensagem_final.replace(placeholder, str(valor))
        
        return mensagem_final
    
    def enviar_whatsapp_zapi(self, telefone, mensagem):
        """Envia WhatsApp via Z-API"""
        
        # MODO DRY RUN
        if self.dry_run:
            print("\n🧪 SIMULANDO ENVIO Z-API")
            print("=" * 40)
            print(f"📱 Para: {telefone}")
            print(f"📝 Mensagem: {mensagem[:100]}...")
            
            # Simular sucesso/falha
            sucesso = random.randint(1, 100) <= 90  # 90% sucesso
            
            if sucesso:
                fake_id = f"DRY_{uuid.uuid4().hex[:8]}"
                print(f"✅ SIMULADO - Sucesso! ID: {fake_id}")
                return {'success': True, 'messageId': fake_id}
            else:
                erro = random.choice([
                    "Número inválido",
                    "Usuário bloqueou bot",
                    "Limite de API atingido"
                ])
                print(f"❌ SIMULADO - Falha: {erro}")
                return {'success': False, 'error': erro}
        
        # MODO REAL
        if not all([self.zapi_instance_id, self.zapi_token, self.zapi_client_token]):
            return {'success': False, 'error': 'Credenciais Z-API não configuradas'}
        
        url = f"https://api.z-api.io/instances/{self.zapi_instance_id}/token/{self.zapi_token}/send-messages"
        
        payload = {
            "phone": telefone,
            "message": mensagem
        }
        
        headers = {
            "Content-Type": "application/json",
            "client-token": self.zapi_client_token
        }
        
        try:
            print(f"📤 Enviando para {telefone}...")
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                message_id = result.get('messageId') or result.get('id')
                
                if message_id:
                    print(f"✅ Enviado! ID: {message_id}")
                    return {'success': True, 'messageId': message_id}
                else:
                    print(f"❌ Falha: Resposta sem ID")
                    return {'success': False, 'error': 'Resposta sem messageId'}
            else:
                erro = f"HTTP {response.status_code}: {response.text}"
                print(f"❌ Falha: {erro}")
                return {'success': False, 'error': erro}
                
        except Exception as e:
            erro = f"Erro de conexão: {str(e)}"
            print(f"❌ Falha: {erro}")
            return {'success': False, 'error': erro}
    
    def executar_campanha(self, leads, config_campanha):
        """Executa campanha de envio para lista de leads"""
        
        print(f"\n🚀 INICIANDO CAMPANHA: {config_campanha['nome']}")
        print("=" * 50)
        print(f"👥 Total de leads: {len(leads)}")
        print(f"📱 Canal: WhatsApp")
        print(f"🧪 Modo: {'DRY RUN' if self.dry_run else 'REAL'}")
        
        resultados = []
        sucessos = 0
        falhas = 0
        
        for i, lead in enumerate(leads, 1):
            nome = lead.get(config_campanha['campos']['nome'], f'Lead {i}')
            telefone_original = lead.get(config_campanha['campos']['telefone'], '')
            
            print(f"\n{i}/{len(leads)} - {nome}")
            
            # Validar telefone
            if not self.validar_telefone(telefone_original):
                print(f"   ❌ Telefone inválido: {telefone_original}")
                resultado = {
                    'lead': nome,
                    'telefone': telefone_original,
                    'sucesso': False,
                    'erro': 'Telefone inválido',
                    'message_id': None
                }
                resultados.append(resultado)
                falhas += 1
                continue
            
            # Formatar telefone
            telefone_formatado = self.formatar_telefone_zapi(telefone_original)
            
            # Personalizar mensagem
            mensagem_personalizada = self.personalizar_mensagem(
                config_campanha['mensagem'], 
                lead, 
                config_campanha['campos']
            )
            
            # Enviar
            resultado_envio = self.enviar_whatsapp_zapi(telefone_formatado, mensagem_personalizada)
            
            # Registrar resultado
            resultado = {
                'lead': nome,
                'telefone': telefone_original,
                'sucesso': resultado_envio.get('success', False),
                'erro': resultado_envio.get('error'),
                'message_id': resultado_envio.get('messageId'),
                'mensagem': mensagem_personalizada
            }
            
            resultados.append(resultado)
            
            if resultado['sucesso']:
                sucessos += 1
                print(f"   ✅ Sucesso!")
            else:
                falhas += 1
                print(f"   ❌ Falha: {resultado['erro']}")
            
            # Log para arquivo
            self.logs.append({
                'timestamp': datetime.now().isoformat(),
                'campanha': config_campanha['nome'],
                'lead': nome,
                'telefone': telefone_original,
                'sucesso': resultado['sucesso'],
                'erro': resultado.get('erro'),
                'message_id': resultado.get('message_id')
            })
        
        # Relatório final
        print(f"\n📊 RELATÓRIO FINAL DA CAMPANHA")
        print("=" * 50)
        print(f"🎯 Campanha: {config_campanha['nome']}")
        print(f"📅 Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        print(f"👥 Total processado: {len(leads)}")
        print(f"✅ Sucessos: {sucessos}")
        print(f"❌ Falhas: {falhas}")
        print(f"📈 Taxa de sucesso: {(sucessos/len(leads)*100):.1f}%")
        
        return {
            'campanha': config_campanha['nome'],
            'resultados': resultados,
            'estatisticas': {
                'total': len(leads),
                'sucessos': sucessos,
                'falhas': falhas,
                'taxa_sucesso': (sucessos/len(leads)*100) if leads else 0
            }
        }
    
    def salvar_relatorio(self, resultado_campanha, pasta='relatorios'):
        """Salva relatório da campanha em arquivo"""
        
        # Criar pasta se não existir
        Path(pasta).mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        nome_arquivo = f"{pasta}/campanha_{timestamp}.json"
        
        # Adicionar timestamp aos resultados
        resultado_campanha['timestamp'] = timestamp
        resultado_campanha['data_execucao'] = datetime.now().isoformat()
        
        # Salvar JSON
        with open(nome_arquivo, 'w', encoding='utf-8') as f:
            json.dump(resultado_campanha, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Relatório salvo: {nome_arquivo}")
        
        # Salvar CSV também
        nome_csv = f"{pasta}/campanha_{timestamp}.csv"
        with open(nome_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Lead', 'Telefone', 'Sucesso', 'Erro', 'Message_ID'])
            
            for resultado in resultado_campanha['resultados']:
                writer.writerow([
                    resultado['lead'],
                    resultado['telefone'],
                    'Sim' if resultado['sucesso'] else 'Não',
                    resultado.get('erro', ''),
                    resultado.get('message_id', '')
                ])
        
        print(f"📊 CSV salvo: {nome_csv}")
        
        return nome_arquivo, nome_csv

# ================================================================
# EXEMPLOS DE USO STANDALONE
# ================================================================

def exemplo_uso_completo():
    """Exemplo completo de uso do sistema standalone"""
    
    print("🎯 EXEMPLO COMPLETO - SISTEMA STANDALONE")
    print("=" * 60)
    
    # 1. Criar instância do sistema
    sistema = SistemaCSVStandalone()
    
    # 2. Configurar modo dry run (seguro)
    sistema.set_dry_run(True)
    
    # 3. Dados de exemplo (como se fossem do seu CSV)
    leads_exemplo = [
        {
            'Nome': 'Catia Camargo',
            'Email': 'catiar_camargo@outlook.com',
            'Telefone': '+5511983460099',
            'Estágio': 'Em análise',
            'Formulário': 'Interesse Sobrado Comercial - Médicos',
            'Fonte': 'Pago'
        },
        {
            'Nome': 'Juliana Felgueiras',
            'Email': 'juliana.rh.andrade@gmail.com',
            'Telefone': '+5511993572641',
            'Estágio': 'Em análise',
            'Formulário': 'Interesse Sobrado Comercial - Médicos',
            'Fonte': 'Pago'
        }
    ]
    
    # 4. Configurar campanha
    config_campanha = {
        'nome': 'Campanha Médicos - Standalone',
        'campos': {
            'nome': 'Nome',
            'telefone': 'Telefone',
            'email': 'Email',
            'campo1': 'Formulário',
            'campo2': 'Estágio'
        },
        'mensagem': """Olá Dr(a). {primeiro_nome}!

Obrigado pelo interesse em "{campo1}" através de nossa plataforma.

🏥 OPORTUNIDADES EXCLUSIVAS PARA MÉDICOS:
• Sobrados comerciais na região médica
• Infraestrutura completa para consultórios
• Estacionamento exclusivo para pacientes
• Facilidades para licenciamento sanitário

📋 SEUS DADOS:
• Nome: {nome}
• E-mail: {email}
• Status: {campo2}
• Telefone: {telefone}

💡 PRÓXIMO PASSO:
Gostaria de agendar uma visita técnica?

📞 WhatsApp: (11) 99999-9999
📧 comercial@exemplo.com

Atenciosamente,
Equipe Médica Especializada

---
Contato em {data_completa}"""
    }
    
    # 5. Executar campanha
    resultado = sistema.executar_campanha(leads_exemplo, config_campanha)
    
    # 6. Salvar relatório
    arquivo_json, arquivo_csv = sistema.salvar_relatorio(resultado)
    
    print(f"\n✅ EXEMPLO CONCLUÍDO!")
    print(f"📁 Relatórios salvos:")
    print(f"   • JSON: {arquivo_json}")
    print(f"   • CSV: {arquivo_csv}")
    
    return resultado

def exemplo_com_seu_csv():
    """Exemplo usando seu arquivo CSV real"""
    
    print("📁 EXEMPLO COM SEU CSV REAL")
    print("=" * 40)
    
    # Criar conteúdo do seu CSV
    csv_content = """Criado em,Nome,Email,Fonte,Formulário,Canal,Estágio,Proprietário,Rótulos,Telefone,Número de telefone secundário
07/06/2025 10:21am,Catia Camargo,catiar_camargo@outlook.com,Pago,Interesse Sobrado Comercial - Médicos,Email,Em análise,Unassigned,,+5511983460099,
07/06/2025 7:42am,Depilação Laser & Procedimentos Estéticos - Brasilandia - ZN,danimacedoooo@hotmail.com,Pago,Interesse Sobrado Comercial - Médicos,Email,Em análise,Unassigned,,+5511989192326,
07/05/2025 12:54pm,Juliana Felgueiras • RNM,juliana.rh.andrade@gmail.com,Pago,Interesse Sobrado Comercial - Médicos,Email,Em análise,Unassigned,,+5511993572641,"""
    
    # Salvar temporariamente
    with open('leads_temp.csv', 'w', encoding='utf-8') as f:
        f.write(csv_content)
    
    # Usar sistema standalone
    sistema = SistemaCSVStandalone()
    sistema.set_dry_run(True)
    
    # Processar CSV
    resultado_csv = sistema.processar_csv('leads_temp.csv')
    
    if resultado_csv['sucesso']:
        # Configurar campanha
        config = {
            'nome': 'Campanha Seus Leads Reais',
            'campos': {
                'nome': 'Nome',
                'telefone': 'Telefone', 
                'email': 'Email',
                'campo1': 'Formulário',
                'campo2': 'Estágio'
            },
            'mensagem': """Olá {primeiro_nome}!

Vi que você demonstrou interesse em "{campo1}".

🏥 SOBRADOS COMERCIAIS PARA MÉDICOS:
• Localização estratégica na região médica
• Infraestrutura completa para consultórios  
• Estacionamento exclusivo para pacientes

Status atual: {campo2}
Seu contato: {telefone}

Gostaria de agendar uma visita?

📞 WhatsApp: (11) 99999-9999

Atenciosamente,
Equipe Especializada"""
        }
        
        # Executar
        resultado_campanha = sistema.executar_campanha(resultado_csv['leads'], config)
        
        # Salvar
        sistema.salvar_relatorio(resultado_campanha)
        
        # Limpar arquivo temporário
        os.remove('leads_temp.csv')
        
        return resultado_campanha
    
    else:
        print(f"❌ Erro ao processar CSV: {resultado_csv['erro']}")
        return None

# ================================================================
# SCRIPT PRINCIPAL
# ================================================================

if __name__ == "__main__":
    print("""
🎯 SISTEMA CSV STANDALONE - INDEPENDENTE

Este sistema funciona totalmente separado do seu Django atual!

COMANDOS DISPONÍVEIS:

1. Exemplo completo:
   resultado = exemplo_uso_completo()

2. Com seu CSV real:
   resultado = exemplo_com_seu_csv()

3. Uso manual:
   sistema = SistemaCSVStandalone()
   sistema.set_dry_run(True)
   leads = sistema.processar_csv('arquivo.csv')['leads'] 
   resultado = sistema.executar_campanha(leads, config)

🔧 CONFIGURAÇÃO Z-API:
   sistema.configurar_zapi('instance_id', 'token', 'client_token')

⚠️  SEMPRE TESTE EM DRY RUN PRIMEIRO!
""")
    
    # Auto-executar exemplo
    exemplo_uso_completo()