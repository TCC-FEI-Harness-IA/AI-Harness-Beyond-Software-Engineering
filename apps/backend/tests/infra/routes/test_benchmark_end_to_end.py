"""Integração ponta a ponta do benchmark: `WS /v1/benchmark/run` e as consultas `GET /v1/benchmark/*`.

Usa o grafo real — dataset do backend, composition roots dos dois fluxos, repositórios JSON ou
MongoDB simulado, mapper e templates reais — com a única substituição na fronteira de rede: o
transporte HTTP do provedor, por `httpx.MockTransport`.
"""
import json
from collections import deque
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient
from starlette.websockets import WebSocketDisconnect

from src.infra.adapters import mongo_client_adapter
from src.infra.services.llm_service_factory import LLMServiceFactory
from src.infra.services.openrouter_service import OpenRouterService
from src.main import create_app

_MODELO = "vendor/modelo"
_CRITERIO = {"criterion_id": "AC1", "met": True, "justification": "Atende"}
_APROVADO = {"decision": "approved", "criteria_evaluation": [_CRITERIO], "unmet_criteria_ids": []}
_TAREFA = {
    "id": "T1",
    "title": "Resolver",
    "description": "Escolher alternativa",
    "expected_input": "Questão",
    "expected_output": "Alternativa",
    "acceptance_criteria": [{"id": "AC1", "description": "Escolher uma alternativa"}],
}


def _roteiro_ralph(resposta: str) -> list[str]:
    return [
        json.dumps({"general_acceptance_criteria": [{"id": "AC1", "description": "Responder"}]}),
        json.dumps({"tasks": [_TAREFA]}),
        json.dumps({"learnings": []}),
        json.dumps({"task_id": "T1", "result": "resolvido"}),
        json.dumps(_APROVADO),
        json.dumps({"learnings": []}),
        json.dumps(_APROVADO),
        json.dumps({"final_answer": resposta}),
    ]


class _Provedor:
    """Provedor simulado: devolve o roteiro na ordem e registra cada corpo enviado."""

    def __init__(self, respostas: list[str], status_code: int = 200) -> None:
        self.respostas = deque(respostas)
        self.status_code = status_code
        self.enviados: list[dict[str, Any]] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.enviados.append(json.loads(request.content))
        if self.status_code != 200:
            return httpx.Response(self.status_code, json={"error": "falha simulada"})
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": self.respostas.popleft()}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            },
        )


