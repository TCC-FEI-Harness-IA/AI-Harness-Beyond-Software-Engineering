"""Refinamentos 03 pelo fluxo completo: procedência, feedback das retentativas, matrizes e apresentação.

Usam os templates, o parser, a fila, a memória, o livro de resultados e o recorder reais, com saídas do
modelo roteirizadas. Provam o material entregue a cada fase, o transporte do feedback, a separação entre
conteúdo e procedência e a ausência de fase ou chamada nova. Não provam que um modelo real identifica o
defeito certo, corrige a objeção ou apresenta o identificador correto: isso é avaliação semântica, com as
matrizes `decomposition_validation_v2.json`, `technical_validation_v2.json` e `final_answer_fidelity_v1.json`.
"""
import json
import logging
import re
from pathlib import Path
from typing import Any

import pytest

from src.domain.entities.thinking.learning import Learning
from src.domain.enums.session_status_enum import SessionStatusEnum
from src.domain.enums.thinking_event_subtype_enum import ThinkingEventSubtypeEnum as Sub
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum as Phase
from src.infra.config.settings import Settings
from src.infra.providers.file_prompt_template_provider import FilePromptTemplateProvider
from tests.doubles.fake_cost_guard import FakeCostGuard
from tests.doubles.ralph_scenario import RalphScenario
from tests.doubles.ralph_scripts import (
    anotacoes_do_enunciado,
    aprendizados,
    criterios,
    global_aprovado,
    plano_aprovado,
    resposta_final,
)

_FIXTURES = Path(__file__).parents[2] / "fixtures"
_TECH_V2 = json.loads((_FIXTURES / "technical_validation_v2.json").read_text(encoding="utf-8"))
_PLAN_V2 = json.loads((_FIXTURES / "decomposition_validation_v2.json").read_text(encoding="utf-8"))
_FINAL = json.loads((_FIXTURES / "final_answer_fidelity_v1.json").read_text(encoding="utf-8"))
_SESSAO = 0.2


def _provider() -> FilePromptTemplateProvider:
    return FilePromptTemplateProvider(settings=Settings(), logger=logging.getLogger("teste.refinamentos"))


def _cenario(roteiro: list, **kwargs: Any) -> RalphScenario:
    return RalphScenario(responses=roteiro, temperature=_SESSAO, template_provider=_provider(),
                         cost_guard=FakeCostGuard(), **kwargs)


def _tarefa(task_id: str, titulo: str, descricao: str, criterios_: list[dict], **extra: Any) -> dict:
    return {"id": task_id, "title": titulo, "description": descricao, "acceptance_criteria": criterios_, **extra}


def _plano(*tarefas: dict) -> str:
    return json.dumps({"tasks": list(tarefas)})


def _resolucao(task_id: str, texto: str) -> str:
    return json.dumps({"task_id": task_id, "result": texto, "conclusion": texto})


def _relatorio(met: dict[str, bool], justificativa: str = "conferido") -> str:
    unmet = [criterion_id for criterion_id, value in met.items() if not value]
    return json.dumps({
        "criteria_evaluation": [
            {"criterion_id": criterion_id, "met": value, "justification": justificativa if not value else "conferido"}
            for criterion_id, value in met.items()
        ],
        "unmet_criteria_ids": unmet,
        "decision": "reproved" if unmet else "approved",
    })


def _aprova(*ids: str) -> str:
    return _relatorio({criterion_id: True for criterion_id in ids})


def _indices(cenario: RalphScenario, fase: Phase, task_id: str | None = None) -> list[int]:
    return [i for i, invocacao in enumerate(cenario.session.invocations)
            if invocacao.phase is fase and invocacao.recovers_invocation_id is None
            and (task_id is None or invocacao.task_id == task_id)]


def _prompts(cenario: RalphScenario, fase: Phase, task_id: str | None = None) -> list[str]:
    return [cenario.llm.texts_of(i)[0] for i in _indices(cenario, fase, task_id)]


def _area(prompt: str, titulo: str) -> str:
    conteudo = prompt.split(f"## {titulo}\n", 1)[1]
    return re.split(r"\n## (?!T\d+\b)", conteudo, maxsplit=1)[0].strip()


def _rotulo(fonte: str | None) -> str:
    return "Question" if fonte is None else f"Task {fonte}"


# ── Procedência: do registro até B/C, sem contaminar conteúdo nem resultados ─


_DADO = "Prazo maximo do contrato: 10 dias."
_ESTIMATIVA = "Duracao estimada de 8 dias, supondo disponibilidade integral da equipe."
_T1 = _tarefa("T1", "Estimar a duracao", "Estime a duracao do projeto com as hipoteses.",
              [{"id": "T1-AC1", "description": "Estimar com hipoteses."}])
