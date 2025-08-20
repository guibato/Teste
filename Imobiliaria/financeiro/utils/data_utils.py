# ================================================================
# FERIADOS BANCÁRIOS BRASILEIROS COMPLETOS
# financeiro/utils/data_utils.py (VERSÃO ATUALIZADA)
# ================================================================

from datetime import date, timedelta, datetime
from dateutil.easter import easter
import calendar

def calcular_feriados_bancarios(ano):
    """
    Calcula todos os feriados bancários para um ano específico
    Incluindo feriados fixos e móveis
    """
    feriados = []
    
    # ================================================================
    # FERIADOS FIXOS NACIONAIS
    # ================================================================
    feriados_fixos = [
        (1, 1, "Confraternização Universal"),
        (4, 21, "Tiradentes"),
        (5, 1, "Dia do Trabalhador"),
        (9, 7, "Independência do Brasil"),
        (10, 12, "Nossa Senhora Aparecida"),
        (11, 2, "Finados"),
        (11, 15, "Proclamação da República"),
        (12, 25, "Natal"),
    ]
    
    for mes, dia, nome in feriados_fixos:
        feriados.append((date(ano, mes, dia), nome))
    
    # ================================================================
    # FERIADOS MÓVEIS (baseados na Páscoa)
    # ================================================================
    pascoa = easter(ano)
    
    # Carnaval (47 e 48 dias antes da Páscoa)
    segunda_carnaval = pascoa - timedelta(days=48)
    terca_carnaval = pascoa - timedelta(days=47)
    
    # Quarta-feira de Cinzas (46 dias antes da Páscoa) - meio expediente bancário
    quarta_cinzas = pascoa - timedelta(days=46)
    
    # Sexta-feira Santa (2 dias antes da Páscoa)
    sexta_santa = pascoa - timedelta(days=2)
    
    # Corpus Christi (60 dias após a Páscoa)
    corpus_christi = pascoa + timedelta(days=60)
    
    feriados_moveis = [
        (segunda_carnaval, "Segunda-feira de Carnaval"),
        (terca_carnaval, "Terça-feira de Carnaval"),
        (quarta_cinzas, "Quarta-feira de Cinzas"),  # Meio expediente
        (sexta_santa, "Sexta-feira Santa"),
        (corpus_christi, "Corpus Christi"),
    ]
    
    feriados.extend(feriados_moveis)
    
    # ================================================================
    # FERIADOS BANCÁRIOS ESPECÍFICOS
    # ================================================================
    
    # Véspera de Natal (24/12) - meio expediente se cair em dia útil
    vespera_natal = date(ano, 12, 24)
    if vespera_natal.weekday() < 5:  # Segunda a sexta
        feriados.append((vespera_natal, "Véspera de Natal (meio expediente)"))
    
    # Véspera de Ano Novo (31/12) - meio expediente se cair em dia útil
    vespera_ano_novo = date(ano, 12, 31)
    if vespera_ano_novo.weekday() < 5:  # Segunda a sexta
        feriados.append((vespera_ano_novo, "Véspera de Ano Novo (meio expediente)"))
    
    # ================================================================
    # PONTES E EMENDAS (opcional - adaptar conforme política)
    # ================================================================
    
    # Verificar se há feriados que caem em terça ou quinta
    # criando pontes naturais (implementação opcional)
    
    return sorted(feriados, key=lambda x: x[0])

def is_feriado_bancario(data):
    """
    Verifica se uma data é feriado bancário
    """
    # Cache dos feriados do ano para evitar recálculos
    if not hasattr(is_feriado_bancario, '_cache'):
        is_feriado_bancario._cache = {}
    
    ano = data.year
    if ano not in is_feriado_bancario._cache:
        feriados_ano = calcular_feriados_bancarios(ano)
        is_feriado_bancario._cache[ano] = [f[0] for f in feriados_ano]
    
    return data in is_feriado_bancario._cache[ano]

def get_nome_feriado(data):
    """
    Retorna o nome do feriado se a data for feriado bancário
    """
    ano = data.year
    feriados_ano = calcular_feriados_bancarios(ano)
    
    for data_feriado, nome in feriados_ano:
        if data_feriado == data:
            return nome
    
    return None

def is_dia_util_bancario(data):
    """
    Verifica se uma data é dia útil bancário
    (segunda a sexta, exceto feriados bancários)
    """
    # Verificar se é fim de semana
    if data.weekday() >= 5:  # 5=sábado, 6=domingo
        return False
    
    # Verificar se é feriado bancário
    if is_feriado_bancario(data):
        return False
    
    return True

