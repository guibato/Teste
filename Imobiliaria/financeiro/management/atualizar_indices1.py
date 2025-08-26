from django.core.management.base import BaseCommand
from financeiro.utils.inflacao import atualizar_indices_inflacao

class Command(BaseCommand):
    help = 'Atualiza os índices de inflação (IPCA/IGPM) no banco de dados'

    def handle(self, *args, **kwargs):
        try:
            atualizar_indices_inflacao()
            self.stdout.write(self.style.SUCCESS("Índices atualizados com sucesso!"))
        except Exception as e:
            self.stderr.write(f"Erro: {str(e)}")