_T2 = _tarefa("T2", "Avaliar o prazo", "Avalie se o projeto cabe no prazo, com as condicoes.",
              [{"id": "T2-AC1", "description": "Concluir com condicoes."}], depends_on=["T1"])


async def test_procedencia_chega_rotulada_a_b_e_c_sem_virar_criterio_resultado_ou_conteudo() -> None:
    cenario = _cenario([
        criterios(), _plano(_T1, _T2), plano_aprovado(), anotacoes_do_enunciado(_DADO),
        _resolucao("T1", "RESULTADO-T1"), _aprova("T1-AC1", "T1-TECH"), aprendizados(_ESTIMATIVA),
        # T2 reestabelece a estimativa e a copia sem o rótulo, como o template de B.4 orienta.
        _resolucao("T2", "RESULTADO-T2"), _aprova("T2-AC1", "T2-TECH"), aprendizados(_ESTIMATIVA),
        global_aprovado(), resposta_final("RESPOSTA"),
    ])

    await cenario.run(question="PERGUNTA")

    assert cenario.learnings_memory.all() == (
        Learning(content=_DADO), Learning(content=_ESTIMATIVA, source_task_id="T1"),
    )
    b1_t2, = _prompts(cenario, Phase.B1_TASK_RESOLUTION, "T2")
    assert _area(b1_t2, "Key Learnings").endswith(f"- [Question] {_DADO}\n- [Task T1] {_ESTIMATIVA}")
    b2_t2, = _prompts(cenario, Phase.B2_TASK_VERIFICATION, "T2")
    assert f"- [Task T1] {_ESTIMATIVA}" in _area(b2_t2, "Key Learnings")
    assert "[Task T1]" not in _area(b2_t2, "Acceptance criteria for this task")
    b4_t2, = _prompts(cenario, Phase.B4_LEARNINGS_EXTRACTION, "T2")
    assert f"- [Task T1] {_ESTIMATIVA}" in _area(b4_t2, "Key Learnings")
    c1, = _prompts(cenario, Phase.C1_GLOBAL_VERIFICATION)
    c3, = _prompts(cenario, Phase.C3_FINAL_ANSWER)
    for prompt in (c1, c3):
        memoria = _area(prompt, "Key Learnings")
        assert f"- [Question] {_DADO}\n- [Tasks T1, T2] {_ESTIMATIVA}" in memoria
        resultados = _area(prompt, "Stored results")
        assert "[Task" not in resultados and "[Question]" not in resultados and _ESTIMATIVA not in resultados
    learn_t2 = [m for m in cenario.session.messages if m.subtype is Sub.LEARN and m.task_id == "T2"]
    assert learn_t2 and all("[Task" not in m.content and "[Question]" not in m.content for m in learn_t2)
    assert cenario.session.status is SessionStatusEnum.COMPLETED


async def test_retirada_e_restauracao_das_fontes_atualizam_a_procedencia_exibida_apos_o_fluxo() -> None:
    cenario = _cenario([criterios(), _plano(_T1), plano_aprovado(), anotacoes_do_enunciado(_DADO),
                        _resolucao("T1", "RESULTADO-T1"), _aprova("T1-AC1", "T1-TECH"), aprendizados(_ESTIMATIVA),
                        global_aprovado(), resposta_final()])
    await cenario.run()
    memoria = cenario.learnings_memory
    memoria.append(learnings=[Learning(content=_ESTIMATIVA, source_task_id="T4")])

    memoria.withdraw(task_ids=("T1",))
    assert memoria.render() == f"- [Question] {_DADO}\n- [Task T4] {_ESTIMATIVA}"
    memoria.withdraw(task_ids=("T4",))
    assert memoria.render() == f"- [Question] {_DADO}"
    memoria.restore(task_ids=("T1", "T4"))
    assert memoria.render() == f"- [Question] {_DADO}\n- [Tasks T1, T4] {_ESTIMATIVA}"


# ── 5.1: o feedback chega pelos canais existentes, com a orientação nova ───


