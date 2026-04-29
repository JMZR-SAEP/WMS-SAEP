"""Tests for material list API endpoint."""

from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.materials.models import GrupoMaterial, Material, SubgrupoMaterial
from apps.stock.models import EstoqueMaterial
from apps.users.models import Setor, User


@pytest.mark.django_db
class TestMaterialListAPI:
    """Tests for GET /api/v1/materials/ endpoint."""

    @staticmethod
    def _criar_subgrupo():
        grupo = GrupoMaterial.objects.create(codigo_grupo="013", nome="Hidráulico")
        return SubgrupoMaterial.objects.create(grupo=grupo, codigo_subgrupo="001", nome="Tubulação")

    @staticmethod
    def _criar_material(subgrupo, **kwargs):
        defaults = dict(
            codigo_completo="013.001.001",
            sequencial="001",
            nome="Tubo PVC 50mm",
            unidade_medida="UN",
            is_active=True,
        )
        defaults.update(kwargs)
        return Material.objects.create(subgrupo=subgrupo, **defaults)

    @staticmethod
    def _criar_usuario():
        # Criar usuário sem setor primeiro
        usuario = User.objects.create(
            matricula_funcional="000001",
            nome_completo="Usuario Teste",
            is_active=True,
        )
        # Criar setor com esse usuário como chefe
        setor = Setor.objects.create(nome="Setor de Teste", chefe_responsavel=usuario)
        # Atualizar usuário para estar no setor
        usuario.setor = setor
        usuario.save()
        return usuario

    def test_lista_materiais_requer_autenticacao(self):
        """Sem autenticação deve retornar 403 (SessionAuthentication sem sessão)."""
        client = APIClient()
        response = client.get(reverse("material-list"))
        assert response.status_code == 403

    def test_lista_materiais_retorna_apenas_ativos(self):
        """Material inativo não deve aparecer na lista."""
        usuario = self._criar_usuario()
        subgrupo = self._criar_subgrupo()
        self._criar_material(subgrupo, codigo_completo="013.001.001", sequencial="001")
        self._criar_material(
            subgrupo,
            codigo_completo="013.001.002",
            sequencial="002",
            nome="Tubo PVC 75mm",
            is_active=False,
        )

        client = APIClient()
        client.force_authenticate(user=usuario)
        response = client.get(reverse("material-list"))

        assert response.status_code == 200
        assert response.data["count"] == 1
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["codigo_completo"] == "013.001.001"

    def test_busca_por_codigo_completo(self):
        """Busca textual por código completo deve filtrar corretamente."""
        usuario = self._criar_usuario()
        subgrupo = self._criar_subgrupo()
        self._criar_material(subgrupo, codigo_completo="013.001.001", sequencial="001")
        self._criar_material(subgrupo, codigo_completo="013.001.002", sequencial="002")

        client = APIClient()
        client.force_authenticate(user=usuario)
        response = client.get(reverse("material-list"), {"search": "013.001.001"})

        assert response.status_code == 200
        assert response.data["count"] == 1
        assert response.data["results"][0]["codigo_completo"] == "013.001.001"

    def test_busca_por_nome(self):
        """Busca textual por nome deve filtrar corretamente."""
        usuario = self._criar_usuario()
        subgrupo = self._criar_subgrupo()
        self._criar_material(
            subgrupo, codigo_completo="013.001.001", sequencial="001", nome="Cimento Portland"
        )
        self._criar_material(
            subgrupo, codigo_completo="013.001.002", sequencial="002", nome="Areia Fina"
        )

        client = APIClient()
        client.force_authenticate(user=usuario)
        response = client.get(reverse("material-list"), {"search": "Cimento"})

        assert response.status_code == 200
        assert response.data["count"] == 1
        assert response.data["results"][0]["nome"] == "Cimento Portland"

    def test_filtro_por_grupo(self):
        """Filtro por grupo deve retornar apenas materiais do grupo."""
        usuario = self._criar_usuario()
        grupo1 = GrupoMaterial.objects.create(codigo_grupo="001", nome="Construção")
        subgrupo1 = SubgrupoMaterial.objects.create(
            grupo=grupo1, codigo_subgrupo="001", nome="Cimento"
        )
        grupo2 = GrupoMaterial.objects.create(codigo_grupo="002", nome="Hidráulico")
        subgrupo2 = SubgrupoMaterial.objects.create(
            grupo=grupo2, codigo_subgrupo="001", nome="Tubulação"
        )

        Material.objects.create(
            subgrupo=subgrupo1,
            codigo_completo="001.001.001",
            sequencial="001",
            nome="Cimento",
            unidade_medida="KG",
        )
        Material.objects.create(
            subgrupo=subgrupo2,
            codigo_completo="002.001.001",
            sequencial="001",
            nome="Tubo",
            unidade_medida="UN",
        )

        client = APIClient()
        client.force_authenticate(user=usuario)
        response = client.get(reverse("material-list"), {"grupo": "001"})

        assert response.status_code == 200
        assert response.data["count"] == 1
        assert response.data["results"][0]["codigo_completo"] == "001.001.001"

    def test_filtro_por_subgrupo(self):
        """Filtro por subgrupo deve retornar apenas materiais do subgrupo."""
        usuario = self._criar_usuario()
        grupo = GrupoMaterial.objects.create(codigo_grupo="001", nome="Construção")
        subgrupo1 = SubgrupoMaterial.objects.create(
            grupo=grupo, codigo_subgrupo="001", nome="Cimento"
        )
        subgrupo2 = SubgrupoMaterial.objects.create(
            grupo=grupo, codigo_subgrupo="002", nome="Areia"
        )

        Material.objects.create(
            subgrupo=subgrupo1,
            codigo_completo="001.001.001",
            sequencial="001",
            nome="Cimento",
            unidade_medida="KG",
        )
        Material.objects.create(
            subgrupo=subgrupo2,
            codigo_completo="001.002.001",
            sequencial="001",
            nome="Areia",
            unidade_medida="KG",
        )

        client = APIClient()
        client.force_authenticate(user=usuario)
        response = client.get(reverse("material-list"), {"subgrupo": "001"})

        assert response.status_code == 200
        assert response.data["count"] == 1
        assert response.data["results"][0]["codigo_completo"] == "001.001.001"

    def test_saldo_disponivel_calcula_corretamente(self):
        """Saldo disponível deve ser saldo_fisico - saldo_reservado."""
        usuario = self._criar_usuario()
        subgrupo = self._criar_subgrupo()
        material = self._criar_material(subgrupo)
        EstoqueMaterial.objects.create(
            material=material,
            saldo_fisico=100.0,
            saldo_reservado=30.0,
        )

        client = APIClient()
        client.force_authenticate(user=usuario)
        response = client.get(reverse("material-list"))

        assert response.status_code == 200
        assert len(response.data["results"]) == 1
        assert Decimal(response.data["results"][0]["saldo_disponivel"]) == Decimal("70")

    def test_saldo_disponivel_none_quando_sem_estoque(self):
        """Material sem EstoqueMaterial deve retornar saldo_disponivel como None."""
        usuario = self._criar_usuario()
        subgrupo = self._criar_subgrupo()
        self._criar_material(subgrupo)

        client = APIClient()
        client.force_authenticate(user=usuario)
        response = client.get(reverse("material-list"))

        assert response.status_code == 200
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["saldo_disponivel"] is None

    def test_paginacao_envelope(self):
        """Resposta deve incluir envelope de paginação correto."""
        usuario = self._criar_usuario()
        subgrupo = self._criar_subgrupo()
        for i in range(25):
            Material.objects.create(
                subgrupo=subgrupo,
                codigo_completo=f"013.001.{i:03d}",
                sequencial=f"{i:03d}",
                nome=f"Material {i}",
                unidade_medida="UN",
            )

        client = APIClient()
        client.force_authenticate(user=usuario)
        response = client.get(reverse("material-list"))

        assert response.status_code == 200
        assert "count" in response.data
        assert "page" in response.data
        assert "page_size" in response.data
        assert "total_pages" in response.data
        assert "results" in response.data
        assert response.data["count"] == 25
        assert response.data["page_size"] == 20
        assert response.data["total_pages"] == 2
        assert len(response.data["results"]) == 20
