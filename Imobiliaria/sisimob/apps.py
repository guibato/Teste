from django.apps import AppConfig

class SisimobConfig(AppConfig):
    name = 'sisimob'

    def ready(self):
        # Importa os sinais do core
        import sisimob.signals  # noqa: F401