def is_meio_expediente_bancario(data):
    """
    Verifica se é meio expediente bancário
    """
    nome_feriado = get_nome_feriado(data)
    if nome_feriado:
        return "meio expediente" in nome_feriado.lower()
    return False

def dia_util_bancario_anterior(data_base, dias_antes):
    """
    Calcula o dia útil bancário anterior considerando apenas dias úteis bancários
    Versão específica para bancos
    """
    if dias_antes == 0:
        # Para o dia do vencimento, usar o próprio dia se for útil
        # ou o último dia útil anterior
        data_atual = data_base
        while not is_dia_util_bancario(data_atual):
            data_atual -= timedelta(days=1)
        return data_atual
    
    # Para outros casos, contar apenas dias úteis bancários
    data_atual = data_base
    dias_contados = 0
    
    while dias_contados < dias_antes:
        data_atual -= timedelta(days=1)
        if is_dia_util_bancario(data_atual):
            dias_contados += 1
    
    return data_atual

def proximo_dia_util_bancario(data_base):
    """
    Retorna o próximo dia útil bancário a partir de uma data
    """
    data_atual = data_base
    while not is_dia_util_bancario(data_atual):
        data_atual += timedelta(days=1)
    return data_atual

def listar_feriados_ano(ano=None):
    """
    Lista todos os feriados bancários de um ano
    """
    if ano is None:
        ano = date.today().year
    
    feriados = calcular_feriados_bancarios(ano)
    
    print(f"📅 FERIADOS BANCÁRIOS {ano}")
    print("=" * 50)
    
    for data_feriado, nome in feriados:
        dia_semana = _nome_dia_semana(data_feriado)
        print(f"{data_feriado.strftime('%d/%m/%Y')} ({dia_semana}) - {nome}")
    
    return feriados

def _nome_dia_semana(data):
    """Retorna nome do dia da semana em português"""
    dias = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
    return dias[data.weekday()]

def verificar_calendario_bancario(data_inicio, data_fim):
    """
    Verifica o calendário bancário entre duas datas
    """
    print(f"📅 CALENDÁRIO BANCÁRIO: {data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}")
    print("=" * 70)
    
    data_atual = data_inicio
    total_dias = 0
    dias_uteis = 0
    feriados_encontrados = 0
    
    while data_atual <= data_fim:
        total_dias += 1
        
        if is_dia_util_bancario(data_atual):
            status = "✅ Dia útil"
            dias_uteis += 1
        elif data_atual.weekday() >= 5:
            status = "🔒 Fim de semana"
        else:
            nome_feriado = get_nome_feriado(data_atual)
            if "meio expediente" in nome_feriado.lower():
                status = f"⚠️ {nome_feriado}"
            else:
                status = f"🔒 {nome_feriado}"
            feriados_encontrados += 1
        
        dia_semana = _nome_dia_semana(data_atual)
        print(f"{data_atual.strftime('%d/%m/%Y')} ({dia_semana}) - {status}")
        
        data_atual += timedelta(days=1)
    
    print(f"\n📊 RESUMO:")
    print(f"   Total de dias: {total_dias}")
    print(f"   Dias úteis bancários: {dias_uteis}")
    print(f"   Feriados/fins de semana: {total_dias - dias_uteis}")
    print(f"   Feriados bancários: {feriados_encontrados}")

# ================================================================
# FUNÇÕES DE COMPATIBILIDADE (para manter código existente)
# ================================================================

# Manter funções originais para compatibilidade
def is_feriado(data):
    """Alias para is_feriado_bancario (compatibilidade)"""
    return is_feriado_bancario(data)

def is_dia_util(data):
    """Alias para is_dia_util_bancario (compatibilidade)"""
    return is_dia_util_bancario(data)

def dia_util_anterior(data_base, dias_antes):
    """Alias para dia_util_bancario_anterior (compatibilidade)"""
    return dia_util_bancario_anterior(data_base, dias_antes)

def proximo_dia_util(data_base):
    """Alias para proximo_dia_util_bancario (compatibilidade)"""
    return proximo_dia_util_bancario(data_base)

# ================================================================
# COMANDO PARA TESTAR FERIADOS
# financeiro/management/commands/verificar_feriados_bancarios.py
# ================================================================

