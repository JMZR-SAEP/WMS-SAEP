import traceback

from django.core.management.base import BaseCommand, CommandError

from apps.notifications.services import enviar_push_lembretes_autorizacoes_atrasadas


class Command(BaseCommand):
    help = "Envia lembretes push agregados para autorizações atrasadas."

    def handle(self, *args, **options):
        try:
            sent = enviar_push_lembretes_autorizacoes_atrasadas()
        except Exception as exc:
            self.stderr.write(
                self.style.ERROR(
                    f"Falha ao enviar lembretes push agregados:\n{traceback.format_exc()}"
                )
            )
            raise CommandError("Falha ao enviar lembretes push agregados.") from exc

        self.stdout.write(self.style.SUCCESS(f"Lembretes push enviados para {sent} chefe(s)."))
