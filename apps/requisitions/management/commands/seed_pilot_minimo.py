from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.requisitions.seed_pilot_minimo import carregar_seed_pilot_minimo


class Command(BaseCommand):
    help = "Carrega seed minima oficial do piloto para validacao manual e Playwright."

    def handle(self, *args, **options):
        if not settings.EPHEMERAL_ENVIRONMENT:
            raise CommandError("Seed piloto mínima só pode ser executada em ambiente efêmero.")

        try:
            carregar_seed_pilot_minimo()
        except Exception as exc:
            raise CommandError(f"Erro ao carregar seed piloto minima: {exc}") from exc

        self.stdout.write(self.style.SUCCESS("Seed piloto mínima carregada com sucesso."))