async def test_retentativa_de_b1_recebe_parecer_e_orientacao_e_b2_seguinte_avalia_so_o_atual() -> None:
    parecer = "PARECER: a raiz alegada nao satisfaz a equacao ao ser substituida."
    cenario = _cenario([
        criterios(), _plano(_tarefa("T1", "Resolver", "Resolva x^2 = 9.", [{"id": "T1-AC1", "description": "Valor."}])),
        plano_aprovado(), anotacoes_do_enunciado(),
        _resolucao("T1", "TENTATIVA-1: x = 2."), _relatorio({"T1-AC1": True, "T1-TECH": False}, parecer),
        _resolucao("T1", "TENTATIVA-2: x = 3; 3^2 = 9."), _aprova("T1-AC1", "T1-TECH"), aprendizados(),
        global_aprovado(), resposta_final(),
    ])

    await cenario.run()

    primeira, segunda = _prompts(cenario, Phase.B1_TASK_RESOLUTION)
    anteriores = _area(segunda, "Previous attempts at this task")
    assert "TENTATIVA-1" in anteriores and parecer in anteriores
    assert "Confront each objection" in anteriores
    assert "restrictions you assumed yourself" in anteriores
    assert "None: this is the first attempt" in _area(primeira, "Previous attempts at this task")
    _, segunda_b2 = _prompts(cenario, Phase.B2_TASK_VERIFICATION)
    assert parecer not in segunda_b2 and "TENTATIVA-1" not in segunda_b2
    assert _area(segunda_b2, "Preliminary result").endswith("TENTATIVA-2: x = 3; 3^2 = 9.")
    b1 = [i.temperature for i in cenario.session.invocations if i.phase is Phase.B1_TASK_RESOLUTION]
    b2 = [i.temperature for i in cenario.session.invocations if i.phase is Phase.B2_TASK_VERIFICATION]
    assert b1 == [_SESSAO, 1.0] and b2 == [_SESSAO, _SESSAO]


# ── Matriz de A.3 pelo ciclo de planejamento ───────────────────────────────


@pytest.mark.parametrize("caso", _PLAN_V2["cases"], ids=lambda caso: caso["name"])
async def test_matriz_de_a3_percorre_o_ciclo_sem_vazar_referencia(caso: dict[str, Any]) -> None:
    relatorio = caso.get("contradictory_report", caso["reference_report"])
    aprovado_de_primeira = relatorio["approved"]
    roteiro = [criterios(), _plano(*caso["tasks"]), json.dumps(relatorio)]
    if not aprovado_de_primeira:
        roteiro += [_plano(*caso["tasks"]), plano_aprovado()]
    roteiro.append(anotacoes_do_enunciado())
    ids = [tarefa["id"] for tarefa in caso["tasks"]]
    for task_id in ids:
        planejados = [c["id"] for t in caso["tasks"] if t["id"] == task_id for c in t["acceptance_criteria"]]
        roteiro += [
            _resolucao(task_id, f"RESULTADO-{task_id}"), _aprova(*planejados, f"{task_id}-TECH"), aprendizados(),
        ]
    cenario = _cenario([*roteiro, global_aprovado(), resposta_final()])

    await cenario.run(question=caso["question"])

    a2 = _prompts(cenario, Phase.A2_TASK_DECOMPOSITION)
    a3 = _prompts(cenario, Phase.A3_DECOMPOSITION_VALIDATION)
    for prompt in (*a2, *a3):
        assert caso["expected_review"] not in prompt
    assert len(a3) == (1 if aprovado_de_primeira else 2)
    if not aprovado_de_primeira:
        revisao = _area(a2[1], "Previous candidate and validation report")
        for issue in relatorio["issues"]:
            assert issue["problem"] in revisao and issue["adjustment"] in revisao
        assert "removes the concrete defect named by each issue" in revisao
        assert all(issue["problem"] not in a3[1] for issue in relatorio["issues"])
        assert [i.temperature for i in cenario.session.invocations
                if i.phase is Phase.A2_TASK_DECOMPOSITION] == [_SESSAO, 0.5]
    assert cenario.task_queue.total_created() == len(ids)
    assert cenario.session.status is SessionStatusEnum.COMPLETED


async def test_parecer_contraditorio_e_aceito_pelo_protocolo_e_so_a_avaliacao_semantica_o_detecta() -> None:
    [caso] = [caso for caso in _PLAN_V2["cases"] if "contradictory_report" in caso]
    roteiro = [criterios(), _plano(*caso["tasks"]), json.dumps(caso["contradictory_report"]),
               _plano(*caso["tasks"]), plano_aprovado(), anotacoes_do_enunciado(),
               _resolucao("T1", "R"), _aprova("T1-AC1", "T1-TECH"), aprendizados(), global_aprovado(), resposta_final()]
    cenario = _cenario(roteiro)

    eventos = await cenario.run(question=caso["question"])

    # Nenhum detector por palavras-chave: o harness não converte a reprovação nem chama outro juiz.
    assert [e.subtype for e in eventos].count(Sub.PLAN_REJECTED) == 1
    assert [i.phase for i in cenario.session.invocations].count(Phase.A3_DECOMPOSITION_VALIDATION) == 2


