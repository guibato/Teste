# financeiro/templatetags/reajuste_extras.py

from django import template
from decimal import Decimal

register = template.Library()

@register.filter
def subtract(value, arg):
    """
    Subtrai o argumento do valor
    """
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def multiply(value, arg):
    """
    Multiplica o valor pelo argumento
    """
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def divide(value, arg):
    """
    Divide o valor pelo argumento
    """
    try:
        if float(arg) == 0:
            return 0
        return float(value) / float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def percentage(value, total):
    """
    Calcula a porcentagem do valor em relação ao total
    """
    try:
        if float(total) == 0:
            return 0
        return (float(value) / float(total)) * 100
    except (ValueError, TypeError):
        return 0

@register.filter
def currency(value):
    """
    Formata um valor como moeda brasileira
    """
    try:
        return f"R$ {float(value):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except (ValueError, TypeError):
        return "R$ 0,00"

@register.filter
def variation_class(value):
    """
    Retorna a classe CSS baseada na variação
    """
    try:
        val = float(value)
        if val > 0:
            return "text-green-600"
        elif val < 0:
            return "text-red-600"
        else:
            return "text-gray-600"
    except (ValueError, TypeError):
        return "text-gray-600"