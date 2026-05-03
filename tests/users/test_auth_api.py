import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.users.models import PapelChoices, Setor, User


@pytest.mark.django_db
class TestAuthAPI:
    @staticmethod
    def _criar_usuario_com_setor(*, matricula: str = "10001") -> User:
        user = User.objects.create_user(
            matricula_funcional=matricula,
            password="senha-segura-123",
            nome_completo="Usuario Auth",
            papel=PapelChoices.CHEFE_SETOR,
            is_active=True,
        )
        setor = Setor.objects.create(nome=f"Setor {matricula}", chefe_responsavel=user)
        user.setor = setor
        user.save(update_fields=["setor"])
        return user

    @staticmethod
    def _csrf_client():
        client = APIClient(enforce_csrf_checks=True)
        csrf_response = client.get(reverse("auth-csrf"))
        return client, csrf_response.data["csrf_token"]

    @staticmethod
    def _criar_setor(*, nome: str, chefe: User, is_active: bool = True) -> Setor:
        return Setor.objects.create(nome=nome, chefe_responsavel=chefe, is_active=is_active)

    @classmethod
    def _criar_usuario(
        cls,
        *,
        matricula: str,
        nome_completo: str,
        papel: str = PapelChoices.SOLICITANTE,
        setor: Setor | None = None,
        is_active: bool = True,
        is_superuser: bool = False,
    ) -> User:
        user = User.objects.create_user(
            matricula_funcional=matricula,
            password="senha-segura-123",
            nome_completo=nome_completo,
            papel=papel,
            setor=setor,
            is_active=is_active,
            is_superuser=is_superuser,
        )
        return user

    def test_me_sem_sessao_valida_retorna_401(self):
        client = APIClient()

        response = client.get(reverse("auth-me"))

        assert response.status_code == 401
        assert response.data["error"]["code"] == "not_authenticated"

    def test_me_com_sessao_valida_retorna_payload_canonico(self):
        user = self._criar_usuario_com_setor()
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get(reverse("auth-me"))

        assert response.status_code == 200
        assert response.data == {
            "id": user.id,
            "matricula_funcional": "10001",
            "nome_completo": "Usuario Auth",
            "papel": PapelChoices.CHEFE_SETOR,
            "setor": {
                "id": user.setor_id,
                "nome": "Setor 10001",
            },
            "is_authenticated": True,
        }

    def test_csrf_retorna_token_e_cookie(self):
        client = APIClient()

        response = client.get(reverse("auth-csrf"))

        assert response.status_code == 200
        assert response.data["csrf_token"]
        assert "csrftoken" in response.cookies

    def test_login_com_matricula_e_senha_validas_cria_sessao_e_retorna_payload(self):
        user = self._criar_usuario_com_setor()
        client, csrf_token = self._csrf_client()

        response = client.post(
            reverse("auth-login"),
            {
                "matricula_funcional": "10001",
                "password": "senha-segura-123",
            },
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        assert response.status_code == 200
        assert response.data["id"] == user.id
        assert response.data["matricula_funcional"] == "10001"
        assert response.data["is_authenticated"] is True

        me_response = client.get(reverse("auth-me"))
        assert me_response.status_code == 200
        assert me_response.data["id"] == user.id

    def test_login_com_credenciais_invalidas_retorna_401(self):
        self._criar_usuario_com_setor()
        client, csrf_token = self._csrf_client()

        response = client.post(
            reverse("auth-login"),
            {
                "matricula_funcional": "10001",
                "password": "senha-invalida",
            },
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        assert response.status_code == 401
        assert response.data["error"]["code"] == "authentication_failed"

    def test_login_com_usuario_inativo_retorna_401(self):
        user = self._criar_usuario_com_setor()
        user.is_active = False
        user.save(update_fields=["is_active"])
        client, csrf_token = self._csrf_client()

        response = client.post(
            reverse("auth-login"),
            {
                "matricula_funcional": "10001",
                "password": "senha-segura-123",
            },
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        assert response.status_code == 401
        assert response.data["error"]["code"] == "authentication_failed"

    def test_login_sem_csrf_valido_retorna_403(self):
        self._criar_usuario_com_setor()
        client = APIClient(enforce_csrf_checks=True)

        response = client.post(
            reverse("auth-login"),
            {
                "matricula_funcional": "10001",
                "password": "senha-segura-123",
            },
            format="json",
        )

        assert response.status_code == 403

    def test_logout_com_sessao_valida_retorna_204_e_invalida_sessao(self):
        self._criar_usuario_com_setor()
        client, csrf_token = self._csrf_client()
        login_response = client.post(
            reverse("auth-login"),
            {
                "matricula_funcional": "10001",
                "password": "senha-segura-123",
            },
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        assert login_response.status_code == 200
        csrf_token = client.cookies["csrftoken"].value

        logout_response = client.post(
            reverse("auth-logout"),
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        assert logout_response.status_code == 204
        me_response = client.get(reverse("auth-me"))
        assert me_response.status_code == 401

    def test_logout_sem_sessao_valida_retorna_204(self):
        client, csrf_token = self._csrf_client()

        response = client.post(
            reverse("auth-logout"),
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        assert response.status_code == 204

    def test_logout_sem_csrf_valido_retorna_403(self):
        client = APIClient(enforce_csrf_checks=True)

        response = client.post(reverse("auth-logout"), format="json")

        assert response.status_code == 403

    def test_login_sem_campos_obrigatorios_retorna_400(self):
        client, csrf_token = self._csrf_client()

        response = client.post(
            reverse("auth-login"),
            {},  # payload vazio
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        assert response.status_code == 400
        assert response.data["error"]["code"] == "validation_error"

    def test_beneficiary_lookup_para_auxiliar_setor_retorna_apenas_mesmo_setor_ativo(self):
        chefe_ti = self._criar_usuario(
            matricula="20001",
            nome_completo="Chefe TI",
            papel=PapelChoices.CHEFE_SETOR,
        )
        setor_ti = self._criar_setor(nome="TI", chefe=chefe_ti)
        chefe_ti.setor = setor_ti
        chefe_ti.save(update_fields=["setor"])

        chefe_rh = self._criar_usuario(
            matricula="20002",
            nome_completo="Chefe RH",
            papel=PapelChoices.CHEFE_SETOR,
        )
        setor_rh = self._criar_setor(nome="RH", chefe=chefe_rh)
        chefe_rh.setor = setor_rh
        chefe_rh.save(update_fields=["setor"])

        ator = self._criar_usuario(
            matricula="20003",
            nome_completo="Auxiliar TI",
            papel=PapelChoices.AUXILIAR_SETOR,
            setor=setor_ti,
        )
        beneficiario_mesmo_setor = self._criar_usuario(
            matricula="20004",
            nome_completo="Ana TI",
            setor=setor_ti,
        )
        self._criar_usuario(
            matricula="20005",
            nome_completo="Ana RH",
            setor=setor_rh,
        )
        self._criar_usuario(
            matricula="20006",
            nome_completo="Ana TI Inativa",
            setor=setor_ti,
            is_active=False,
        )

        client = APIClient()
        client.force_authenticate(user=ator)

        response = client.get(reverse("user-beneficiary-lookup"), {"q": "Ana"})

        assert response.status_code == 200
        assert response.data == [
            {
                "id": beneficiario_mesmo_setor.id,
                "nome_completo": "Ana TI",
                "matricula_funcional": "20004",
                "setor": {
                    "id": setor_ti.id,
                    "nome": "TI",
                },
            }
        ]

    def test_beneficiary_lookup_para_solicitante_retorna_apenas_o_proprio_usuario(self):
        chefe_ti = self._criar_usuario(
            matricula="21001",
            nome_completo="Chefe TI 2",
            papel=PapelChoices.CHEFE_SETOR,
        )
        setor_ti = self._criar_setor(nome="TI 2", chefe=chefe_ti)
        chefe_ti.setor = setor_ti
        chefe_ti.save(update_fields=["setor"])

        ator = self._criar_usuario(
            matricula="21002",
            nome_completo="Ana Solicitante",
            papel=PapelChoices.SOLICITANTE,
            setor=setor_ti,
        )
        self._criar_usuario(
            matricula="21003",
            nome_completo="Ana Colega",
            papel=PapelChoices.SOLICITANTE,
            setor=setor_ti,
        )

        client = APIClient()
        client.force_authenticate(user=ator)

        response = client.get(reverse("user-beneficiary-lookup"), {"q": "Ana"})

        assert response.status_code == 200
        assert response.data == [
            {
                "id": ator.id,
                "nome_completo": "Ana Solicitante",
                "matricula_funcional": "21002",
                "setor": {
                    "id": setor_ti.id,
                    "nome": "TI 2",
                },
            }
        ]

    def test_beneficiary_lookup_para_solicitante_sem_setor_retorna_lista_vazia(self):
        ator = self._criar_usuario(
            matricula="21101",
            nome_completo="Ana Sem Setor",
            papel=PapelChoices.SOLICITANTE,
            setor=None,
        )

        client = APIClient()
        client.force_authenticate(user=ator)

        response = client.get(reverse("user-beneficiary-lookup"), {"q": "Ana"})

        assert response.status_code == 200
        assert response.data == []

    def test_beneficiary_lookup_para_chefe_setor_filtra_por_setor_responsavel(self):
        chefe_ti = self._criar_usuario(
            matricula="21501",
            nome_completo="Chefe TI Lookup",
            papel=PapelChoices.CHEFE_SETOR,
        )
        setor_ti = self._criar_setor(nome="TI Lookup", chefe=chefe_ti)
        chefe_ti.setor = setor_ti
        chefe_ti.save(update_fields=["setor"])

        chefe_rh = self._criar_usuario(
            matricula="21502",
            nome_completo="Chefe RH Lookup",
            papel=PapelChoices.CHEFE_SETOR,
        )
        setor_rh = self._criar_setor(nome="RH Lookup", chefe=chefe_rh)
        chefe_rh.setor = setor_rh
        chefe_rh.save(update_fields=["setor"])

        beneficiario_mesmo_setor = self._criar_usuario(
            matricula="21503",
            nome_completo="Bruno TI",
            setor=setor_ti,
        )
        self._criar_usuario(
            matricula="21504",
            nome_completo="Bruno RH",
            setor=setor_rh,
        )
        self._criar_usuario(
            matricula="21505",
            nome_completo="Bruno TI Inativo",
            setor=setor_ti,
            is_active=False,
        )

        client = APIClient()
        client.force_authenticate(user=chefe_ti)

        response = client.get(reverse("user-beneficiary-lookup"), {"q": "Bruno"})

        assert response.status_code == 200
        assert response.data == [
            {
                "id": beneficiario_mesmo_setor.id,
                "nome_completo": "Bruno TI",
                "matricula_funcional": "21503",
                "setor": {
                    "id": setor_ti.id,
                    "nome": "TI Lookup",
                },
            }
        ]

    def test_beneficiary_lookup_para_chefe_setor_sem_setor_responsavel_retorna_lista_vazia(self):
        chefe_sem_setor = self._criar_usuario(
            matricula="21601",
            nome_completo="Chefe Sem Setor",
            papel=PapelChoices.CHEFE_SETOR,
            setor=None,
        )

        client = APIClient()
        client.force_authenticate(user=chefe_sem_setor)

        response = client.get(reverse("user-beneficiary-lookup"), {"q": "Bruno"})

        assert response.status_code == 200
        assert response.data == []

    def test_beneficiary_lookup_para_almoxarifado_ordenado_por_relevancia_simples(self):
        chefe_alm = self._criar_usuario(
            matricula="22001",
            nome_completo="Chefe Almox",
            papel=PapelChoices.CHEFE_ALMOXARIFADO,
        )
        setor_alm = self._criar_setor(nome="Almoxarifado", chefe=chefe_alm)
        chefe_alm.setor = setor_alm
        chefe_alm.save(update_fields=["setor"])

        chefe_obras = self._criar_usuario(
            matricula="22002",
            nome_completo="Chefe Obras",
            papel=PapelChoices.CHEFE_SETOR,
        )
        setor_obras = self._criar_setor(nome="Obras", chefe=chefe_obras)
        chefe_obras.setor = setor_obras
        chefe_obras.save(update_fields=["setor"])

        ator = self._criar_usuario(
            matricula="22003",
            nome_completo="Auxiliar Almox",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor_alm,
        )
        self._criar_usuario(
            matricula="22004",
            nome_completo="Mariana Obras",
            setor=setor_obras,
        )
        self._criar_usuario(
            matricula="22005",
            nome_completo="Ana Paula",
            setor=setor_obras,
        )
        self._criar_usuario(
            matricula="22006",
            nome_completo="Ana Setor Inativo",
            setor=self._criar_setor(
                nome="Setor Inativo",
                chefe=self._criar_usuario(
                    matricula="22007",
                    nome_completo="Chefe Inativo",
                    papel=PapelChoices.CHEFE_SETOR,
                ),
                is_active=False,
            ),
        )

        client = APIClient()
        client.force_authenticate(user=ator)

        response = client.get(reverse("user-beneficiary-lookup"), {"q": "Ana"})

        assert response.status_code == 200
        assert [item["nome_completo"] for item in response.data] == [
            "Ana Paula",
            "Mariana Obras",
        ]

    def test_beneficiary_lookup_para_auxiliar_setor_sem_setor_retorna_lista_vazia(self):
        auxiliar_sem_setor = self._criar_usuario(
            matricula="22101",
            nome_completo="Auxiliar Sem Setor",
            papel=PapelChoices.AUXILIAR_SETOR,
            setor=None,
        )

        client = APIClient()
        client.force_authenticate(user=auxiliar_sem_setor)

        response = client.get(reverse("user-beneficiary-lookup"), {"q": "Ana"})

        assert response.status_code == 200
        assert response.data == []

    def test_beneficiary_lookup_para_superusuario_retorna_visibilidade_ampla_elegivel(self):
        chefe_ti = self._criar_usuario(
            matricula="22501",
            nome_completo="Chefe TI Super",
            papel=PapelChoices.CHEFE_SETOR,
        )
        setor_ti = self._criar_setor(nome="TI Super", chefe=chefe_ti)
        chefe_ti.setor = setor_ti
        chefe_ti.save(update_fields=["setor"])

        chefe_rh = self._criar_usuario(
            matricula="22502",
            nome_completo="Chefe RH Super",
            papel=PapelChoices.CHEFE_SETOR,
        )
        setor_rh = self._criar_setor(nome="RH Super", chefe=chefe_rh)
        chefe_rh.setor = setor_rh
        chefe_rh.save(update_fields=["setor"])

        superuser = User.objects.create_superuser(
            matricula_funcional="99901",
            password="senha-segura-123",
            nome_completo="Super Admin Lookup",
        )

        self._criar_usuario(
            matricula="22503",
            nome_completo="Carla TI",
            setor=setor_ti,
        )
        self._criar_usuario(
            matricula="22504",
            nome_completo="Carla RH",
            setor=setor_rh,
        )
        self._criar_usuario(
            matricula="22505",
            nome_completo="Carla Inativa",
            setor=setor_ti,
            is_active=False,
        )

        client = APIClient()
        client.force_authenticate(user=superuser)

        response = client.get(reverse("user-beneficiary-lookup"), {"q": "Carla"})

        assert response.status_code == 200
        assert [item["nome_completo"] for item in response.data] == [
            "Carla RH",
            "Carla TI",
        ]

    def test_beneficiary_lookup_sem_autenticacao_retorna_401(self):
        client = APIClient()

        response = client.get(reverse("user-beneficiary-lookup"), {"q": "Ana"})

        assert response.status_code == 401
        assert response.data["error"]["code"] == "not_authenticated"

    def test_beneficiary_lookup_com_query_curta_retorna_400(self):
        user = self._criar_usuario_com_setor()
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get(reverse("user-beneficiary-lookup"), {"q": "An"})

        assert response.status_code == 400
        assert response.data["error"]["code"] == "validation_error"
