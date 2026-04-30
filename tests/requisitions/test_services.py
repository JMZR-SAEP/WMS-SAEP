import pytest

from apps.requisitions.services import _gerar_numero_publico


@pytest.mark.django_db(transaction=True)
class TestSequenciaNumeroRequisicaoService:
    def test_gera_numeros_incrementais_no_mesmo_ano(self):
        primeiro = _gerar_numero_publico(ano=2026)
        segundo = _gerar_numero_publico(ano=2026)

        assert primeiro == "REQ-2026-000001"
        assert segundo == "REQ-2026-000002"

    def test_reinicia_sequencia_em_novo_ano(self):
        numero_2026 = _gerar_numero_publico(ano=2026)
        numero_2027 = _gerar_numero_publico(ano=2027)

        assert numero_2026 == "REQ-2026-000001"
        assert numero_2027 == "REQ-2027-000001"
