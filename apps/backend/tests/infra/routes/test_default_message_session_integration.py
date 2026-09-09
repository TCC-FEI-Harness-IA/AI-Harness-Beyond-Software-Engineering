"""Integração ponta a ponta do fluxo baseline: rota → caso de uso → sessão em disco.

Só o `ILLMService` é substituído por dublê; todo o restante do grafo é o real,
incluindo o repositório de arquivos, apontado para o `tmp_path` do teste.
"""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.infra.startups import default_message_startup as startup_module
from src.main import create_app
from tests.doubles.fake_llm_service import FakeLLMService


@pytest.fixture
def storage_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isola o armazenamento de sessões e a configuração de modelo dentro do teste."""
    caminho = tmp_path / "sessions"
    monkeypatch.setenv("RALPH_SESSIONS_STORAGE_PATH", str(caminho))
    monkeypatch.setenv("OPENROUTER_MODEL", "vendor/modelo")
    monkeypatch.setenv("OPENROUTER_API_KEY", "chave-de-teste")
    monkeypatch.setenv("GENAI_AVAILABLE_MODELS", "vendor/modelo")
    monkeypatch.setenv("GENAI_AVAILABLE_PROVIDERS", "open_router")
    return caminho


@pytest.fixture
def client(storage_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Cliente HTTP com o provedor de LLM substituído por dublê."""
    monkeypatch.setattr(
        startup_module,
        "OpenRouterService",
        lambda logger, settings: FakeLLMService(),
    )
    return TestClient(create_app())


def _build_body() -> dict[str, object]:
    return {
        "message": {"user_input": "Qual dos números é primo, par e maior que 2?"},
        "llm_model_config": {
            "provider": "open_router",
            "provider_config": {"model_name": "vendor/modelo"},
            "max_tokens": 100,
            "temperature": 0.3,
        },
    }


def test_inferencia_direta_grava_a_sessao_completa_em_disco(client: TestClient, storage_path: Path) -> None:
    resposta = client.post("/v1/message/default", json=_build_body())

    assert resposta.status_code == 200
    session_id = resposta.json()["session_id"]

    documento = json.loads((storage_path / f"{session_id}.json").read_text(encoding="utf-8"))
    assert documento["user_question"] == "Qual dos números é primo, par e maior que 2?"
    assert documento["final_answer"] == "resposta do modelo"
    assert documento["status"] == "completed"
    assert [mensagem["source"] for mensagem in documento["messages"]] == ["user", "llm_agent"]
    assert documento["messages"][1]["tokens_input"] == 11
    assert documento["messages"][1]["tokens_output"] == 22
    assert documento["messages"][1]["inference_time_ms"] >= 0
    assert documento["totals"]["tokens_input"] == 11
    assert documento["totals"]["tokens_output"] == 22
    assert documento["totals"]["total_tokens"] == 33
    assert documento["totals"]["total_llm_calls"] == 1
    assert documento["totals"]["wall_time_ms"] >= 0


def test_consulta_devolve_o_mesmo_documento_gravado(client: TestClient, storage_path: Path) -> None:
    session_id = client.post("/v1/message/default", json=_build_body()).json()["session_id"]

    consulta = client.get(f"/v1/sessions/{session_id}")

    assert consulta.status_code == 200
    assert consulta.json() == json.loads((storage_path / f"{session_id}.json").read_text(encoding="utf-8"))


def test_listagem_inclui_a_sessao_recem_criada(client: TestClient) -> None:
    session_id = client.post("/v1/message/default", json=_build_body()).json()["session_id"]

    assert client.get("/v1/sessions").json()["session_ids"] == [session_id]
