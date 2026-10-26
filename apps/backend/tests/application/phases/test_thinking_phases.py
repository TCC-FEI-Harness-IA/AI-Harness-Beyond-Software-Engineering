import json
import logging

import pytest

from src.application.phases.additional_planning_phase import AdditionalPlanningPhase
from src.application.phases.base_thinking_phase import BaseThinkingPhase
from src.application.phases.final_answer_phase import FinalAnswerPhase
from src.application.phases.general_criteria_phase import GeneralCriteriaPhase
from src.application.phases.global_verification_phase import GlobalVerificationPhase
from src.application.phases.learnings_extraction_phase import LearningsExtractionPhase
from src.application.phases.planning_learnings_phase import PlanningLearningsPhase
from src.application.phases.task_decomposition_phase import TaskDecompositionPhase
from src.application.phases.task_resolution_phase import TaskResolutionPhase
from src.application.phases.task_verification_phase import TaskVerificationPhase
from src.domain.entities.llm.context_window import ContextWindow
from src.domain.entities.thinking.validation_context import ValidationContext
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.infra.adapters.session_recorder_adapter import SessionRecorderAdapter
from src.infra.adapters.structured_response_parser_adapter import StructuredResponseParserAdapter
from tests.doubles.fake_clock import FakeClock
from tests.doubles.fake_cost_guard import FakeCostGuard
from tests.doubles.fake_prompt_template_provider import FakePromptTemplateProvider
from tests.doubles.fake_settings import FakeSettings
from tests.doubles.scripted_llm_completions import ScriptedLLMCompletions

_TAREFA = {
    "id": "T1",
    "title": "titulo",
    "description": "descricao",
    "acceptance_criteria": [{"id": "T1-AC1", "description": "criterio"}],
}
_VERIFICACAO = json.dumps(
    {
        "decision": "approved",
        "criteria_evaluation": [{"criterion_id": "T1-AC1", "met": True, "justification": "atende"}],
        "unmet_criteria_ids": [],
    }
)

_CASOS = [
    (
        GeneralCriteriaPhase,
        ThinkingPhaseEnum.A1_GENERAL_CRITERIA,
        json.dumps({"general_acceptance_criteria": [{"id": "AC1", "description": "d"}]}),
        {"user_question": "pergunta"},
    ),
    (
        TaskDecompositionPhase,
        ThinkingPhaseEnum.A2_TASK_DECOMPOSITION,
        json.dumps({"tasks": [_TAREFA]}),
        {"user_question": "pergunta"},
    ),
    (
        PlanningLearningsPhase,
        ThinkingPhaseEnum.A3_PLANNING_LEARNINGS,
        json.dumps({"learnings": ["Alternativas: A) 2; B) 4"]}),
        {"user_question": "pergunta"},
    ),
    (
        TaskResolutionPhase,
        ThinkingPhaseEnum.B1_TASK_RESOLUTION,
        json.dumps({"task_id": "T1", "result": "resolucao"}),
        {"task_description": "descricao", "task_acceptance_criteria": "- T1-AC1"},
    ),
    (
        TaskVerificationPhase,
        ThinkingPhaseEnum.B2_TASK_VERIFICATION,
        _VERIFICACAO,
        {"preliminary_result": "resolucao", "task_acceptance_criteria": "- T1-AC1"},
    ),
    (
        LearningsExtractionPhase,
        ThinkingPhaseEnum.B4_LEARNINGS_EXTRACTION,
        json.dumps({"learnings": ["fato seco"]}),
        {},
    ),
    (
        GlobalVerificationPhase,
        ThinkingPhaseEnum.C1_GLOBAL_VERIFICATION,
        _VERIFICACAO,
        {"stored_results": "## T1", "general_acceptance_criteria": "- AC1"},
    ),
    (
        AdditionalPlanningPhase,
        ThinkingPhaseEnum.C2_ADDITIONAL_PLANNING,
        json.dumps({"tasks": [_TAREFA]}),
        {"unmet_criteria": "- AC1", "stored_results": "## T1", "next_task_number": "2"},
    ),
    (
        FinalAnswerPhase,
        ThinkingPhaseEnum.C3_FINAL_ANSWER,
        json.dumps({"final_answer": "D) Nenhuma das anteriores"}),
        {"stored_results": "## T1", "general_acceptance_criteria": "- AC1"},
    ),
]


_FASES_DE_VERIFICACAO = {ThinkingPhaseEnum.B2_TASK_VERIFICATION, ThinkingPhaseEnum.C1_GLOBAL_VERIFICATION}


def _monta(fase_classe: type[BaseThinkingPhase], llm: ScriptedLLMCompletions,
           provider: FakePromptTemplateProvider, recorder: SessionRecorderAdapter) -> BaseThinkingPhase:
    return fase_classe(
        llm_completions=llm,
        template_provider=provider,
        parser=StructuredResponseParserAdapter(logger=logging.getLogger("teste.parser")),
        cost_guard=FakeCostGuard(),
        session_recorder=recorder,
        clock=FakeClock(),
        settings=FakeSettings(),
        logger=logging.getLogger("teste.fase"),
    )


@pytest.mark.parametrize(("fase_classe", "fase", "saida", "variaveis"), _CASOS)
def test_cada_fase_expoe_o_identificador_do_paper(
    fase_classe: type[BaseThinkingPhase],
    fase: ThinkingPhaseEnum,
    saida: str,
    variaveis: dict[str, str],
    recorder: SessionRecorderAdapter,
) -> None:
    montada = _monta(
        fase_classe, ScriptedLLMCompletions(responses=[saida]), FakePromptTemplateProvider(), recorder
    )

    assert montada.phase is fase


@pytest.mark.parametrize(("fase_classe", "fase", "saida", "variaveis"), _CASOS)
async def test_cada_fase_renderiza_o_proprio_template_com_as_variaveis_recebidas(
    fase_classe: type[BaseThinkingPhase],
    fase: ThinkingPhaseEnum,
    saida: str,
    variaveis: dict[str, str],
    recorder: SessionRecorderAdapter,
) -> None:
    provider = FakePromptTemplateProvider()
    montada = _monta(fase_classe, ScriptedLLMCompletions(responses=[saida]), provider, recorder)
    validacao = ValidationContext(expected_criteria_ids=("T1-AC1",)) if fase in _FASES_DE_VERIFICACAO else None

    resultado = await montada.execute(
        context=ContextWindow(context_id="ctx-1", phase=fase),
        variables=variaveis,
        validation=validacao,
    )

    assert provider.variables_of(fase) == [variaveis]
    assert resultado.raw_output == saida
