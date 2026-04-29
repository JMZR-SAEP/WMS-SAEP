import pytest
from django.core.management import call_command
from django.core.management.base import CommandError


@pytest.mark.django_db
class TestImportarScpiCommand:
    def test_arquivo_inexistente_levanta_command_error(self):
        with pytest.raises(CommandError, match="Arquivo não encontrado"):
            call_command("importar_scpi", "/caminho/inexistente/scpi.csv")

    def test_csv_invalido_levanta_command_error(self, tmp_path):
        csv_path = tmp_path / "scpi.csv"
        csv_path.write_bytes(b"arquivo_invalido")

        with pytest.raises(CommandError, match="Erro técnico"):
            call_command("importar_scpi", str(csv_path))