@pytest.fixture
def ambiente(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isola armazenamento e modelo dentro do teste."""
    monkeypatch.setenv("RALPH_SESSION_STORAGE_BACKEND", "json_file")
    monkeypatch.setenv("RALPH_SESSIONS_STORAGE_PATH", str(tmp_path / "sessions"))
    monkeypatch.setenv("RALPH_BENCHMARK_SESSIONS_STORAGE_PATH", str(tmp_path / "benchmark-sessions"))
    monkeypatch.setenv("RALPH_BENCHMARK_PROGRESS_INTERVAL_SECONDS", "0.05")
    monkeypatch.setenv("LLM_MODEL", _MODELO)
    monkeypatch.setenv("OPENROUTER_API_KEY", "chave-de-teste")
    monkeypatch.setenv("GENAI_AVAILABLE_MODELS", _MODELO)
    monkeypatch.setenv("GENAI_AVAILABLE_PROVIDERS", "open_router")
    return tmp_path


def _cliente(monkeypatch: pytest.MonkeyPatch, provedor: _Provedor) -> TestClient:
    def _servicos(factory: LLMServiceFactory) -> list[OpenRouterService]:
        return [
            OpenRouterService(
                logger=factory.settings.logger(__file__),
                settings=factory.settings,
                transport=httpx.MockTransport(provedor),
            )
        ]

    monkeypatch.setattr(LLMServiceFactory, "create_all", _servicos)
    return TestClient(create_app())


def _abertura(**sobrescritas: Any) -> dict[str, Any]:
    corpo: dict[str, Any] = {
        "question_count": 2,
        "max_parallel": 1,
        "llm_model_config": {
            "provider": "open_router",
            "provider_config": {"model_name": _MODELO},
            "max_tokens": 4096,
            "temperature": 0,
        },
    }
    corpo.update(sobrescritas)
    return corpo


def _executar(cliente: TestClient, abertura: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
    with cliente.websocket_connect("/v1/benchmark/run") as ws:
        ws.send_json(abertura)
        frames = []
        try:
            while True:
                frames.append(ws.receive_json())
        except WebSocketDisconnect as exc:
            return frames, exc.code


def _sessoes_gravadas(diretorio: Path) -> list[dict[str, Any]]:
    return [json.loads(path.read_text(encoding="utf-8")) for path in sorted(diretorio.glob("*.json"))]


def test_bateria_executa_as_primeiras_questoes_e_grava_a_benchmark_session(
    ambiente: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Q108 (gabarito D): simples acerta, Ralph acerta. Q112 (gabarito A): simples erra, Ralph acerta.
    provedor = _Provedor(
        ["RESPOSTA_FINAL: D", *_roteiro_ralph("RESPOSTA_FINAL: D"), "RESPOSTA_FINAL: B", *_roteiro_ralph("A")]
    )

    frames, codigo = _executar(_cliente(monkeypatch, provedor), _abertura())

    assert codigo == 1000
    assert not provedor.respostas
    assert all(corpo["model"] == _MODELO and corpo["temperature"] == 0 for corpo in provedor.enviados)
    assert {frame["type"] for frame in frames[:-1]} == {"progress"}
    assert frames[0]["benchmark_session"]["progress"] == {
        "total": 2, "pending": 2, "running": 0, "finished": 0, "interrupted": 0,
    }

    final = frames[-1]
    assert final["type"] == "result"
    bateria = final["benchmark_session"]
    assert bateria["status"] == "completed"
    assert bateria["progress"]["finished"] == 2
    assert [questao["question_id"] for questao in bateria["questions"]] == [
        "FISICA_ENEM_2023_AZUL_Q108",
        "FISICA_ENEM_2023_AZUL_Q112",
    ]
    assert bateria["summary"]["simple"]["correct"] == 1
    assert bateria["summary"]["simple"]["wrong"] == 1
    assert bateria["summary"]["ralph"]["correct"] == 2
    assert bateria["summary"]["ralph"]["accuracy"] == 1.0
    assert bateria["total_tokens"] == 18 * 15
    assert len(bateria["session_ids"]) == 4

    sessoes = _sessoes_gravadas(ambiente / "sessions")
    assert {sessao["id"] for sessao in sessoes} == set(bateria["session_ids"])
    assert all(sessao["benchmark_details"]["run_id"] == bateria["id"] for sessao in sessoes)
    assert all(sessao["benchmark_details"]["is_banchmark"] is True for sessao in sessoes)
    assert all("alternativa_correta" not in sessao["user_question"] for sessao in sessoes)
    assert all("RESPOSTA_FINAL: LETRA" in sessao["user_question"] for sessao in sessoes)

    gravada = json.loads((ambiente / "benchmark-sessions" / f"{bateria['id']}.json").read_text(encoding="utf-8"))
    assert gravada == bateria


def test_falha_do_provedor_vira_erro_avaliado_sem_derrubar_a_bateria(
    ambiente: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    provedor = _Provedor([], status_code=500)

    frames, codigo = _executar(_cliente(monkeypatch, provedor), _abertura(question_count=1))

    assert codigo == 1000
    bateria = frames[-1]["benchmark_session"]
    assert bateria["status"] == "completed"
    assert bateria["summary"]["simple"]["failures"] == 1
    assert bateria["summary"]["ralph"]["failures"] == 1
    questao = bateria["questions"][0]
    assert questao["simple"]["error"] and questao["ralph"]["error"]
    sessoes = _sessoes_gravadas(ambiente / "sessions")
    assert {sessao["status"] for sessao in sessoes} == {"failed"}
    assert all(sessao["benchmark_details"]["is_correct"] is False for sessao in sessoes)


def test_bateria_no_mongodb_grava_as_baterias_na_colecao_propria(
    ambiente: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("RALPH_SESSION_STORAGE_BACKEND", "mongodb")
    monkeypatch.setenv("MONGODB_DATABASE", "benchmark_teste")
    cliente_mongo = AsyncMongoMockClient()
    monkeypatch.setattr(mongo_client_adapter, "AsyncIOMotorClient", lambda *args: cliente_mongo)
    provedor = _Provedor(["RESPOSTA_FINAL: D", *_roteiro_ralph("RESPOSTA_FINAL: D")])
    cliente = _cliente(monkeypatch, provedor)

    frames, codigo = _executar(cliente, _abertura(question_count=1))

    assert codigo == 1000
    bateria = frames[-1]["benchmark_session"]
    listagem = cliente.get("/v1/benchmark/sessions").json()["benchmark_sessions"]
    assert [item["id"] for item in listagem] == [bateria["id"]]
    assert cliente.get(f"/v1/benchmark/sessions/{bateria['id']}").json() == bateria
    for session_id in bateria["session_ids"]:
        assert cliente.get(f"/v1/sessions/{session_id}").json()["benchmark_details"]["run_id"] == bateria["id"]


def test_consultas_listam_detalham_e_descrevem_o_dataset(ambiente: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    provedor = _Provedor(["RESPOSTA_FINAL: D", *_roteiro_ralph("RESPOSTA_FINAL: D")])
    cliente = _cliente(monkeypatch, provedor)
    frames, _ = _executar(cliente, _abertura(question_count=1))
    bateria = frames[-1]["benchmark_session"]

    dataset = cliente.get("/v1/benchmark/questions").json()
    listagem = cliente.get("/v1/benchmark/sessions").json()
    detalhe = cliente.get(f"/v1/benchmark/sessions/{bateria['id']}")

    assert len(dataset["question_ids"]) == 15
    assert dataset["question_ids"][0] == "FISICA_ENEM_2023_AZUL_Q108"
    assert dataset["max_parallel_limit"] == 10
    assert listagem == {"benchmark_sessions": [bateria]}
    assert detalhe.status_code == 200
    assert detalhe.json() == bateria


def test_quantidade_acima_do_dataset_e_recusada_antes_de_qualquer_chamada(
    ambiente: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    provedor = _Provedor([])

    frames, codigo = _executar(_cliente(monkeypatch, provedor), _abertura(question_count=16))

    assert codigo == 1003
    assert frames == [{"type": "error", "content": frames[0]["content"]}]
    assert "question_count" in frames[0]["content"]
    assert provedor.enviados == []
    assert not (ambiente / "benchmark-sessions").exists()
