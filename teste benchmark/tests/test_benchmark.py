"""Testes sem rede: fila, avaliação e integração com os dois fluxos reais."""

import asyncio
import json
import sys
from collections import deque
from pathlib import Path

import pytest

MODULE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE))

from benchmark import (  # noqa: E402
    MODEL, Question, Reply, load_questions, run_benchmark, selected_answer, write_reports,
)


def question(identifier="Q1"):
    return Question(identifier, "Pergunta\n\nA) um\nB) dois\nC) três\nD) quatro\nE) cinco", {
        "A": "um", "B": "dois", "C": "três", "D": "quatro", "E": "cinco",
    }, "A")


@pytest.mark.parametrize("response,expected", [
    ("A", "A"), ("A) um", "A"), ("Descarto B e C.\nRESPOSTA_FINAL: A", "A"),
    ("**RESPOSTA_FINAL: B**", "B"), ("A ou B", None), ("A) dois", None),
    ("RESPOSTA_FINAL: A\nRESPOSTA_FINAL: B", None),
    ("RESPOSTA_FINAL: F", None), ("RESPOSTA_FINAL: A\nAfinal, B.", None), ("", None),
])
def test_avalia_somente_uma_escolha_inequivoca(response, expected):
    assert selected_answer(response, question().options) == expected


def test_dataset_real_tem_quinze_questoes_validas():
    questions = load_questions(MODULE / "QUESTOES_BENCHMARK")
    assert len(questions) == 15
    assert all(len(item.options) == 5 for item in questions)


def test_recusa_gabarito_com_texto_diferente(tmp_path):
    folder = tmp_path / "Q1"
    folder.mkdir()
    (folder / "enunciado.md").write_text(question().statement)
    (folder / "alternativa_correta.md").write_text("A) outro texto")
    with pytest.raises(ValueError, match="Texto do gabarito"):
        load_questions(tmp_path)


def test_fila_tem_cinco_questoes_ativas_e_sequencia_por_questao(tmp_path):
    class FakeFlows:
        def __init__(self):
            self.active = set()
            self.maximum = 0
            self.started = []
            self.prompts = {}
            self.ralph_finished = set()
            self.five_started = asyncio.Event()

        async def simple(self, question_id, prompt):
            self.active.add(question_id)
            self.maximum = max(self.maximum, len(self.active))
            self.started.append(question_id)
            self.prompts[question_id] = prompt
            if len(self.active) == 5:
                self.five_started.set()
            await asyncio.wait_for(self.five_started.wait(), 2)
            if question_id == "Q0":
                raise RuntimeError("falha da inferência simples")
            return Reply("RESPOSTA_FINAL: B")

        async def ralph(self, question_id, prompt):
            assert question_id in self.active
            assert prompt == self.prompts[question_id]
            assert prompt == question(question_id).statement + "\n\nInstrução comum"
            await asyncio.sleep(0)
            self.active.remove(question_id)
            self.ralph_finished.add(question_id)
            return Reply("RESPOSTA_FINAL: A")

    flows = FakeFlows()
    questions = [question(f"Q{i}") for i in range(12)]
    results = asyncio.run(run_benchmark(questions, flows, "Instrução comum", output=tmp_path))
    assert flows.maximum == 5
    assert flows.started == [item.id for item in questions]
    assert flows.ralph_finished == {item.id for item in questions}
    assert [item.question_id for item in results] == flows.started
    assert all(item.ralph.correct for item in results)
    assert not any(item.simple.correct for item in results)
    write_reports(tmp_path, results, {"model": MODEL, "concurrency": 5})
    report = json.loads((tmp_path / "resultados.json").read_text())
    assert report["totais"]["simple"] == {"acertos": 0, "erros": 12, "falhas": 1, "nao_executadas": 0}
    assert report["totais"]["ralph"] == {"acertos": 12, "erros": 0, "falhas": 0, "nao_executadas": 0}
    assert "| RALPH LOOP adaptado | 12 | 0 | 100.0% |" in (tmp_path / "relatorio.md").read_text()
    assert len(list(tmp_path.glob("Q*.json"))) == 12


