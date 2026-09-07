from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.application.dtos.default_message_output_dto import DefaultMessageOutputDTO
from src.infra.routes.v1.message import router as message_router_module
from src.main import create_app

_SAIDA = DefaultMessageOutputDTO(
    message="pergunta do usuario",
    response="resposta do modelo",
    tokens_input=11,
    tokens_output=22,
    inference_time_ms=0,
)


class _FakeStartup:
    """Dublê do startup, para manter a rota isolada da rede."""

    error: Exception | None = None

    def __init__(self) -> None:
        pass

    async def run(self, payload: Any) -> Any:
        """Devolve a resposta programada ou levanta o erro programado."""
        if _FakeStartup.error is not None:
            raise _FakeStartup.error

        from src.infra.routes.v1.message.dtos.default_output_dto import DefaultOutputDTO

        return DefaultOutputDTO(message=_SAIDA.message, response=_SAIDA.response)


def _build_body(**overrides: Any) -> dict[str, Any]:
    corpo: dict[str, Any] = {
        "message": {"user_input": "pergunta do usuario"},
        "llm_model_config": {
            "provider": "open_router",
            "provider_config": {"model_name": "vendor/modelo"},
            "max_tokens": 100,
            "temperature": 0.3,
        },
    }
    corpo.update(overrides)
    return corpo


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Cliente HTTP com o startup do fluxo baseline substituído por dublê."""
    _FakeStartup.error = None
    monkeypatch.setattr(message_router_module, "DefaultMessageStartup", _FakeStartup)
    return TestClient(create_app())


def test_fluxo_default_devolve_pergunta_e_resposta(client: TestClient) -> None:
    resposta = client.post("/v1/message/default", json=_build_body())

    assert resposta.status_code == 200
    assert resposta.json() == {"message": "pergunta do usuario", "response": "resposta do modelo"}


def test_falha_do_fluxo_vira_erro_500_com_detalhe(client: TestClient) -> None:
    _FakeStartup.error = RuntimeError("provedor fora do ar")

    resposta = client.post("/v1/message/default", json=_build_body())

    assert resposta.status_code == 500
    assert resposta.json()["detail"] == "provedor fora do ar"


def test_corpo_sem_mensagem_e_recusado(client: TestClient) -> None:
    corpo = _build_body()
    del corpo["message"]

    assert client.post("/v1/message/default", json=corpo).status_code == 422


def test_temperatura_fora_do_intervalo_e_recusada(client: TestClient) -> None:
    corpo = _build_body()
    corpo["llm_model_config"]["temperature"] = 5

    assert client.post("/v1/message/default", json=corpo).status_code == 422


def test_health_check_responde_ok(client: TestClient) -> None:
    resposta = client.get("/v1/health")

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok"}


def test_rota_de_reasoning_foi_removida_nesta_fase(client: TestClient) -> None:
    assert client.post("/v1/message/reasoning", json=_build_body()).status_code == 404
