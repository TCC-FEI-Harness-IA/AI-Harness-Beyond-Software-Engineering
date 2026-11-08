"""Transporte com prompts, parser e fases reais, com todas as saídas do LLM roteirizadas.

Os resultados e vereditos abaixo são exemplos, não um julgamento semântico automático.
"""
import json
import logging
from pathlib import Path

import pytest

from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum as Phase
from src.infra.providers.file_prompt_template_provider import FilePromptTemplateProvider
from tests.doubles.fake_settings import FakeSettings
from tests.doubles.ralph_scenario import RalphScenario
from tests.doubles.ralph_scripts import aprendizados, relatorio, resposta_final

_MATRIX = json.loads((Path(__file__).parents[2] / "fixtures/planning_semantics_v1.json").read_text())
_CASES = {case["name"]: case for case in _MATRIX["cases"]}


def _json(**content: object) -> str:
    return json.dumps(content, ensure_ascii=False)


def _criteria(case: dict) -> str:
    return _json(general_acceptance_criteria=[
        {"id": f"AC{index}", "description": description}
        for index, description in enumerate(case["general_criteria"], 1)
    ])


def _result(task_id: str, result: str, conclusion: str) -> str:
    return _json(task_id=task_id, result=result, conclusion=conclusion)


def _scenario(responses: list[str]) -> RalphScenario:
    settings = FakeSettings()
    return RalphScenario(responses=responses, settings=settings, template_provider=FilePromptTemplateProvider(
        settings=settings, logger=logging.getLogger(__name__),
    ))


def _prompts(scenario: RalphScenario, phase: Phase) -> list[str]:
    return [scenario.llm.texts_of(index)[0] for index, invocation in enumerate(scenario.session.invocations)
            if invocation.phase is phase]


def _area(prompt: str, heading: str) -> str:
    # Blocos de tarefas usam o mesmo nível de heading; as áreas superiores têm nomes conhecidos.
    area = prompt.split(f"## {heading}\n", 1)[1]
    for next_heading in ("Acceptance criteria for this task", "Key Learnings", "Previous attempts at this task",
                         "General criteria not yet met", "Global verification feedback", "Results already stored",
                         "Content gaps and corrective investigation", "Instructions"):
        area = area.split(f"\n## {next_heading}\n", 1)[0]
    return area.strip()


async def test_colisoes_consumem_conclusoes_obtidas_pela_memoria_sem_embuti_las_no_plano() -> None:
    case = _CASES["collisions"]
    forces = "The block has the greater average force: its momentum reversal has twice the change of adhesion."
    energy = "Clay dissipates more kinetic energy: it stops, whereas the rigid block rebounds at the same speed."
    joint = "A maior força média ocorre no bloco; a maior energia dissipada ocorre na argila."
    details = [
        "FORCE_DERIVATION_ONLY: Δp_block=-2mv; Δp_clay=-mv; |F|=|Δp|/Δt, in N.",
        "ENERGY_DERIVATION_ONLY: K=mv²/2; compare initial and final kinetic energies, in J.",
        "The force and energy orderings in memory are opposite, since momentum transfer and energy loss differ.",
    ]
    responses = [_criteria(case), _json(tasks=case["tasks"]), aprendizados(case["question"])]
    for task, result, conclusion in zip(case["tasks"], details, [forces, energy, joint]):
        responses.extend([
            _result(task["id"], result + " " + conclusion, conclusion),
            relatorio(*[(criterion["id"], True) for criterion in task["acceptance_criteria"]]),
            aprendizados(conclusion),
        ])
    responses.extend([relatorio(("AC1", True), ("AC2", True)), resposta_final(joint)])
    scenario = _scenario(responses)

    events = await scenario.run(question=case["question"])

    b1 = _prompts(scenario, Phase.B1_TASK_RESOLUTION)
    assert forces not in b1[0] and energy not in b1[0]
    assert forces in _area(b1[1], "Key Learnings") and energy not in b1[1]
    for conclusion in (forces, energy):
        assert conclusion in _area(b1[2], "Key Learnings")
        assert conclusion not in _area(b1[2], "Task")
        assert conclusion not in _prompts(scenario, Phase.A2_TASK_DECOMPOSITION)[0]
    assert details[0] not in b1[2] and details[1] not in b1[2]
    c3 = _prompts(scenario, Phase.C3_FINAL_ANSWER)[0]
    assert details[0] in c3 and details[1] in c3 and joint in c3
    assert scenario.session.final_answer == events[-1].content == joint
    assert scenario.llm.call_count == 14
    assert not scenario.llm.responses
    assert len({i.context_id for i in scenario.session.invocations}) == scenario.llm.call_count
    assert all(len(conversation) == 1 for conversation in scenario.llm.conversations)


