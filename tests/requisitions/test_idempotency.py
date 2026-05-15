import hashlib
from unittest.mock import MagicMock, patch

import pytest
from django.db import IntegrityError

from apps.requisitions.idempotency import get_or_create_idempotency_record
from apps.requisitions.models import Requisicao, RequisicaoIdempotencyKey, StatusIdempotencia
from apps.users.models import PapelChoices, Setor, User

OPERATION_FULFILL = "requisitions_fulfill"
OPERATION_PICKUP = "requisitions_pickup"


def _hash(value: str = "payload") -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _criar_setor(nome: str, chefe_matricula: str) -> Setor:
    chefe = User.objects.create(
        matricula_funcional=chefe_matricula,
        nome_completo=f"Chefe {nome}",
        papel=PapelChoices.CHEFE_SETOR,
        is_active=True,
    )
    setor = Setor.objects.create(nome=nome, chefe_responsavel=chefe)
    chefe.setor = setor
    chefe.save(update_fields=["setor"])
    return setor


def _criar_usuario(matricula: str, nome: str, setor: Setor) -> User:
    return User.objects.create(
        matricula_funcional=matricula,
        nome_completo=nome,
        papel=PapelChoices.SOLICITANTE,
        setor=setor,
        is_active=True,
    )


def _criar_requisicao(criador: User) -> Requisicao:
    return Requisicao.objects.create(
        criador=criador,
        beneficiario=criador,
        status="rascunho",
        observacao="",
    )


@pytest.mark.django_db
class TestGetOrCreateIdempotencyRecord:
    def setup_method(self):
        self.setor = _criar_setor("Almox", "000")
        self.usuario = _criar_usuario("001", "Solicitante A", self.setor)
        self.outro_usuario = _criar_usuario("002", "Solicitante B", self.setor)
        self.requisicao = _criar_requisicao(self.usuario)

    def test_primeira_chamada_cria_registro_in_progress(self):
        registro, criado = get_or_create_idempotency_record(
            usuario=self.usuario,
            requisicao=self.requisicao,
            operation=OPERATION_FULFILL,
            key="chave-1",
            payload_hash=_hash(),
        )

        assert criado is True
        assert registro.status == StatusIdempotencia.IN_PROGRESS
        assert registro.payload_hash == _hash()
        assert RequisicaoIdempotencyKey.objects.count() == 1

    def test_segunda_chamada_mesma_chave_retorna_existente(self):
        get_or_create_idempotency_record(
            usuario=self.usuario,
            requisicao=self.requisicao,
            operation=OPERATION_FULFILL,
            key="chave-1",
            payload_hash=_hash(),
        )
        registro, criado = get_or_create_idempotency_record(
            usuario=self.usuario,
            requisicao=self.requisicao,
            operation=OPERATION_FULFILL,
            key="chave-1",
            payload_hash=_hash(),
        )

        assert criado is False
        assert RequisicaoIdempotencyKey.objects.count() == 1

    def test_operations_diferentes_nao_colidem(self):
        _, criado_a = get_or_create_idempotency_record(
            usuario=self.usuario,
            requisicao=self.requisicao,
            operation=OPERATION_FULFILL,
            key="chave-x",
            payload_hash=_hash("a"),
        )
        _, criado_b = get_or_create_idempotency_record(
            usuario=self.usuario,
            requisicao=self.requisicao,
            operation=OPERATION_PICKUP,
            key="chave-x",
            payload_hash=_hash("b"),
        )

        assert criado_a is True
        assert criado_b is True
        assert RequisicaoIdempotencyKey.objects.count() == 2

    def test_usuarios_diferentes_nao_colidem(self):
        _, criado_a = get_or_create_idempotency_record(
            usuario=self.usuario,
            requisicao=self.requisicao,
            operation=OPERATION_FULFILL,
            key="chave-y",
            payload_hash=_hash(),
        )
        _, criado_b = get_or_create_idempotency_record(
            usuario=self.outro_usuario,
            requisicao=self.requisicao,
            operation=OPERATION_FULFILL,
            key="chave-y",
            payload_hash=_hash(),
        )

        assert criado_a is True
        assert criado_b is True
        assert RequisicaoIdempotencyKey.objects.count() == 2

    def test_payload_hash_preservado_no_registro(self):
        hash_esperado = _hash("meu-payload-especifico")
        registro, _ = get_or_create_idempotency_record(
            usuario=self.usuario,
            requisicao=self.requisicao,
            operation=OPERATION_FULFILL,
            key="chave-hash",
            payload_hash=hash_esperado,
        )

        assert registro.payload_hash == hash_esperado

    def test_fallback_integrityerror_retorna_registro_existente(self):
        hash_original = _hash("race")
        registro_existente = RequisicaoIdempotencyKey.objects.create(
            usuario=self.usuario,
            requisicao=self.requisicao,
            endpoint=OPERATION_FULFILL,
            key="chave-race",
            payload_hash=hash_original,
            status=StatusIdempotencia.IN_PROGRESS,
        )

        mock_qs = MagicMock()
        mock_qs.get_or_create.side_effect = IntegrityError("simulated race condition")
        mock_qs.get.return_value = registro_existente

        with patch.object(
            RequisicaoIdempotencyKey.objects,
            "select_for_update",
            return_value=mock_qs,
        ):
            registro, criado = get_or_create_idempotency_record(
                usuario=self.usuario,
                requisicao=self.requisicao,
                operation=OPERATION_FULFILL,
                key="chave-race",
                payload_hash=hash_original,
            )

        assert criado is False
        assert registro.pk == registro_existente.pk
        assert registro.payload_hash == hash_original
        assert registro.status == StatusIdempotencia.IN_PROGRESS
        assert RequisicaoIdempotencyKey.objects.count() == 1
