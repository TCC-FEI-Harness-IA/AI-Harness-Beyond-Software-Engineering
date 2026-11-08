"""Integração ponta a ponta do benchmark: `WS /v1/benchmark/run` e as consultas `GET /v1/benchmark/*`.

Usa o grafo real — dataset do backend, composition roots dos dois fluxos, repositórios JSON ou
MongoDB simulado, mapper e templates reais — com a única substituição na fronteira de rede: o
transporte HTTP do provedor, por `httpx.MockTransport`.
"""
import json
import io
import logging
import zipfile
from collections import deque
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient
from starlette.websockets import WebSocketDisconnect

from src.infra.adapters import mongo_client_adapter
from src.infra.config.settings import Settings
from src.infra.providers.file_benchmark_question_provider import FileBenchmarkQuestionProvider
from src.infra.providers.mmlu_benchmark_question_provider import MMLUBenchmarkQuestionProvider, MMLU_REVISION
from src.domain.services.benchmark_question_selector import select_mmlu_questions
from src.infra.providers.gpqa_benchmark_question_provider import GPQABenchmarkQuestionProvider, GPQA_REVISION
from src.infra.services.llm_service_factory import LLMServiceFactory
from src.infra.services.openrouter_service import OpenRouterService
from src.main import create_app

_MODELO = "vendor/modelo"
_CRITERIO = {"criterion_id": "AC1", "met": True, "justification": "Atende"}
_APROVADO = {"decision": "approved", "criteria_evaluation": [_CRITERIO], "unmet_criteria_ids": []}
# B.2 avalia o conjunto efetivo da tarefa: o critério planejado e o técnico fixo `T1-TECH`.
_APROVADO_LOCAL = {
    "decision": "approved",
    "criteria_evaluation": [_CRITERIO, {"criterion_id": "T1-TECH", "met": True, "justification": "Fundamentado"}],
    "unmet_criteria_ids": [],
}
_TAREFA = {
    "id": "T1",
    "title": "Resolver",
    "description": "Escolher alternativa",
    "acceptance_criteria": [{"id": "AC1", "description": "Escolher uma alternativa"}],
}


