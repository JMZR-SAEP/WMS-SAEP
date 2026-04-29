from django.core.management.base import BaseCommand

from apps.materials.csv_parser import ScpiCsvParserError
from apps.materials.services import importar_csv_scpi


class Command(BaseCommand):
    help = "Importa carga inicial de materiais e saldos do CSV SCPI."

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_path",
            type=str,
            help="Caminho para o arquivo CSV do SCPI",
        )

    def handle(self, *args, **options):
        csv_path = options["csv_path"]

        try:
            with open(csv_path, "rb") as f:
                conteudo = f.read()
        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f"Arquivo não encontrado: {csv_path}"))
            return
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Erro ao abrir arquivo: {e}"))
            return

        try:
            resultado = importar_csv_scpi(conteudo)
        except ScpiCsvParserError as e:
            self.stderr.write(self.style.ERROR(f"Erro técnico: {e}"))
            return
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Erro ao processar importação: {e}"))
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"Importação concluída: "
                f"{resultado.grupos_criados} grupos, "
                f"{resultado.subgrupos_criados} subgrupos, "
                f"{resultado.materiais_criados} materiais, "
                f"{resultado.estoques_criados} estoques criados."
            )
        )

        if resultado.erros:
            self.stderr.write(self.style.WARNING("Erros encontrados:"))
            for erro in resultado.erros:
                self.stderr.write(self.style.WARNING(f"  - {erro}"))