@pytest.mark.parametrize("case_name", ["additional_period_gap", "additional_energy_contradiction"])
async def test_c2_recebe_motivo_concreto_de_c1_e_preserva_resultados_e_memoria_separados(case_name: str) -> None:
    case = _CASES[case_name]
    initial_ids = [f"T{index}" for index in range(1, int(case["tasks"][0]["id"][1:]))]
    initial_tasks = [{
        "id": task_id, "title": f"Prior investigation {task_id}",
        "description": "Investigate one relation in the request and explain the finding.",
        "acceptance_criteria": [{"id": f"{task_id}-AC1", "description": "Explained finding in scope."}],
    } for task_id in initial_ids]
    responses = [_criteria(case), _json(tasks=initial_tasks), aprendizados(case["question"])]
    for task_id in initial_ids:
        responses.extend([
            _result(task_id, "FULL_PRIOR_REASONING: " + case["stored_results"], case["stored_results"]),
            relatorio((f"{task_id}-AC1", True)), aprendizados(case["learnings"]),
        ])
    responses.extend([
        _json(criteria_evaluation=[{"criterion_id": "AC1", "met": False, "justification": case["gap"]}],
              unmet_criteria_ids=["AC1"], decision="reproved"),
        _json(tasks=case["tasks"]),
    ])
    final_task = case["tasks"][0]
    determination = ("O período de P é 96 meses: pela relação de Kepler, T/12=4^(3/2)."
                     if case_name == "additional_period_gap" else
                     "A energia vem do vapor da camisa: o balanço distingue a energia cedida pelo vapor "
                     "ao esfriar e condensar da energia absorvida pelo produto ao aquecer e evaporar.")
    responses.extend([
        _result(final_task["id"], determination, determination), relatorio((final_task["id"] + "-AC1", True)),
        aprendizados(determination), relatorio(("AC1", True)), resposta_final(determination),
    ])
    scenario = _scenario(responses)

    await scenario.run(question=case["question"])

    c2 = _prompts(scenario, Phase.C2_ADDITIONAL_PLANNING)[0]
    feedback = _area(c2, "Global verification feedback")
    assert case["gap"] in feedback and "`AC1`" in feedback and "reproved" in feedback
    assert case["stored_results"] in _area(c2, "Results already stored")
    assert "FULL_PRIOR_REASONING" not in c2
    assert case["gap"] not in _area(c2, "Results already stored")
    assert case["learnings"] in _area(c2, "Key Learnings")
    assert case["question"] in _area(c2, "Original Prompt")
    assert f"at most {scenario.cost_guard.remaining_task_slots()}" in c2
    assert f"T{len(initial_ids) + 1}`" in c2
    b1 = _prompts(scenario, Phase.B1_TASK_RESOLUTION)[-1]
    assert final_task["description"] in _area(b1, "Task")
    assert case["gap"] not in b1  # Feedback pertence a C.2; a tarefa corretiva é a entrada de B.1.
    assert determination not in c2 and determination not in b1
    c3 = _prompts(scenario, Phase.C3_FINAL_ANSWER)[0]
    assert determination in c3 and "FULL_PRIOR_REASONING" in c3
    assert scenario.session.final_answer == determination
    assert not scenario.llm.responses
    assert all(len(conversation) == 1 for conversation in scenario.llm.conversations)
