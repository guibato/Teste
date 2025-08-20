# financeiro/management/commands/verificar_feriados_bancarios.py
# ARQUIVO COMPLETO DO COMANDO

from django.core.management.base import BaseCommand
from datetime import date, timedelta
from financeiro.utils.data_utils import (
    listar_feriados_ano, 
    verificar_calendario_bancario,
    is_dia_util_bancario,
    get_nome_feriado,
    calcular_feriados_bancarios,
    proximo_dia_util_bancario
)

class Command(BaseCommand):
    help = 'Verifica e exibe feriados bancários brasileiros'

    def add_arguments(self, parser):
        parser.add_argument(
            '--ano', 
            type=int, 
            help='Ano para listar feriados (ex: --ano 2025)'
        )
        parser.add_argument(
            '--calendario', 
            action='store_true', 
            help='Mostrar calendário do mês atual'
        )
        parser.add_argument(
            '--mes', 
            type=int, 
            choices=range(1, 13),
            help='Mês para mostrar calendário (1-12, usar com --calendario)'
        )
        parser.add_argument(
            '--hoje',
            action='store_true',
            help='Verificar apenas o dia de hoje'
        )

    def handle(self, *args, **options):
        hoje = date.today()
        
        # Cabeçalho
        self.stdout.write("🏦 VERIFICADOR DE FERIADOS BANCÁRIOS")
        self.stdout.write("=" * 60)
        
        if options['hoje']:
            self._verificar_hoje(hoje)
        
        elif options['ano']:
            self._listar_feriados_ano(options['ano'])
        
        elif options['calendario']:
            mes = options.get('mes') or hoje.month
            self._mostrar_calendario_mes(hoje.year, mes)
        
        else:
            # Verificação padrão
            self._verificacao_padrao(hoje)

    def _verificar_hoje(self, hoje):
        """Verifica apenas o dia de hoje"""
        self.stdout.write(f"📅 VERIFICAÇÃO DE HOJE - {hoje.strftime('%d/%m/%Y')}")
        self.stdout.write("-" * 50)
        
        dia_semana = self._nome_dia_semana(hoje)
        self.stdout.write(f"   Data: {hoje.strftime('%d/%m/%Y')} ({dia_semana})")
        
        if is_dia_util_bancario(hoje):
            self.stdout.write("   Status: ✅ Dia útil bancário")
        else:
            if hoje.weekday() >= 5:
                self.stdout.write("   Status: 🔒 Fim de semana")
            else:
                nome_feriado = get_nome_feriado(hoje)
                if nome_feriado:
                    self.stdout.write(f"   Status: 🔒 Feriado bancário - {nome_feriado}")
                else:
                    self.stdout.write("   Status: 🔒 Não é dia útil")
        
        # Próximo dia útil
        if not is_dia_util_bancario(hoje):
            proximo = proximo_dia_util_bancario(hoje + timedelta(days=1))
            self.stdout.write(f"   Próximo dia útil: {proximo.strftime('%d/%m/%Y')}")

    def _listar_feriados_ano(self, ano):
        """Lista todos os feriados do ano"""
        self.stdout.write(f"📅 FERIADOS BANCÁRIOS DE {ano}")
        self.stdout.write("-" * 50)
        
        try:
            feriados = calcular_feriados_bancarios(ano)
            
            if not feriados:
                self.stdout.write("   Nenhum feriado encontrado")
                return
            
            for data_feriado, nome in feriados:
                dia_semana = self._nome_dia_semana(data_feriado)
                
                if "meio expediente" in nome.lower():
                    icone = "⚠️"
                else:
                    icone = "🔒"
                
                self.stdout.write(
                    f"   {icone} {data_feriado.strftime('%d/%m/%Y')} "
                    f"({dia_semana}) - {nome}"
                )
            
            self.stdout.write(f"\n📊 Total: {len(feriados)} feriados bancários")
            
        except Exception as e:
            self.stdout.write(f"❌ Erro ao calcular feriados: {str(e)}")

    def _mostrar_calendario_mes(self, ano, mes):
        """Mostra calendário de um mês específico"""
        try:
            # Validar mês
            if mes < 1 or mes > 12:
                self.stdout.write("❌ Mês deve ser entre 1 e 12")
                return
            
            # Primeiro e último dia do mês
            primeiro_dia = date(ano, mes, 1)
            if mes == 12:
                ultimo_dia = date(ano + 1, 1, 1) - timedelta(days=1)
            else:
                ultimo_dia = date(ano, mes + 1, 1) - timedelta(days=1)
            
            meses = [
                '', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
            ]
            
            self.stdout.write(f"📅 CALENDÁRIO BANCÁRIO - {meses[mes]} {ano}")
            self.stdout.write("-" * 60)
            
            data_atual = primeiro_dia
            total_dias = 0
            dias_uteis = 0
            feriados_encontrados = 0
            
            while data_atual <= ultimo_dia:
                total_dias += 1
                dia_semana = self._nome_dia_semana(data_atual)
                
                if is_dia_util_bancario(data_atual):
                    status = "✅ Dia útil"
                    dias_uteis += 1
                elif data_atual.weekday() >= 5:
                    status = "🔒 Fim de semana"
                else:
                    nome_feriado = get_nome_feriado(data_atual)
                    if nome_feriado:
                        if "meio expediente" in nome_feriado.lower():
                            status = f"⚠️ {nome_feriado}"
                        else:
                            status = f"🔒 {nome_feriado}"
                        feriados_encontrados += 1
                    else:
                        status = "🔒 Não útil"
                
                self.stdout.write(
                    f"   {data_atual.strftime('%d/%m')} ({dia_semana:7}) - {status}"
                )
                
                data_atual += timedelta(days=1)
            
            # Resumo do mês
            self.stdout.write(f"\n📊 RESUMO DE {meses[mes].upper()}:")
            self.stdout.write(f"   📅 Total de dias: {total_dias}")
            self.stdout.write(f"   ✅ Dias úteis bancários: {dias_uteis}")
            self.stdout.write(f"   🔒 Fins de semana/feriados: {total_dias - dias_uteis}")
            self.stdout.write(f"   🏦 Feriados bancários: {feriados_encontrados}")
            
        except Exception as e:
            self.stdout.write(f"❌ Erro ao gerar calendário: {str(e)}")

    def _verificacao_padrao(self, hoje):
        """Verificação padrão quando nenhuma opção específica é dada"""
        # Status de hoje
        self._verificar_hoje(hoje)
        
        # Próximos feriados
        self.stdout.write(f"\n📅 PRÓXIMOS FERIADOS BANCÁRIOS:")
        self.stdout.write("-" * 50)
        
        try:
            feriados_ano = calcular_feriados_bancarios(hoje.year)
            
            # Filtrar apenas feriados futuros
            proximos_feriados = [
                (data, nome) for data, nome in feriados_ano 
                if data >= hoje
            ]
            
            if proximos_feriados:
                # Mostrar próximos 5 feriados
                for data_feriado, nome in proximos_feriados[:5]:
                    dias_restantes = (data_feriado - hoje).days
                    dia_semana = self._nome_dia_semana(data_feriado)
                    
                    if dias_restantes == 0:
                        quando = "HOJE"
                    elif dias_restantes == 1:
                        quando = "AMANHÃ"
                    else:
                        quando = f"em {dias_restantes} dias"
                    
                    if "meio expediente" in nome.lower():
                        icone = "⚠️"
                    else:
                        icone = "🔒"
                    
                    self.stdout.write(
                        f"   {icone} {data_feriado.strftime('%d/%m/%Y')} "
                        f"({dia_semana}) - {nome} ({quando})"
                    )
            else:
                self.stdout.write("   ✅ Nenhum feriado restante neste ano")
            
            # Se estivermos no final do ano, mostrar alguns do próximo
            if hoje.month >= 11:
                self.stdout.write(f"\n📅 PRIMEIROS FERIADOS DE {hoje.year + 1}:")
                feriados_proximo_ano = calcular_feriados_bancarios(hoje.year + 1)
                
                for data_feriado, nome in feriados_proximo_ano[:3]:
                    dia_semana = self._nome_dia_semana(data_feriado)
                    self.stdout.write(
                        f"   🔒 {data_feriado.strftime('%d/%m/%Y')} "
                        f"({dia_semana}) - {nome}"
                    )
        
        except Exception as e:
            self.stdout.write(f"❌ Erro ao buscar próximos feriados: {str(e)}")
        
        # Dicas de uso
        self.stdout.write(f"\n💡 DICAS DE USO:")
        self.stdout.write("-" * 30)
        self.stdout.write(f"   --ano 2025        Ver todos os feriados de 2025")
        self.stdout.write(f"   --calendario      Ver calendário do mês atual")
        self.stdout.write(f"   --calendario --mes 12  Ver calendário de dezembro")
        self.stdout.write(f"   --hoje            Verificar apenas hoje")

    def _nome_dia_semana(self, data):
        """Retorna nome do dia da semana em português"""
        dias = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
        return dias[data.weekday()]

