"""Validação, consistência e aproximações fundamentadas (thinking 04) com prompts reais.

Fases, provider de arquivos, parser, fila, memória e persistência são reais; as saídas do LLM,
inclusive os vereditos de B.2 e C.1, são roteirizadas a partir da matriz
`validation_semantics_v1.json`. Os testes demonstram a fiação — o que cada fase recebe e para
onde cada veredito leva o fluxo —, não que um modelo real reconhece aproximações, contradições
ou lacunas. Essa avaliação exige execução com modelo real e a rubrica da matriz.
"""
import json
import logging
import re
from pathlib import Path

import pytest

from src.domain.enums.output_problem_code_enum import OutputProblemCodeEnum
from src.domain.enums.recovery_result_enum import RecoveryResultEnum
from src.domain.enums.session_status_enum import SessionStatusEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum as Phase
from src.infra.providers.file_prompt_template_provider import FilePromptTemplateProvider
from tests.doubles.fake_settings import FakeSettings
from tests.doubles.ralph_scenario import RalphScenario
from tests.doubles.ralph_scripts import aprendizados, relatorio, resposta_final

_MATRIX = json.loads((Path(__file__).parents[2] / "fixtures/validation_semantics_v1.json").read_text())
_C1_APPROVED = [c for c in _MATRIX["cases"] if c["phase"] == "C1" and c["reference_decision"] == "approved"]
_C1_REPROVED = [c for c in _MATRIX["cases"] if c["phase"] == "C1" and c["reference_decision"] == "reproved"]
_B2_CASES = [c for c in _MATRIX["cases"] if c["phase"] == "B2"]
_PLANNING = [Phase.A1_GENERAL_CRITERIA, Phase.A2_TASK_DECOMPOSITION, Phase.A3_PLANNING_LEARNINGS]
_TASK_CYCLE = [Phase.B1_TASK_RESOLUTION, Phase.B2_TASK_VERIFICATION, Phase.B4_LEARNINGS_EXTRACTION]


