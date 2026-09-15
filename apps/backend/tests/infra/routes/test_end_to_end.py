"""Integração ponta a ponta dos dois fluxos comparáveis do experimento.

`WS /v1/message/reasoning` (harness) e `POST /v1/message/default` (baseline) usam o
grafo real de dependências — repositório em disco, mapper, templates reais — com a
única substituição de fronteira externa: `ILLMCompletions`/`ILLMService` por dublês.
"""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from src.infra.startups import default_message_startup as default_startup_module
from src.infra.startups import ralph_thinking_startup as ralph_startup_module
from src.main import create_app
from tests.doubles.fake_llm_service import FakeLLMService
from tests.doubles.scripted_llm_completions import ScriptedLLMCompletions


class _FakeLLMServiceFactory:
    """Dublê da fábrica que devolve um único serviço, o dublê do provedor."""

    def __init__(self, settings: object, llm_service: FakeLLMService) -> None:
        self.settings = settings
        self.llm_service = llm_service

    def create_all(self) -> list[FakeLLMService]:
        """Devolve o dublê como único serviço registrado."""
        return [self.llm_service]


def _criterios() -> str:
    return json.dumps(
        {
            "general_acceptance_criteria": [
                {"id": "AC1", "description": "responder em portugues"},
            ]
        }
    )


def _tarefas(*ids: str) -> str:
    return json.dumps(
        {
            "tasks": [
                {
                    "id": task_id,
                    "title": f"titulo de {task_id}",
                    "description": f"descricao de {task_id}",
                    "expected_input": "entrada esperada",
                    "expected_output": "saida esperada",
                    "acceptance_criteria": [{"id": f"{task_id}-AC1", "description": f"criterio de {task_id}"}],
                }
                for task_id in ids
            ]
        }
    )


def _resolucao(texto: str) -> str:
    return json.dumps({"task_id": "T1", "result": texto})


def _aprovado(criterion_id: str = "T1-AC1") -> str:
    return json.dumps(
        {
            "decision": "approved",
            "criteria_evaluation": [{"criterion_id": criterion_id, "met": True, "justification": "atende"}],
            "unmet_criteria_ids": [],
        }
    )


def _aprendizados(*fatos: str) -> str:
    return json.dumps({"learnings": list(fatos)})


def _resposta_final(texto: str = "D) Nenhuma das anteriores") -> str:
    return json.dumps({"final_answer": texto})


def _roteiro_feliz() -> list[str]:
    return [
        _criterios(),
        _tarefas("T1"),
        _resolucao("2 é primo, par e maior que 2 não existe; a resposta correta é D"),
        _aprovado(),
        _aprendizados("O único primo par é o 2."),
        _aprovado("AC1"),
        _resposta_final(),
    ]


@pytest.fixture
def storage_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isola o armazenamento de sessões e a configuração de modelo dentro do teste."""
    caminho = tmp_path / "sessions"
    monkeypatch.setenv("RALPH_SESSIONS_STORAGE_PATH", str(caminho))
    monkeypatch.setenv("LLM_MODEL", "vendor/modelo")
    monkeypatch.setenv("OPENROUTER_API_KEY", "chave-de-teste")
    monkeypatch.setenv("GENAI_AVAILABLE_MODELS", "vendor/modelo")
    monkeypatch.setenv("GENAI_AVAILABLE_PROVIDERS", "open_router")
    return caminho


@pytest.fixture
def client(storage_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Cliente HTTP com as portas de LLM dos dois fluxos substituídas por dublês."""
    llm_service = FakeLLMService()
    monkeypatch.setattr(
        default_startup_module,
        "LLMServiceFactory",
        lambda settings: _FakeLLMServiceFactory(settings=settings, llm_service=llm_service),
    )
    scripted_completions = ScriptedLLMCompletions(responses=_roteiro_feliz())
    monkeypatch.setattr(
        ralph_startup_module,
        "LLMCompletionsAdapter",
        lambda **kwargs: scripted_completions,
    )
    return TestClient(create_app())


