# Em templatetags/despesa_filters.py
from django import template

register = template.Library()

@register.filter
def total_valor(despesas_list):
    return sum(d.valor_total for d in despesas_list)

@register.filter
def count_ativas(despesas_list):
    return sum(1 for d in despesas_list if d.is_ativa)

@register.filter
def count_inativas(despesas_list):
    return sum(1 for d in despesas_list if not d.is_ativa)