def _json(**value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def _criteria(case: dict) -> str:
    return _json(general_acceptance_criteria=[
        {"id": item["id"], "description": item["description"]} for item in case["criteria"]
    ])


def _task(task_id: str, title: str, description: str, criterion: str = "Resultado explicado.") -> dict:
    return {"id": task_id, "title": title, "description": description,
            "acceptance_criteria": [{"id": f"{task_id}-AC1", "description": criterion}]}


def _plan(*tasks: dict) -> str:
    return _json(tasks=list(tasks))


def _result(task_id: str, text: str) -> str:
    return _json(task_id=task_id, result=text, conclusion=text)


def _report(evaluations: list[tuple[str, bool]], justification: str, decision: str | None = None) -> str:
    unmet = [criterion_id for criterion_id, met in evaluations if not met]
    return _json(
        criteria_evaluation=[{"criterion_id": criterion_id, "met": met, "justification": justification}
                             for criterion_id, met in evaluations],
        unmet_criteria_ids=unmet, decision=decision or ("reproved" if unmet else "approved"),
    )


def _global(case: dict, unmet: list[str], justification: str) -> str:
    return _report([(item["id"], item["id"] not in unmet) for item in case["criteria"]], justification)


def _scenario(responses: list[str]) -> RalphScenario:
    settings = FakeSettings()
    return RalphScenario(responses=responses, settings=settings, template_provider=FilePromptTemplateProvider(
        settings=settings, logger=logging.getLogger("test.validation.templates"),
    ))


def _phases(scenario: RalphScenario) -> list[Phase]:
    return [invocation.phase for invocation in scenario.session.invocations]


def _prompts(scenario: RalphScenario, phase: Phase) -> list[str]:
    return [scenario.llm.texts_of(index)[0] for index, invocation in enumerate(scenario.session.invocations)
            if invocation.phase is phase]


def _area(prompt: str, heading: str) -> str:
    content = prompt.split(f"## {heading}\n", 1)[1]
    return re.split(r"\n## (?!T\d+\b)", content, maxsplit=1)[0].strip()


def _flat(text: str) -> str:
    return " ".join(text.split())


def _stored_tasks(case: dict) -> list[str]:
    """Plano e execução aprovada de cada resultado armazenado do caso."""
    tasks = [_task(item["task_id"], item["title"], f"Investigue: {item['title']}, explicando o resultado.")
             for item in case["stored_results"]]
    responses = [_criteria(case), _plan(*tasks), aprendizados(*case["learnings"])]
    for item in case["stored_results"]:
        responses.extend([_result(item["task_id"], item["content"]),
                          relatorio((f"{item['task_id']}-AC1", True)), aprendizados()])
    return responses


def _question(case: dict) -> str:
    return " ".join(case["learnings"]) + " " + " ".join(item["description"] for item in case["criteria"])


# ── Aceitações sem coincidência exata, estimativa e apresentação ───────────


@pytest.mark.parametrize("case", _C1_APPROVED, ids=lambda case: case["name"])
async def test_resultado_sustentado_segue_de_c1_a_c3_sem_c2_desnecessaria(case: dict) -> None:
    final = f"Resposta apresentada: {case['name']}"
    scenario = _scenario([*_stored_tasks(case), _global(case, [], case["reference_justification"]),
                          resposta_final(final)])

    events = await scenario.run(question=_question(case))

    assert _phases(scenario) == [*_PLANNING, *_TASK_CYCLE * len(case["stored_results"]),
                                 Phase.C1_GLOBAL_VERIFICATION, Phase.C3_FINAL_ANSWER]
    c1 = _prompts(scenario, Phase.C1_GLOBAL_VERIFICATION)[0]
    c3 = _prompts(scenario, Phase.C3_FINAL_ANSWER)[0]
    for item in case["stored_results"]:
        assert item["content"] in _area(c1, "Stored results")
    assert _area(c1, "Stored results") == _area(c3, "Stored results")
    policy = _flat(_area(c1, "Evidence and consistency policy"))
    assert "a numerical difference alone is not a defect" in policy
    assert "no rule that selecting an option passes" in policy
    assert "an estimate as an estimate" in _flat(c3)
    for prompt in _prompts(scenario, Phase.B2_TASK_VERIFICATION):
        assert "lack of an exact match is not, by itself, a reason for rejection" in _flat(prompt)
    assert scenario.session.final_answer == final == events[-1].content
    assert scenario.session.status is SessionStatusEnum.COMPLETED
    assert not scenario.llm.responses


# ── Reprovações reais em C.1 → C.2 → B → C.1 → C.3 ─────────────────────────


@pytest.mark.parametrize("case", _C1_REPROVED, ids=lambda case: case["name"])
async def test_lacuna_ou_contradicao_de_c1_vira_investigacao_especifica_antes_de_c3(case: dict) -> None:
    next_id = f"T{len(case['stored_results']) + 1}"
    corrective = _task(next_id, "Investigação da pendência", case["corrective_task"],
                       "Investiga a pendência e explica o resultado, confirmando ou corrigindo o registrado.")
    final = f"Resposta corrigida: {case['name']}"
    scenario = _scenario([
        *_stored_tasks(case), _global(case, case["reference_unmet"], case["reference_justification"]),
        _plan(corrective), _result(next_id, case["corrective_result"]), relatorio((f"{next_id}-AC1", True)),
        aprendizados(case["corrective_result"]), _global(case, [], "A investigação explicada resolve a pendência."),
        resposta_final(final),
    ])

    await scenario.run(question=_question(case))

    assert _phases(scenario)[-7:] == [Phase.C1_GLOBAL_VERIFICATION, Phase.C2_ADDITIONAL_PLANNING, *_TASK_CYCLE,
                                      Phase.C1_GLOBAL_VERIFICATION, Phase.C3_FINAL_ANSWER]
    c2 = _prompts(scenario, Phase.C2_ADDITIONAL_PLANNING)[0]
    feedback = _area(c2, "Global verification feedback")
    assert case["reference_justification"] in feedback and "reproved" in feedback
    for criterion_id in case["reference_unmet"]:
        assert f"`{criterion_id}`" in _area(c2, "General criteria not yet met")
    assert case["reference_justification"] not in _area(c2, "Results already stored")
    assert 'only "choose the closest option"' in _flat(c2)
    b1 = _prompts(scenario, Phase.B1_TASK_RESOLUTION)[-1]
    assert case["corrective_task"] in _area(b1, "Task")
    assert case["reference_justification"] not in b1
    first, second = _prompts(scenario, Phase.C1_GLOBAL_VERIFICATION)
    assert case["corrective_result"] not in _area(first, "Stored results")
    assert case["corrective_result"] in _area(second, "Stored results")
    assert "When rejecting, identify the gap or contradiction" in _flat(first)
    assert scenario.session.final_answer == final
    assert all(len(conversation) == 1 for conversation in scenario.llm.conversations)
    assert not scenario.llm.responses


# ── Verificação técnica local em B.2 ───────────────────────────────────────


@pytest.mark.parametrize("case", _B2_CASES, ids=lambda case: case["name"])
async def test_b2_verifica_a_relacao_tecnica_e_so_reprova_com_defeito_nomeado(case: dict) -> None:
    criterion = case["criteria"][0]
    general = {"criteria": [{"id": "AC1", "description": "Responder ao pedido."},
                            {"id": "AC2", "description": "Responder em português."}]}
    responses = [
        _criteria(general), _plan(_task("T1", "Tarefa", "Resolva o pedido, explicando.", criterion["description"])),
        aprendizados(*case["learnings"]), _result("T1", case["result"]),
        _report([("T1-AC1", case["reference_decision"] == "approved")], case["reference_justification"]),
    ]
    reproved = case["reference_decision"] == "reproved"
    if reproved:
        responses.extend([_result("T1", case["corrective_result"]),
                          _report([("T1-AC1", True)], "A relação técnica está correta.")])
    responses.extend([aprendizados(), relatorio(("AC1", True), ("AC2", True)), resposta_final("ok")])
    scenario = _scenario(responses)

    await scenario.run(question=" ".join(case["learnings"]))

    b2 = _prompts(scenario, Phase.B2_TASK_VERIFICATION)
    assert len(b2) == (2 if reproved else 1)
    technical = _flat(_area(b2[0], "Technical verification of the local criteria"))
    assert "The presence of an explanation is not its correctness" in technical
    assert "same standard of implicit content to every option compared" in technical
    assert case["result"] in _area(b2[0], "Preliminary result")
    first_b2 = next(i for i in scenario.session.invocations if i.phase is Phase.B2_TASK_VERIFICATION)
    assert first_b2.content_accepted is True
    assert first_b2.recovery is None
    stored = _area(_prompts(scenario, Phase.C1_GLOBAL_VERIFICATION)[0], "Stored results")
    if reproved:
        retry = _prompts(scenario, Phase.B1_TASK_RESOLUTION)[1]
        previous = _area(retry, "Previous attempts at this task")
        assert case["reference_justification"] in previous and case["result"] in previous
        assert "Address the concrete problem" in _flat(previous)
        b1_temperatures = [i.temperature for i in scenario.session.invocations if i.phase is Phase.B1_TASK_RESOLUTION]
        assert b1_temperatures == [scenario.temperature, 1.0]
        assert case["corrective_result"] in stored and case["result"] not in stored
    else:
        assert case["result"] in stored
    assert Phase.C2_ADDITIONAL_PLANNING not in _phases(scenario)


async def test_feedback_por_termo_implicito_nao_obriga_trocar_a_resposta_sustentada() -> None:
    case = next(c for c in _B2_CASES if c["category"] == "implicit_content")
    literal_gap = "D não usa a palavra religiosidade."
    explicit = case["result"] + " O rito para pedir chuva é a religiosidade que sustenta D."
    general = {"criteria": [{"id": "AC1", "description": "Indicar a alternativa."},
                            {"id": "AC2", "description": "Responder em português."}]}
    scenario = _scenario([
        _criteria(general),
        _plan(_task("T1", "Interpretação", "Compare A e D com o texto, explicando.",
                    case["criteria"][0]["description"])),
        aprendizados(*case["learnings"]),
        _result("T1", case["result"]), _report([("T1-AC1", False)], literal_gap),
        _result("T1", explicit), _report([("T1-AC1", True)], "D está sustentada pela interpretação do rito."),
        aprendizados(), relatorio(("AC1", True), ("AC2", True)), resposta_final("D"),
    ])

    await scenario.run(question=" ".join(case["learnings"]))

    retry = _prompts(scenario, Phase.B1_TASK_RESOLUTION)[1]
    previous = _flat(_area(retry, "Previous attempts at this task"))
    assert literal_gap in previous
    assert "Keep the conclusions that the verdict did not refute" in previous
    assert "make the supporting link explicit instead of switching to another conclusion" in previous
    assert "same standard of implicit content to every option compared" in _flat(
        _prompts(scenario, Phase.B2_TASK_VERIFICATION)[0])
    assert explicit in _area(_prompts(scenario, Phase.C1_GLOBAL_VERIFICATION)[0], "Stored results")
    assert scenario.session.final_answer == "D"


# ── Cobertura depois da recuperação de A.2 ─────────────────────────────────


async def test_a2_recuperada_so_com_tarefa_intermediaria_passa_por_c1_c2_b_c1_c3() -> None:
    case = next(c for c in _C1_REPROVED if c["category"] == "missing_content")
    ratio = case["stored_results"][0]
    intermediate = _task("T1", ratio["title"], "Determine a razão entre as distâncias médias de Marte e da "
                         "Terra ao Sol, explicando.")
    rejected = _plan({key: value for key, value in intermediate.items() if key != "title"})
    corrective = _task("T2", "Período de Marte", case["corrective_task"], "Período em meses explicado.")
    scenario = _scenario([
        _criteria(case), rejected, _plan(intermediate), aprendizados(*case["learnings"]),
        _result("T1", ratio["content"]), relatorio(("T1-AC1", True)), aprendizados(ratio["content"]),
        _global(case, case["reference_unmet"], case["reference_justification"]),
        _plan(corrective), _result("T2", case["corrective_result"]), relatorio(("T2-AC1", True)),
        aprendizados(case["corrective_result"]), _global(case, [], "O período em meses foi determinado."),
        resposta_final("RESPOSTA_FINAL: C"),
    ])

    await scenario.run(question=_question(case))

    assert _phases(scenario) == [
        Phase.A1_GENERAL_CRITERIA, Phase.A2_TASK_DECOMPOSITION, Phase.A2_TASK_DECOMPOSITION,
        Phase.A3_PLANNING_LEARNINGS, *_TASK_CYCLE, Phase.C1_GLOBAL_VERIFICATION, Phase.C2_ADDITIONAL_PLANNING,
        *_TASK_CYCLE, Phase.C1_GLOBAL_VERIFICATION, Phase.C3_FINAL_ANSWER,
    ]
    invocations = scenario.session.invocations
    assert [i.content_accepted for i in invocations[1:3]] == [False, True]
    assert invocations[2].recovers_invocation_id == invocations[1].id
    assert invocations[1].recovery.result is RecoveryResultEnum.RECOVERED
    assert "distance ratio is not the calculation of a period" in _flat(
        _prompts(scenario, Phase.C1_GLOBAL_VERIFICATION)[0])
    assert case["reference_justification"] in _area(
        _prompts(scenario, Phase.C2_ADDITIONAL_PLANNING)[0], "Global verification feedback")
    assert ratio["content"] in _area(_prompts(scenario, Phase.B1_TASK_RESOLUTION)[1], "Key Learnings")
    first, second = _prompts(scenario, Phase.C1_GLOBAL_VERIFICATION)
    assert case["corrective_result"] in _area(second, "Stored results")
    assert case["corrective_result"] not in _area(first, "Stored results")
    assert scenario.session.final_answer == "RESPOSTA_FINAL: C"
    assert scenario.session.totals.total_llm_calls == scenario.llm.call_count == 14


# ── Contrato do relatório: incoerência recuperável x reprovação aceita ──────


async def test_c1_aprovado_com_criterio_nao_atendido_e_corrigido_e_reprovacao_coerente_e_aceita() -> None:
    case = next(c for c in _C1_REPROVED if c["category"] == "contradiction")
    incoherent = _report([("AC1", False), ("AC2", True)], case["reference_justification"], decision="approved")
    next_id = f"T{len(case['stored_results']) + 1}"
    scenario = _scenario([
        *_stored_tasks(case), incoherent, _global(case, case["reference_unmet"], case["reference_justification"]),
        _plan(_task(next_id, "Investigação", case["corrective_task"])), _result(next_id, case["corrective_result"]),
        relatorio((f"{next_id}-AC1", True)), aprendizados(), _global(case, [], "Contradição investigada."),
        resposta_final("final"),
    ])

    await scenario.run(question=_question(case))

    c1 = [(index, i) for index, i in enumerate(scenario.session.invocations) if i.phase is Phase.C1_GLOBAL_VERIFICATION]
    (refused_index, refused), (_, accepted), (_, final_c1) = c1
    assert refused.content_accepted is False
    assert refused.output_diagnostic.problem.code is OutputProblemCodeEnum.DECISION_CONSISTENCY
    assert refused.recovery.result is RecoveryResultEnum.RECOVERED
    assert refused.recovery.resolved_by_invocation_id == accepted.id
    assert accepted.recovers_invocation_id == refused.id and accepted.context_id == refused.context_id
    assert [refused.temperature, accepted.temperature] == [scenario.temperature, 1.0]
    correction = scenario.llm.texts_of(refused_index + 1)
    assert incoherent in correction and correction[0].count("# C.1") == 1
    assert accepted.content_accepted is True and accepted.recovery is None
    assert final_c1.context_id != accepted.context_id and final_c1.temperature == scenario.temperature
    assert Phase.C2_ADDITIONAL_PLANNING in _phases(scenario)
    assert scenario.session.totals.total_llm_calls == scenario.llm.call_count
    assert scenario.session.final_answer == "final"