def _build_default_body() -> dict[str, object]:
    return {
        "message": {"user_input": "Qual dos seguintes números é primo, par e maior que 2?"},
        "llm_model_config": {
            "provider": "open_router",
            "provider_config": {"model_name": "vendor/modelo"},
            "max_tokens": 100,
            "temperature": 0.3,
        },
    }


def _build_reasoning_payload() -> dict[str, object]:
    return {
        "message": {"user_input": "Qual dos seguintes números é primo, par e maior que 2?"},
        "llm_model_config": {
            "provider": "open_router",
            "provider_config": {"model_name": "vendor/modelo"},
            "max_tokens": 1200,
            "temperature": 0.3,
        },
    }


def _run_harness(client: TestClient) -> tuple[list[dict], int]:
    with client.websocket_connect("/v1/message/reasoning") as ws:
        ws.send_json(_build_reasoning_payload())
        frames = []
        try:
            while True:
                frames.append(ws.receive_json())
        except WebSocketDisconnect as exc:
            return frames, exc.code


def test_harness_completo_grava_pergunta_fases_resposta_tokens_e_tempos(
    client: TestClient, storage_path: Path
) -> None:
    frames, close_code = _run_harness(client)

    assert close_code == 1000
    assert frames[-1]["type"] == "result"
    session_id = frames[-1]["session_id"]

    documento = json.loads((storage_path / f"{session_id}.json").read_text(encoding="utf-8"))
    assert documento["user_question"] == "Qual dos seguintes números é primo, par e maior que 2?"
    assert documento["flow"] == "A1"
    assert documento["status"] == "completed"
    assert documento["final_answer"] == "D) Nenhuma das anteriores"
    assert documento["totals"]["total_tokens"] > 0
    assert documento["totals"]["wall_time_ms"] >= 0

    fases_percorridas = {mensagem["phase"] for mensagem in documento["messages"]}
    assert {"A1", "A2", "B1", "B2", "B3", "B4", "C1", "C3"} <= fases_percorridas


def test_consulta_apos_o_websocket_devolve_exatamente_a_sessao_persistida(
    client: TestClient, storage_path: Path
) -> None:
    frames, _ = _run_harness(client)
    session_id = frames[-1]["session_id"]

    consulta = client.get(f"/v1/sessions/{session_id}")

    assert consulta.status_code == 200
    assert consulta.json() == json.loads((storage_path / f"{session_id}.json").read_text(encoding="utf-8"))


def test_baseline_cria_sessao_direct_inference_com_duas_mensagens(client: TestClient) -> None:
    resposta = client.post("/v1/message/default", json=_build_default_body())

    assert resposta.status_code == 200
    session_id = resposta.json()["session_id"]

    documento = client.get(f"/v1/sessions/{session_id}").json()
    assert documento["flow"] == "DIRECT"
    assert len(documento["messages"]) == 2


def test_baseline_e_harness_produzem_sessoes_comparaveis_para_a_mesma_pergunta(client: TestClient) -> None:
    frames, _ = _run_harness(client)
    harness_session_id = frames[-1]["session_id"]

    baseline_session_id = client.post("/v1/message/default", json=_build_default_body()).json()["session_id"]

    harness_doc = client.get(f"/v1/sessions/{harness_session_id}").json()
    baseline_doc = client.get(f"/v1/sessions/{baseline_session_id}").json()

    assert harness_doc["flow"] != baseline_doc["flow"]
    assert harness_doc["user_question"] == baseline_doc["user_question"]


def test_listagem_inclui_as_sessoes_dos_dois_fluxos(client: TestClient) -> None:
    frames, _ = _run_harness(client)
    harness_session_id = frames[-1]["session_id"]
    baseline_session_id = client.post("/v1/message/default", json=_build_default_body()).json()["session_id"]

    listagem = client.get("/v1/sessions").json()["session_ids"]

    assert set(listagem) == {harness_session_id, baseline_session_id}
