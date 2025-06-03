# financeiro/templatetags/financeiro_filters.py
"""
Filtros personalizados para templates do módulo financeiro
"""

from django import template

register = template.Library()

@register.filter
def mes_nome(mes_numero):
    """
    Converte número do mês para nome em português
    """
    meses = {
        1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
        5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
        9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
    }
    return meses.get(mes_numero, f'Mês {mes_numero}')

@register.filter
def split_string(value, delimiter):
    """
    Split uma string usando o delimitador especificado
    """
    if value:
        return value.split(delimiter)
    return []

@register.filter
def currency_format(value):
    """
    Formatar valor como moeda brasileira
    """
    if value is None:
        return 'R$ 0,00'
    
    try:
        # Converter para float se necessário
        if isinstance(value, str):
            value = float(value.replace(',', '.'))
        
        # Formatar como moeda
        return f'R$ {value:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    except (ValueError, TypeError):
        return 'R$ 0,00'

@register.filter
def status_badge_class(status):
    """
    Retorna a classe CSS para o badge de status
    """
    classes = {
        'pendente': 'status-pendente',
        'paga': 'status-paga', 
        'atrasada': 'status-atrasada',
        'cancelada': 'status-cancelada'
    }
    return classes.get(status, 'status-pendente')

@register.filter
def status_display(status):
    """
    Retorna o texto de exibição para o status
    """
    displays = {
        'pendente': 'Pendente',
        'paga': 'Paga',
        'atrasada': 'Atrasada', 
        'cancelada': 'Cancelada'
    }
    return displays.get(status, status.title())

@register.filter
def pluralize_pt(value, forms):
    """
    Pluralização em português
    Usage: {{ dias|pluralize_pt:"dia,dias" }}
    """
    if not forms or ',' not in forms:
        return ''
        
    singular, plural = forms.split(',', 1)
    
    try:
        num = int(value)
        return singular if num == 1 else plural
    except (ValueError, TypeError):
        return plural

@register.simple_tag
def query_string(request, **kwargs):
    """
    Gera query string preservando parâmetros existentes
    Usage: {% query_string request page=2 %}
    """
    query_dict = request.GET.copy()
    
    for key, value in kwargs.items():
        if value is None:
            query_dict.pop(key, None)
        else:
            query_dict[key] = value
    
    return query_dict.urlencode()

@register.inclusion_tag('financeiro/includes/status_badge.html')
def status_badge(status, size='sm'):
    """
    Renderiza badge de status
    Usage: {% status_badge cobranca.status %}
    """
    return {
        'status': status,
        'status_class': status_badge_class(status),
        'status_text': status_display(status),
        'size': size
    }

@register.inclusion_tag('financeiro/includes/currency_display.html')
def currency_display(value, label='', highlight=False):
    """
    Renderiza valor monetário formatado
    Usage: {% currency_display cobranca.valor_total "Total" True %}
    """
    return {
        'value': value,
        'formatted_value': currency_format(value),
        'label': label,
        'highlight': highlight
    }

@register.filter
def subtract(value, arg):
    """
    Subtrai arg de value
    """
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def multiply(value, arg):
    """
    Multiplica value por arg
    """
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def divide(value, arg):
    """
    Divide value por arg
    """
    try:
        arg_float = float(arg)
        if arg_float == 0:
            return 0
        return float(value) / arg_float
    except (ValueError, TypeError):
        return 0

@register.filter
def percentage(value, total):
    """
    Calcula percentual de value em relação ao total
    """
    try:
        total_float = float(total)
        if total_float == 0:
            return 0
        return (float(value) / total_float) * 100
    except (ValueError, TypeError):
        return 0