# ── Matriz técnica v2 pelo fluxo, com notas reais do enunciado e de T1 ─────


@pytest.mark.parametrize("caso", _TECH_V2["cases"], ids=lambda caso: caso["name"])
async def test_matriz_tecnica_v2_chega_a_b2_com_procedencia_real_e_feedback_sem_referencia(
    caso: dict[str, Any],
) -> None:
    da_pergunta = [nota["content"] for nota in caso["learnings"] if nota["source"] is None]
    de_t1 = [nota["content"] for nota in caso["learnings"] if nota["source"] == "T1"]
    t1 = _tarefa("T1", "Etapa anterior", "Etapa anterior do caso.", [{"id": "T1-AC1", "description": "Concluir."}])
    t2 = _tarefa("T2", caso["task"]["title"], caso["task"]["description"], caso["criteria"], depends_on=["T1"])
    referencia = caso["reference"]
    roteiro = [criterios(), _plano(t1, t2), plano_aprovado(), anotacoes_do_enunciado(*da_pergunta),
               _resolucao("T1", "RESULTADO-T1"), _aprova("T1-AC1", "T1-TECH"), aprendizados(*de_t1),
               _resolucao("T2", caso["preliminary_result"]), _relatorio(referencia["met"], referencia["rationale"])]
    corrigido = "RESOLUCAO-CORRIGIDA a partir do defeito apontado."
    if referencia["decision"] == "reproved":
        roteiro += [_resolucao("T2", corrigido), _aprova(*referencia["met"])]
    cenario = _cenario([*roteiro, aprendizados(), global_aprovado(), resposta_final()])

    await cenario.run(question=caso["task"]["description"])

    b2 = _prompts(cenario, Phase.B2_TASK_VERIFICATION, "T2")[0]
    memoria = _area(b2, "Key Learnings")
    for nota in caso["learnings"]:
        assert f"- [{_rotulo(nota['source'])}] {nota['content']}" in memoria
    for prompt in (*_prompts(cenario, Phase.A3_DECOMPOSITION_VALIDATION), b2):
        assert referencia["rationale"] not in prompt
        assert all(check not in prompt for check in caso["review_checks"])
    if referencia["decision"] == "reproved":
        retentativa = _prompts(cenario, Phase.B1_TASK_RESOLUTION, "T2")[1]
        assert referencia["rationale"] in _area(retentativa, "Previous attempts at this task")
        assert referencia["rationale"] not in _prompts(cenario, Phase.B2_TASK_VERIFICATION, "T2")[1]
        assert cenario.results_ledger.get(task_id="T2").content == corrigido
    else:
        assert cenario.results_ledger.get(task_id="T2").content == caso["preliminary_result"]


# ── Apresentação: C.3 recebe os resultados aprovados e as notas, nada mais ──


@pytest.mark.parametrize("caso", _FINAL["cases"], ids=lambda caso: caso["name"])
async def test_c3_recebe_resultado_aprovado_e_notas_rotuladas_sem_fase_nova(caso: dict[str, Any]) -> None:
    corpo = caso["stored_results"].split("\n\n", 1)[1]
    t1 = _tarefa("T1", "Determinacao", "Determine o pedido.", [{"id": "T1-AC1", "description": "Determinar."}])
    da_pergunta = [nota["content"] for nota in caso["learnings"] if nota["source"] is None]
    de_t1 = [nota["content"] for nota in caso["learnings"] if nota["source"] == "T1"]
    cenario = _cenario([
        criterios(), _plano(t1), plano_aprovado(), anotacoes_do_enunciado(*da_pergunta),
        _resolucao("T1", corpo), _aprova("T1-AC1", "T1-TECH"), aprendizados(*de_t1),
        global_aprovado(), resposta_final(caso["reference_answer"]),
    ])

    await cenario.run(question=caso["user_question"])

    c3, = _prompts(cenario, Phase.C3_FINAL_ANSWER)
    assert corpo in _area(c3, "Stored results")
    for nota in caso["learnings"]:
        assert f"- [{_rotulo(nota['source'])}] {nota['content']}" in _area(c3, "Key Learnings")
    for referencia in (caso["invalid_presentation"], *caso["review_checks"]):
        assert referencia not in c3
    assert "Global verification" not in c3 and "criteria_evaluation" not in c3
    assert cenario.session.invocations[-1].phase is Phase.C3_FINAL_ANSWER
    assert [i.phase for i in cenario.session.invocations].count(Phase.C3_FINAL_ANSWER) == 1
    assert cenario.session.final_answer == caso["reference_answer"]