def _roteiro_ralph(resposta: str) -> list[str]:
    return [
        json.dumps({"general_acceptance_criteria": [{"id": "AC1", "description": "Responder"}]}),
        json.dumps({"tasks": [_TAREFA]}),
        json.dumps({"approved": True, "issues": []}),
        json.dumps({"learnings": []}),
        json.dumps({"task_id": "T1", "result": "resolvido", "conclusion": "resolvido"}),
        json.dumps(_APROVADO_LOCAL),
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
    monkeypatch.setenv("LLM_MAX_TOKENS", "120000")
    monkeypatch.setenv("RALPH_FINAL_ANSWER_TOKEN_RESERVE", "4000")
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
            "max_tokens": 50000,
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


def _resposta_certa_da_primeira_questao() -> str:
    """Resposta correta da primeira questão do dataset real, sem fixar uma letra no teste."""
    primeira = FileBenchmarkQuestionProvider(Settings(), logging.getLogger("teste.dataset")).list_questions()[0]
    return f"RESPOSTA_FINAL: {primeira.expected_alternative}"


def _sessoes_gravadas(diretorio: Path) -> list[dict[str, Any]]:
    return [json.loads(path.read_text(encoding="utf-8")) for path in sorted(diretorio.glob("*.json"))]


@pytest.mark.parametrize("few_shot", [0, 5])
def test_mmlu_executa_os_dois_fluxos_preserva_protocolo_e_exporta_a_origem_correta(
    ambiente: Path, monkeypatch: pytest.MonkeyPatch, few_shot: int,
) -> None:
    provider = MMLUBenchmarkQuestionProvider(few_shot)
    question = select_mmlu_questions(provider.list_questions(), ("college_physics",), 1, 123)[0]
    correct = f"RESPOSTA_FINAL: {question.expected_alternative}"
    wrong = "RESPOSTA_FINAL: " + next(letter for letter in "ABCD" if letter != question.expected_alternative)
    transport = _Provedor([correct, *_roteiro_ralph(wrong)])
    client = _cliente(monkeypatch, transport)

    descriptor = client.get("/v1/benchmark/questions?benchmark=mmlu")
    assert descriptor.status_code == 200
    assert len(descriptor.json()["question_ids"]) == 14042
    assert len(descriptor.json()["subjects"]) == 57

    frames, code = _executar(client, _abertura(
        benchmark="mmlu", few_shot=few_shot, subjects=["college_physics"], sample_seed=123, question_count=1,
    ))
    assert code == 1000
    session = frames[-1]["benchmark_session"]
    assert session["benchmark"] == {
        "dataset": "mmlu", "revision": MMLU_REVISION, "protocol": f"generative_{few_shot}shot",
        "split": "test", "few_shot": few_shot, "subjects": ["college_physics"], "sample_seed": 123,
    }
    assert session["questions"][0]["question_id"] == question.id
    assert session["questions"][0]["subject"] == "college_physics"
    assert session["summary"]["simple"]["accuracy"] == 1
    assert session["summary"]["ralph"]["accuracy"] == 0
    assert client.get(f"/v1/benchmark/sessions/{session['id']}").json() == session
    children = _sessoes_gravadas(ambiente / "sessions")
    assert len(children) == 2
    prompts = {child["user_question"] for child in children}
    assert len(prompts) == 1
    prompt = prompts.pop()
    assert question.statement in prompt
    assert prompt.count("Answer: ") == few_shot
    assert correct not in prompt

    export = client.get(f"/v1/benchmark/sessions/{session['id']}/ralph-loop-errors/export")
    assert export.status_code == 200
    with zipfile.ZipFile(io.BytesIO(export.content)) as archive:
        exported = json.loads(archive.read(f"questao-{question.id}/questao.json"))
        assert exported["statement"] == question.statement
        assert exported["options"] == question.options
    assert client.get("/v1/benchmark/questions").json()["benchmark"]["dataset"] == "vestibular"


@pytest.mark.parametrize("subset,count", [("diamond", 198), ("main", 448), ("extended", 546)])
def test_gpqa_executa_os_dois_fluxos_preserva_protocolo_e_exporta_a_origem_correta(
    ambiente: Path, monkeypatch: pytest.MonkeyPatch, subset: str, count: int,
) -> None:
    provider = GPQABenchmarkQuestionProvider(subset=subset)
    question = select_mmlu_questions(provider.list_questions(), ("physics",), 1, 123)[0]
    correct = f"RESPOSTA_FINAL: {question.expected_alternative}"
    wrong = "RESPOSTA_FINAL: " + next(letter for letter in "ABCD" if letter != question.expected_alternative)
    transport = _Provedor([correct, *_roteiro_ralph(wrong)])
    client = _cliente(monkeypatch, transport)

    suffix = f"&gpqa_subset={subset}" if subset != "diamond" else ""
    descriptor = client.get(f"/v1/benchmark/questions?benchmark=gpqa{suffix}")
    assert descriptor.status_code == 200
    assert len(descriptor.json()["question_ids"]) == count
    assert len(descriptor.json()["subjects"]) == 3

    frames, code = _executar(client, _abertura(
        benchmark="gpqa", few_shot=0, subjects=["physics"], sample_seed=123, question_count=1,
        **({"gpqa_subset": subset} if subset != "diamond" else {}),
    ))
    assert code == 1000
    session = frames[-1]["benchmark_session"]
    assert session["benchmark"] == {
        "dataset": "gpqa", "revision": GPQA_REVISION, "protocol": "generative_0shot",
        "split": subset, "few_shot": 0, "subjects": ["physics"], "sample_seed": 123,
    }
    assert session["questions"][0]["question_id"] == question.id
    assert session["questions"][0]["subject"] == "physics"
    assert session["summary"]["simple"]["accuracy"] == 1
    assert session["summary"]["ralph"]["accuracy"] == 0
    assert client.get(f"/v1/benchmark/sessions/{session['id']}").json() == session
    children = _sessoes_gravadas(ambiente / "sessions")
    assert len(children) == 2
    prompts = {child["user_question"] for child in children}
    assert len(prompts) == 1
    prompt = prompts.pop()
    assert question.statement in prompt
    assert prompt.count("Answer: ") == 0
    assert correct not in prompt

    export = client.get(f"/v1/benchmark/sessions/{session['id']}/ralph-loop-errors/export")
    assert export.status_code == 200
    with zipfile.ZipFile(io.BytesIO(export.content)) as archive:
        exported = json.loads(archive.read(f"questao-{question.id}/questao.json"))
        assert exported["statement"] == question.statement
        assert exported["options"] == question.options
    assert client.get("/v1/benchmark/questions").json()["benchmark"]["dataset"] == "vestibular"

    # O rerun usa a mesma permutação e corrige apenas o fluxo que errou.
    transport.respostas.extend(_roteiro_ralph(correct))
    path = f"/v1/benchmark/sessions/{session['id']}/questions/{question.id}/rerun"
    with client.websocket_connect(path) as socket:
        while True:
            frame = socket.receive_json()
            if frame["type"] == "result":
                break
    rerun_session = frame["benchmark_session"]
    assert rerun_session["benchmark"] == session["benchmark"]
    assert rerun_session["questions"][0]["expected_alternative"] == question.expected_alternative
    assert rerun_session["summary"]["ralph"]["accuracy"] == 1
    assert rerun_session["questions"][0]["simple"] == session["questions"][0]["simple"]


@pytest.mark.parametrize("options", [
    {"benchmark": "gpqa", "gpqa_subset": "unknown"},
    {"benchmark": "mmlu", "gpqa_subset": "main"},
    {"benchmark": "gpqa", "gpqa_subset": "main", "subjects": ["biology"], "question_count": 79},
    {"benchmark": "gpqa", "gpqa_subset": "extended", "subjects": ["biology"], "question_count": 106},
    {"benchmark": "gpqa", "few_shot": 5},
    {"benchmark": "gpqa", "sample_seed": -1},
    {"benchmark": "gpqa", "subjects": ["unknown"]},
    {"benchmark": "gpqa", "subjects": ["biology"], "question_count": 20},
    {"benchmark": "outro"}, {"benchmark": "mmlu", "few_shot": 3},
    {"benchmark": "vestibular", "few_shot": 5}, {"subjects": ["college_physics"]},
    {"benchmark": "mmlu", "sample_seed": -1},
    {"benchmark": "mmlu", "subjects": ["inexistente"]},
    {"benchmark": "mmlu", "subjects": ["college_physics"], "question_count": 103},
])
def test_opcoes_de_benchmark_invalidas_nao_criam_bateria_nem_chamam_modelo(
    ambiente: Path, monkeypatch: pytest.MonkeyPatch, options: dict,
) -> None:
    transport = _Provedor([])
    frames, code = _executar(_cliente(monkeypatch, transport), _abertura(**options))
    assert code == 1003
    assert frames[-1]["type"] == "error"
    assert transport.enviados == []
    assert not (ambiente / "benchmark-sessions").exists()


def test_bateria_executa_as_primeiras_questoes_e_grava_a_benchmark_session(
    ambiente: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # ENEM 2022 Q92 (D) e Q98 (E): simples acerta só a primeira, Ralph acerta ambas.
    provedor = _Provedor(
        ["RESPOSTA_FINAL: D", *_roteiro_ralph("RESPOSTA_FINAL: D"), "RESPOSTA_FINAL: A", *_roteiro_ralph("E")]
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
        "BIOLOGIA_ENEM_2022_AZUL_Q092",
        "BIOLOGIA_ENEM_2022_AZUL_Q098",
    ]
    assert bateria["summary"]["simple"]["correct"] == 1
    assert bateria["summary"]["simple"]["wrong"] == 1
    assert bateria["summary"]["ralph"]["correct"] == 2
    assert bateria["summary"]["ralph"]["accuracy"] == 1.0
    assert bateria["total_tokens"] == 20 * 15  # 2 inferências simples + 2 Ralph de 9 chamadas (com A.3)
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
    monkeypatch.setattr(mongo_client_adapter, "AsyncIOMotorClient", lambda *args, **kwargs: cliente_mongo)
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

    assert len(dataset["question_ids"]) == 270
    assert dataset["question_ids"][0] == "BIOLOGIA_ENEM_2022_AZUL_Q092"
    assert dataset["max_parallel_limit"] == 10
    assert dataset["max_tokens_limit"] == 120000
    assert listagem == {"benchmark_sessions": [bateria]}
    assert detalhe.status_code == 200
    assert detalhe.json() == bateria


def test_quantidade_acima_do_dataset_e_recusada_antes_de_qualquer_chamada(
    ambiente: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    provedor = _Provedor([])

    frames, codigo = _executar(_cliente(monkeypatch, provedor), _abertura(question_count=271))

    assert codigo == 1003
    assert frames == [{"type": "error", "content": frames[0]["content"]}]
    assert "question_count" in frames[0]["content"]
    assert provedor.enviados == []
    assert not (ambiente / "benchmark-sessions").exists()


def test_bateria_completa_usa_as_270_questoes_nos_dois_fluxos(
    ambiente: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    questoes = FileBenchmarkQuestionProvider(Settings(), logging.getLogger("teste.dataset")).list_questions()
    respostas = []
    for questao in questoes:
        resposta = f"RESPOSTA_FINAL: {questao.expected_alternative}"
        respostas.extend([resposta, *_roteiro_ralph(resposta)])
    provedor = _Provedor(respostas)

    frames, codigo = _executar(_cliente(monkeypatch, provedor), _abertura(question_count=270))

    assert codigo == 1000
    assert not provedor.respostas
    bateria = frames[-1]["benchmark_session"]
    assert bateria["status"] == "completed"
    assert bateria["progress"]["finished"] == 270
    assert [item["question_id"] for item in bateria["questions"]] == [questao.id for questao in questoes]
    assert bateria["summary"]["simple"]["correct"] == 270
    assert bateria["summary"]["ralph"]["correct"] == 270
    assert len(bateria["session_ids"]) == 540
    assert len(provedor.enviados) == 270 * 10


@pytest.mark.parametrize("max_tokens", [120_001, 10_000_000, 1_000_000_000])
def test_max_tokens_acima_do_limite_por_sessao_do_backend_e_recusado_sem_chamar_o_provedor(
    ambiente: Path, monkeypatch: pytest.MonkeyPatch, max_tokens: int
) -> None:
    """O limite por sessão pedido nunca passa de `LLM_MAX_TOKENS`: a bateria nem é criada."""
    provedor = _Provedor([])
    abertura = _abertura(question_count=1)
    abertura["llm_model_config"]["max_tokens"] = max_tokens

    frames, codigo = _executar(_cliente(monkeypatch, provedor), abertura)

    assert codigo == 1003
    assert "limite de tokens por sessão do backend (120000)" in frames[0]["content"]
    assert provedor.enviados == []
    assert not (ambiente / "benchmark-sessions").exists()
    assert not (ambiente / "sessions").exists()


def test_max_tokens_no_limite_do_backend_roda_os_dois_fluxos_com_o_guardiao_de_custo_real(
    ambiente: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """O limite é da sessão: cada chamada do Ralph pede só o saldo que resta dele."""
    certa = _resposta_certa_da_primeira_questao()
    provedor = _Provedor([certa, *_roteiro_ralph(certa)])
    abertura = _abertura(question_count=1)
    abertura["llm_model_config"]["max_tokens"] = 120000

    frames, codigo = _executar(_cliente(monkeypatch, provedor), abertura)

    assert codigo == 1000
    bateria = frames[-1]["benchmark_session"]
    assert bateria["max_tokens"] == 120000
    assert bateria["summary"]["simple"]["correct"] == 1
    assert bateria["summary"]["ralph"]["correct"] == 1
    assert bateria["summary"]["ralph"]["failures"] == 0
    assert len(provedor.enviados) == 10
    simples, *ralph = [corpo["max_tokens"] for corpo in provedor.enviados]
    assert simples == 120000
    # A.1 enxerga o orçamento de trabalho inteiro; cada chamada seguinte, só o que sobrou dele.
    assert ralph[0] == 120000 - 4000
    assert ralph[1] == ralph[0] - 15


def test_limite_da_sessao_que_nao_comporta_a_reserva_falha_o_ralph_sem_chamar_o_modelo(
    ambiente: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    provedor = _Provedor([_resposta_certa_da_primeira_questao()])
    abertura = _abertura(question_count=1)
    abertura["llm_model_config"]["max_tokens"] = 4000

    frames, codigo = _executar(_cliente(monkeypatch, provedor), abertura)

    assert codigo == 1000
    bateria = frames[-1]["benchmark_session"]
    assert bateria["summary"]["simple"]["correct"] == 1
    assert bateria["summary"]["ralph"]["failures"] == 1
    assert "RALPH_FINAL_ANSWER_TOKEN_RESERVE" in bateria["questions"][0]["ralph"]["error"]
    assert len(provedor.enviados) == 1


@pytest.mark.parametrize("query", ["benchmark=gpqa&gpqa_subset=unknown", "benchmark=mmlu&gpqa_subset=main"])
def test_descricao_recusa_subconjunto_invalido(ambiente: Path, monkeypatch: pytest.MonkeyPatch, query: str) -> None:
    client = _cliente(monkeypatch, _Provedor([]))
    assert client.get(f"/v1/benchmark/questions?{query}").status_code == 422


def test_bateria_por_materia_executa_as_cotas_nos_dois_fluxos_e_persiste_a_distribuicao(
    ambiente: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    questions = FileBenchmarkQuestionProvider(Settings(), logging.getLogger("teste.cotas")).list_questions()
    selected = [q for q in questions if q.subject == "BIOLOGIA"][:1] + [
        q for q in questions if q.subject == "MATEMATICA"
    ][:2]
    responses = []
    for question in selected:
        correct = f"RESPOSTA_FINAL: {question.expected_alternative}"
        responses.extend([correct, *_roteiro_ralph(correct)])
    provider = _Provedor(responses)
    client = _cliente(monkeypatch, provider)
    frames, code = _executar(client, _abertura(
        question_count=3, subject_counts={"BIOLOGIA": 1, "MATEMATICA": 2, "FISICA": 0},
    ))
    assert code == 1000
    final = frames[-1]["benchmark_session"]
    assert [q["question_id"] for q in final["questions"]] == [q.id for q in selected]
    assert [q["subject"] for q in final["questions"]] == ["BIOLOGIA", "MATEMATICA", "MATEMATICA"]
    assert final["summary"]["simple"]["correct"] == final["summary"]["ralph"]["correct"] == 3
    assert len(final["session_ids"]) == 6
    assert len(provider.enviados) == 30
    assert client.get(f"/v1/benchmark/sessions/{final['id']}").json() == final


@pytest.mark.parametrize("counts, count", [
    ({}, None), ({"MATEMATICA": 0}, None), ({"INEXISTENTE": 1}, None),
    ({"HISTORIA": 31}, None), ({"MATEMATICA": 51}, None), ({"FISICA": 2}, 3),
])
def test_cotas_invalidas_sao_recusadas_antes_de_criar_bateria_ou_chamar_llm(
    ambiente: Path, monkeypatch: pytest.MonkeyPatch, counts: dict, count: int | None,
) -> None:
    provider = _Provedor([])
    frames, code = _executar(_cliente(monkeypatch, provider), _abertura(
        question_count=count, subject_counts=counts,
    ))
    assert code == 1003
    assert frames[-1]["type"] == "error"
    assert "subject_counts" in frames[-1]["content"]
    assert not provider.enviados
    assert not (ambiente / "benchmark-sessions").exists()
