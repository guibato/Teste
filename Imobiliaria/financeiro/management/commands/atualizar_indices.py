from django.core.management.base import BaseCommand
from financeiro.utils.atualizar_indices import atualizar_indices_inflacao

class Command(BaseCommand):
    help = 'Atualiza os índices de inflação IPCA e IGPM a partir de fontes oficiais'

    def handle(self, *args, **kwargs):
        self.stdout.write("Atualizando índices de inflação...")
        try:
            atualizar_indices_inflacao()
            self.stdout.write(self.style.SUCCESS("Índices atualizados com sucesso!"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Erro ao atualizar índices: {e}"))
