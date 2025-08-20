from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from financeiro.models.cobranca import Cobranca
from financeiro.models.lembrete import LembreteEnviado
from financeiro.utils.data_utils import dia_util_anterior, is_dia_util, proximo_dia_util

class Command(BaseCommand):
    help = 'Gera relatório de lembretes considerando apenas dias úteis'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dias-antes',
            nargs='+',
            type=int,
            default=[10, 3, 1, 0],
            help='Dias ÚTEIS antes do vencimento (padrão: 10 3 1 0)'
        )
        parser.add_argument(
            '--mostrar-calendario',
            action='store_true',
            help='Mostra calendário de dias úteis'
        )

    def handle(self, *args, **options):
        self.stdout.write("📋 RELATÓRIO DIÁRIO DE LEMBRETES (DIAS ÚTEIS)")
        self.stdout.write("=" * 70)
        
        hoje = date.today()
        dias_antes = options['dias_antes']
        
        self.stdout.write(f"📅 Data atual: {hoje.strftime('%d/%m/%Y')} ({self._nome_dia_semana(hoje)})")
        self.stdout.write(f"💼 É dia útil: {'✅ SIM' if is_dia_util(hoje) else '❌ NÃO'}")
        self.stdout.write(f"⏰ Dias úteis configurados: {dias_antes}")
        
        if options['mostrar_calendario']:
            self._mostrar_calendario_dias_uteis(hoje)
        
        if not is_dia_util(hoje):
            proximo_util = proximo_dia_util(hoje)
            self.stdout.write(f"⚠️ Hoje não é dia útil. Próximo dia útil: {proximo_util.strftime('%d/%m/%Y')}")
            self.stdout.write(f"💡 Execute novamente em {proximo_util.strftime('%d/%m/%Y')}")
            return
        
        total_lembretes = 0
        lembretes_por_categoria = {}
        
        # Para cada configuração de dias úteis
        for dias in dias_antes:
            self.stdout.write(f"\n{'='*50}")
            
            # Buscar cobranças que precisam de lembrete hoje
            cobrancas_para_lembrete = self._buscar_cobrancas_para_lembrete(hoje, dias)
            
            if dias == 0:
                categoria = "🚨 VENCIMENTO HOJE"
            elif dias == 1:
                categoria = f"⚠️ VENCE NO PRÓXIMO DIA ÚTIL"
            else:
                categoria = f"📅 VENCE EM {dias} DIAS ÚTEIS"
            
            self.stdout.write(categoria)
            
            lembretes_encontrados = []
            
            for info in cobrancas_para_lembrete:
                cobranca = info['cobranca']
                data_envio_calculada = info['data_envio']
                data_vencimento = info['data_vencimento']
                
                # Verificar se já foi enviado
                ja_enviado = LembreteEnviado.objects.filter(
                    cobranca=cobranca,
                    dias_antes_vencimento=dias,
                    status='enviado'
                ).exists()
                
                if ja_enviado:
                    continue
                
                # Obter informações do inquilino
                inquilino_info = self._get_inquilino_info(cobranca)
                
                if not inquilino_info['nome']:
                    self.stdout.write(f"   ⚠️ Sem inquilino: Cobrança #{cobranca.pk}")
                    continue
                
                if not inquilino_info['telefone']:
                    self.stdout.write(f"   📵 Sem telefone: {inquilino_info['nome']}")
                    continue
                
                lembretes_encontrados.append({
                    'cobranca': cobranca,
                    'inquilino': inquilino_info,
                    'data_envio': data_envio_calculada,
                    'data_vencimento': data_vencimento,
                    'dias_uteis': dias
                })
            
            if lembretes_encontrados:
                self.stdout.write(f"📤 {len(lembretes_encontrados)} lembretes para enviar:")
                
                for item in lembretes_encontrados:
                    cobranca = item['cobranca']
                    inquilino = item['inquilino']
                    
                    self.stdout.write(
                        f"   • {inquilino['nome']} - R$ {cobranca.valor_total} - "
                        f"Venc: {item['data_vencimento'].strftime('%d/%m/%Y')} - "
                        f"Tel: {inquilino['telefone']}"
                    )
                
                lembretes_por_categoria[dias] = lembretes_encontrados
                total_lembretes += len(lembretes_encontrados)
            else:
                self.stdout.write(f"   ✅ Nenhum lembrete necessário")
        
        # Resumo final
        self.stdout.write(f"\n{'='*70}")
        self.stdout.write(f"📊 RESUMO GERAL:")
        self.stdout.write(f"   📅 Data: {hoje.strftime('%d/%m/%Y (%A)')}")
        self.stdout.write(f"   📤 Total de lembretes: {total_lembretes}")
        
        if lembretes_por_categoria:
            self.stdout.write(f"   📋 Por categoria:")
            for dias, lembretes in lembretes_por_categoria.items():
                nome_categoria = self._get_nome_categoria(dias)
                self.stdout.write(f"      {nome_categoria}: {len(lembretes)}")
        
        if total_lembretes > 0:
            self.stdout.write(f"\n🚀 PRÓXIMO PASSO:")
            self.stdout.write(f"   Acesse: http://localhost:8000/financeiro/lembretes/envio-programado/")
        else:
            self.stdout.write(f"\n✅ Nenhuma ação necessária hoje!")
    
    def _buscar_cobrancas_para_lembrete(self, hoje, dias_uteis_antes):
        """
        Busca cobranças que precisam de lembrete hoje baseado em dias úteis
        """
        cobrancas_info = []
        
        # Buscar todas as cobranças pendentes
        cobrancas = Cobranca.objects.filter(
            status__in=['pendente', 'atrasada']
        )
        
        for cobranca in cobrancas:
            data_vencimento = cobranca.data_vencimento
            
            # Calcular quando deve ser enviado o lembrete para esta cobrança
            data_envio_calculada = dia_util_anterior(data_vencimento, dias_uteis_antes)
            
            # Se a data de envio calculada é hoje, incluir na lista
            if data_envio_calculada == hoje:
                cobrancas_info.append({
                    'cobranca': cobranca,
                    'data_envio': data_envio_calculada,
                    'data_vencimento': data_vencimento,
                    'dias_uteis_antes': dias_uteis_antes
                })
        
        return cobrancas_info
    
    def _get_inquilino_info(self, cobranca):
        """
        Obtém informações do inquilino de forma defensiva
        """
        info = {
            'nome': None,
            'telefone': None,
            'inquilino': None
        }
        
        try:
            # Tentar diferentes formas de acessar inquilino
            inquilino = None
            
            if hasattr(cobranca, 'inquilino') and cobranca.inquilino:
                inquilino = cobranca.inquilino
            elif hasattr(cobranca, 'contrato') and cobranca.contrato:
                contrato = cobranca.contrato
                if hasattr(contrato, 'inquilino'):
                    if hasattr(contrato.inquilino, 'nome'):
                        inquilino = contrato.inquilino
                    elif hasattr(contrato.inquilino, 'first'):
                        inquilino = contrato.inquilino.first()
            
            if inquilino:
                info['inquilino'] = inquilino
                info['nome'] = getattr(inquilino, 'nome', None)
                
                # Buscar telefone
                for campo in ['whatsapp', 'telefone', 'celular', 'telefone_celular']:
                    if hasattr(inquilino, campo):
                        telefone = getattr(inquilino, campo)
                        if telefone:
                            info['telefone'] = telefone
                            break
        
        except Exception as e:
            self.stdout.write(f"   ❌ Erro ao acessar inquilino da cobrança {cobranca.pk}: {str(e)}")
        
        return info
    
    def _mostrar_calendario_dias_uteis(self, hoje):
        """
        Mostra calendário dos próximos dias úteis
        """
        self.stdout.write(f"\n📅 CALENDÁRIO DOS PRÓXIMOS DIAS ÚTEIS:")
        self.stdout.write("-" * 50)
        
        data_atual = hoje
        for i in range(15):  # Próximos 15 dias
            util = "✅" if is_dia_util(data_atual) else "❌"
            dia_semana = self._nome_dia_semana(data_atual)
            
            self.stdout.write(f"   {data_atual.strftime('%d/%m/%Y')} ({dia_semana}) {util}")
            data_atual += timedelta(days=1)
    
    def _nome_dia_semana(self, data):
        """Retorna nome do dia da semana em português"""
        dias = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
        return dias[data.weekday()]
    
    def _get_nome_categoria(self, dias):
        """Retorna nome amigável da categoria"""
        if dias == 0:
            return "Vencimento hoje"
        elif dias == 1:
            return "Próximo dia útil"
        else:
            return f"{dias} dias úteis antes"