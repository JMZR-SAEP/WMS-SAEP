from django.core.management.base import BaseCommand

from apps.notifications.services import enviar_push_lembretes_autorizacoes_atrasadas


class Command(BaseCommand):
    help = "Envia lembretes push agregados para autorizações atrasadas."

    def handle(self, *args, **options):
        sent = enviar_push_lembretes_autorizacoes_atrasadas()
        self.stdout.write(f"Lembretes push enviados para {sent} chefe(s).")
