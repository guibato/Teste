# sisimob/templatetags/custom_filters.py
from django import template

register = template.Library()

@register.filter(name='replace')
def replace(value, arg):
    """
    Substitui uma substring por outra.
    Uso: {{ valor|replace:".,," }}
    """
    from_char, to_char = arg.split(',')
    return str(value).replace(from_char, to_char)

@register.filter
def format_decimal(value):
    """
    Formata um número decimal para usar vírgula como separador decimal.
    Exemplo: 5.00 → 5,00
    """
    return f"{value:.2f}".replace('.', ',')