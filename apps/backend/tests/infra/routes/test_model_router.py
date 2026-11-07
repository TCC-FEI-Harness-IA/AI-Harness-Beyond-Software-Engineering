from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.domain.errors.model_already_registered_error import ModelAlreadyRegisteredError
from src.domain.errors.model_not_found_error import ModelNotFoundError
from src.infra.routes.v1.model import router as model_router_module
from src.infra.routes.v1.model.dtos.model_info_dto import ModelInfoFieldsDTO, ModelInfoInputDTO
from src.main import create_app


class _StartupFalso:
    """Catálogo em memória no lugar do `ModelCatalogStartup`, compartilhado entre requisições."""

    modelos: dict[str, dict[str, Any]] = {}

    async def list_models(self) -> list[dict[str, Any]]:
        return [self.modelos[nome] for nome in sorted(self.modelos)]

    async def register_model(self, payload: ModelInfoInputDTO) -> dict[str, Any]:
        if payload.model_name in self.modelos:
            raise ModelAlreadyRegisteredError(model_name=payload.model_name)
        self.modelos[payload.model_name] = payload.model_dump()
        return self.modelos[payload.model_name]

    async def update_model(self, model_name: str, payload: ModelInfoFieldsDTO) -> dict[str, Any]:
        if model_name not in self.modelos:
            raise ModelNotFoundError(model_name=model_name)
        self.modelos[model_name] = {"model_name": model_name, **payload.model_dump()}
        return self.modelos[model_name]

    async def delete_model(self, model_name: str) -> None:
        if self.modelos.pop(model_name, None) is None:
            raise ModelNotFoundError(model_name=model_name)


@pytest.fixture
def cliente(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    _StartupFalso.modelos = {}
    monkeypatch.setattr(model_router_module, "ModelCatalogStartup", _StartupFalso)
    return TestClient(create_app())


def test_lista_os_modelos_do_startup(cliente: TestClient) -> None:
    _StartupFalso.modelos = {"vendor/modelo": {"model_name": "vendor/modelo", "context_length": 8192}}

    resposta = cliente.get("/v1/models")

    assert resposta.status_code == 200
    assert resposta.json() == {"models": [{"model_name": "vendor/modelo", "context_length": 8192}]}


def test_cadastro_devolve_201_e_o_modelo(cliente: TestClient) -> None:
    resposta = cliente.post("/v1/models", json={"model_name": "vendor/novo", "context_length": 4096})

    assert resposta.status_code == 201
    assert resposta.json()["model_name"] == "vendor/novo"
    assert resposta.json()["context_length"] == 4096


def test_cadastro_repetido_devolve_409(cliente: TestClient) -> None:
    cliente.post("/v1/models", json={"model_name": "vendor/novo"})

    resposta = cliente.post("/v1/models", json={"model_name": "vendor/novo"})

    assert resposta.status_code == 409
    assert "vendor/novo" in resposta.json()["detail"]


@pytest.mark.parametrize(
    "corpo",
    [
        {"model_name": ""},
        {"model_name": "vendor/x", "input_price_per_million_tokens": -1},
        {"model_name": "vendor/x", "context_length": 0},
        {"model_name": "vendor/x", "throughput_tokens_per_second": 0},
    ],
)
def test_cadastro_invalido_devolve_422(cliente: TestClient, corpo: dict[str, Any]) -> None:
    assert cliente.post("/v1/models", json=corpo).status_code == 422


def test_edicao_aceita_identificador_com_barra(cliente: TestClient) -> None:
    cliente.post("/v1/models", json={"model_name": "vendor/modelo"})

    resposta = cliente.put("/v1/models/vendor/modelo", json={"display_name": "Vendor: Modelo"})

    assert resposta.status_code == 200
    assert resposta.json()["model_name"] == "vendor/modelo"
    assert resposta.json()["display_name"] == "Vendor: Modelo"


def test_edicao_de_modelo_inexistente_devolve_404(cliente: TestClient) -> None:
    assert cliente.put("/v1/models/vendor/fantasma", json={}).status_code == 404


def test_remocao_devolve_204_e_depois_404(cliente: TestClient) -> None:
    cliente.post("/v1/models", json={"model_name": "vendor/modelo"})

    assert cliente.delete("/v1/models/vendor/modelo").status_code == 204
    assert cliente.delete("/v1/models/vendor/modelo").status_code == 404


def test_falha_inesperada_vira_500(monkeypatch: pytest.MonkeyPatch) -> None:
    class _StartupQuebrado:
        def __init__(self) -> None:
            raise RuntimeError("mongo fora do ar")

    monkeypatch.setattr(model_router_module, "ModelCatalogStartup", _StartupQuebrado)

    resposta = TestClient(create_app()).get("/v1/models")

    assert resposta.status_code == 500
    assert resposta.json()["detail"] == "mongo fora do ar"


class _StartupComErro:
    erro: Exception = RuntimeError("falha")

    async def register_model(self, payload: ModelInfoInputDTO) -> dict[str, Any]:
        raise self.erro

    async def update_model(self, model_name: str, payload: ModelInfoFieldsDTO) -> dict[str, Any]:
        raise self.erro

    async def delete_model(self, model_name: str) -> None:
        raise self.erro


@pytest.mark.parametrize(("erro", "status"), [(ValueError("valor inválido"), 400), (RuntimeError("falha"), 500)])
def test_erros_do_cadastro_e_da_edicao_viram_status_http(
    monkeypatch: pytest.MonkeyPatch, erro: Exception, status: int
) -> None:
    _StartupComErro.erro = erro
    monkeypatch.setattr(model_router_module, "ModelCatalogStartup", _StartupComErro)
    cliente = TestClient(create_app())

    assert cliente.post("/v1/models", json={"model_name": "vendor/x"}).status_code == status
    assert cliente.put("/v1/models/vendor/x", json={}).status_code == status


def test_falha_inesperada_na_remocao_vira_500(monkeypatch: pytest.MonkeyPatch) -> None:
    _StartupComErro.erro = RuntimeError("falha")
    monkeypatch.setattr(model_router_module, "ModelCatalogStartup", _StartupComErro)

    assert TestClient(create_app()).delete("/v1/models/vendor/x").status_code == 500
