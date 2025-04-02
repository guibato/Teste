# sisimob/templatetags/custom_filters.py
from django import template
import locale

register = template.Library()

# Definir o filtro customizado para moeda
@register.filter
def currency(value):
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')  # Define o locale para pt_BR
    try:
        return locale.currency(value, grouping=True)  # Formata o valor para moeda com ponto de milhar
    except (ValueError, TypeError):
        return value  # Retorna o valor original se algo der errado


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

@register.filter(name='add_class')
def add_class(value, arg):
    """
    Adiciona uma classe CSS a um campo de formulário
    
    Uso no template: {{ form.campo|add_class:"classe-css" }}
    """
    if hasattr(value, 'as_widget'):
        css_classes = value.field.widget.attrs.get('class', '')
        # Adiciona a nova classe, garantindo que não haja duplicação
        if css_classes:
            css_classes = f"{css_classes} {arg}"
        else:
            css_classes = arg
        return value.as_widget(attrs={'class': css_classes})
    return value