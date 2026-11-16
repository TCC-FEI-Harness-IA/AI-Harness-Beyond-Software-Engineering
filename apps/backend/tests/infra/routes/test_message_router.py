from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.application.dtos.default_message_output_dto import DefaultMessageOutputDTO
from src.infra.routes.v1.message import router as message_router_module
from src.main import create_app
from tests.doubles.security_doubles import ORIGEM, authenticated_client, build_security, sign_in

_SAIDA = DefaultMessageOutputDTO(
    message="pergunta do usuario",
    response="resposta do modelo",
    session_id="sess_ab12",
    tokens_input=11,
    tokens_output=22,
    inference_time_ms=812,
)


class _FakeStartup:
    """Dublê do startup, para manter a rota isolada da rede."""

    error: Exception | None = None
    kwargs: list[dict[str, Any]] = []

    def __init__(self, **kwargs: Any) -> None:
        _FakeStartup.kwargs.append(kwargs)

    async def run(self, payload: Any) -> Any:
        """Devolve a resposta programada ou levanta o erro programado."""
        if _FakeStartup.error is not None:
            raise _FakeStartup.error

        from src.infra.routes.v1.message.dtos.default_output_dto import DefaultOutputDTO

        return DefaultOutputDTO(
            message=_SAIDA.message,
            response=_SAIDA.response,
            session_id=_SAIDA.session_id,
            tokens_input=_SAIDA.tokens_input,
            tokens_output=_SAIDA.tokens_output,
            inference_time_ms=_SAIDA.inference_time_ms,
        )


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
    _FakeStartup.kwargs = []
    monkeypatch.setattr(message_router_module, "DefaultMessageStartup", _FakeStartup)
    return authenticated_client(user_id="usr_ana")


def test_fluxo_default_devolve_pergunta_e_resposta(client: TestClient) -> None:
    resposta = client.post("/v1/message/default", json=_build_body())

    assert resposta.status_code == 200
    assert resposta.json() == {
        "message": "pergunta do usuario",
        "response": "resposta do modelo",
        "session_id": "sess_ab12",
        "tokens_input": 11,
        "tokens_output": 22,
        "inference_time_ms": 812,
    }


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


def test_limites_informam_o_teto_de_tokens_por_sessao_do_backend(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LLM_MAX_TOKENS", "64000")

    resposta = client.get("/v1/limits")

    assert resposta.status_code == 200
    assert resposta.json() == {"max_tokens_limit": 64000}


def test_max_tokens_acima_do_teto_por_sessao_do_backend_e_recusado(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LLM_MAX_TOKENS", "500")
    corpo = _build_body()
    corpo["llm_model_config"]["max_tokens"] = 501

    assert client.post("/v1/message/default", json=corpo).status_code == 422


def test_rota_de_reasoning_foi_removida_nesta_fase(client: TestClient) -> None:
    assert client.post("/v1/message/reasoning", json=_build_body()).status_code == 404


def test_startup_recebe_o_dono_e_a_autorizacao_da_sessao(client: TestClient) -> None:
    client.post("/v1/message/default", json=_build_body())

    chamada = _FakeStartup.kwargs[0]
    assert chamada["owner_id"] == "usr_ana"
    assert chamada["authorization"].owner_id == "usr_ana"
    assert chamada["authorization"].credential.api_key.startswith("sk-or-v1-")


def test_visitante_nao_executa_chamada_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    _FakeStartup.kwargs = []
    monkeypatch.setattr(message_router_module, "DefaultMessageStartup", _FakeStartup)
    client = TestClient(create_app(security=build_security()))

    resposta = client.post("/v1/message/default", json=_build_body(), headers={"Origin": ORIGEM})

    assert resposta.status_code == 401
    assert _FakeStartup.kwargs == []


def test_sem_credencial_openrouter_a_execucao_e_recusada(monkeypatch: pytest.MonkeyPatch) -> None:
    _FakeStartup.kwargs = []
    monkeypatch.setattr(message_router_module, "DefaultMessageStartup", _FakeStartup)
    client = authenticated_client(with_credential=False)

    resposta = client.post("/v1/message/default", json=_build_body())

    assert resposta.status_code == 428
    assert _FakeStartup.kwargs == []


def test_sem_token_anti_csrf_a_execucao_e_recusada(client: TestClient) -> None:
    del client.headers["X-CSRF-Token"]

    assert client.post("/v1/message/default", json=_build_body()).status_code == 403
    assert _FakeStartup.kwargs == []


def test_limite_de_execucoes_por_janela(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(message_router_module, "DefaultMessageStartup", _FakeStartup)
    _FakeStartup.error = None
    client = authenticated_client(security=build_security(max_run_starts_per_window=1))

    assert client.post("/v1/message/default", json=_build_body()).status_code == 200
    bloqueada = client.post("/v1/message/default", json=_build_body())

    assert bloqueada.status_code == 429
    assert int(bloqueada.headers["retry-after"]) > 0


def test_credencial_de_outra_conta_nao_executa(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(message_router_module, "DefaultMessageStartup", _FakeStartup)
    seguranca = build_security()
    ana = authenticated_client(user_id="usr_ana", security=seguranca)
    cookie_da_ana = ana.cookies.get("ralph_llm_credential")
    bia = TestClient(create_app(security=seguranca))
    bia.headers.update(sign_in(bia, seguranca, user_id="usr_bia"))
    bia.cookies.set("ralph_llm_credential", cookie_da_ana)

    assert bia.post("/v1/message/default", json=_build_body()).status_code == 428