def test_falha_do_ralph_nao_impede_proximas_questoes():
    class FakeFlows:
        async def simple(self, question_id, prompt):
            return Reply("RESPOSTA_FINAL: A")

        async def ralph(self, question_id, prompt):
            if question_id == "Q1":
                raise RuntimeError("limite do Ralph")
            return Reply("Não sei")

    results = asyncio.run(run_benchmark([question("Q1"), question("Q2")], FakeFlows(), "instrução", 1))
    assert all(item.simple.correct for item in results)
    assert "limite do Ralph" in results[0].ralph.error
    assert "sem alternativa" in results[1].ralph.error
    assert not any(item.ralph.correct for item in results)


def test_backend_real_usa_modelo_em_todas_as_fases_sem_rede(tmp_path, monkeypatch):
    import httpx

    from backend import BackendFlows, configure_backend

    monkeypatch.setenv("OPENROUTER_API_KEY", "somente-teste")
    monkeypatch.setenv("RALPH_PROMPT_TEMPLATES_PATH", str(MODULE.parent / "apps/backend/src/infra/templates"))
    for name in ("LLM_PROVIDER", "LLM_MODEL", "GENAI_AVAILABLE_MODELS", "GENAI_AVAILABLE_PROVIDERS",
                 "RALPH_SESSION_STORAGE_BACKEND", "RALPH_SESSIONS_STORAGE_PATH"):
        monkeypatch.setenv(name, "anterior")
    configure_backend(MODULE.parent, tmp_path, tmp_path / "inexistente.env")
    from src.infra.services.llm_service_factory import LLMServiceFactory
    from src.infra.services.openrouter_service import OpenRouterService

    criterion = {"criterion_id": "AC1", "met": True, "justification": "Atende"}
    approved = {"decision": "approved", "criteria_evaluation": [criterion], "unmet_criteria_ids": []}
    task = {
        "id": "T1", "title": "Resolver", "description": "Escolher alternativa",
        "expected_input": "Questão", "expected_output": "Alternativa",
        "acceptance_criteria": [{"id": "AC1", "description": "Escolher uma alternativa"}],
    }
    scripted = deque([
        "RESPOSTA_FINAL: A",
        json.dumps({"general_acceptance_criteria": [{"id": "AC1", "description": "Responder"}]}),
        json.dumps({"tasks": [task]}), json.dumps({"learnings": []}),
        json.dumps({"task_id": "T1", "result": "A"}), json.dumps(approved),
        json.dumps({"learnings": []}), json.dumps(approved),
        json.dumps({"final_answer": "RESPOSTA_FINAL: A"}),
    ])
    sent = []

    def handler(request):
        sent.append(json.loads(request.content))
        return httpx.Response(200, json={
            "choices": [{"message": {"content": scripted.popleft()}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 10},
        })

    def services(factory):
        return [OpenRouterService(
            logger=factory.settings.logger(__file__), settings=factory.settings,
            transport=httpx.MockTransport(handler),
        )]

    monkeypatch.setattr(LLMServiceFactory, "create_all", services)
    results = asyncio.run(run_benchmark([question()], BackendFlows(tmp_path, 4096, 0.0), "instrução"))
    assert results[0].simple.correct, results[0].simple.error
    assert results[0].ralph.correct, results[0].ralph.error
    assert not scripted
    assert len(sent) == 9
    assert all(payload["model"] == MODEL and payload["temperature"] == 0 for payload in sent)
    assert results[0].simple.session_id != results[0].ralph.session_id
    sessions = [json.loads(path.read_text()) for path in (tmp_path / "sessions").glob("*.json")]
    assert len(sessions) == 2
    assert all(session["status"] == "completed" and session["model_name"] == MODEL for session in sessions)
    events = [json.loads(line) for line in (tmp_path / "Q1_ralph_eventos.jsonl").read_text().splitlines()]
    assert events[-1]["type"] == "result"
