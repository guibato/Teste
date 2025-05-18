# apps.py
from django.apps import AppConfig


class FinanceiroConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'financeiro'
    verbose_name = 'Gestão Financeira'

    def ready(self):
        import financeiro.signals # Importa os signals quando o app é carregado