"""
Utilitários para formatação de valores monetários e datas para o sistema de administração imobiliária.
"""

from decimal import Decimal
from datetime import date, datetime

def format_currency(value):
    """
    Formata um valor decimal como moeda (R$).

    Args:
        value: Valor decimal ou numérico a ser formatado

    Returns:
        str: Valor formatado como moeda brasileira
    """
    if value is None:
        return "R$ 0,00"

    # Garantir que o valor é um Decimal
    if not isinstance(value, Decimal):
        value = Decimal(str(value))

    # Formatar com separador de milhares e duas casas decimais
    # Formato brasileiro: R$ 1.234,56
    formatted = f"R$ {value:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

    return formatted

def format_date(date_value, format_str="%d/%m/%Y"):
    """
    Formata uma data no padrão brasileiro.

    Args:
        date_value: Objeto date ou datetime
        format_str: String de formato (padrão: dia/mês/ano)

    Returns:
        str: Data formatada
    """
    if not date_value:
        return ""

    if isinstance(date_value, str):
        try:
            date_value = datetime.strptime(date_value, "%Y-%m-%d").date()
        except ValueError:
            return date_value

    return date_value.strftime(format_str)

def format_percentage(value):
    """
    Formata um valor decimal como percentual.

    Args:
        value: Valor decimal ou numérico a ser formatado

    Returns:
        str: Valor formatado como percentual
    """
    if value is None:
        return "0%"

    # Garantir que o valor é um Decimal
    if not isinstance(value, Decimal):
        value = Decimal(str(value))

    # Formatar com duas casas decimais
    return f"{value:.2f}%".replace('.', ',')
