# financeiro/apps.py
from django.apps import AppConfig


class FinanceiroConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'financeiro'
    
    def ready(self):
        """
        🚀 Importa os signals quando a app é carregada
        """
        try:
            import financeiro.signals  # Importa os signals
            print("✅ Signals de repasse carregados com sucesso!")
        except ImportError as e:
            print(f"⚠️ Erro ao carregar signals: {e}")
        except Exception as e:
            print(f"❌ Erro inesperado ao carregar signals: {e}")