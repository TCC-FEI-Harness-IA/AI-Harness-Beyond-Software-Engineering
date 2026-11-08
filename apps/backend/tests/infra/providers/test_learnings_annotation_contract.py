"""Contrato dos templates reais; presença de instruções não avalia extração semântica."""
import logging

import pytest

from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum as Phase
from src.infra.providers.file_prompt_template_provider import FilePromptTemplateProvider
from tests.doubles.fake_settings import FakeSettings


@pytest.mark.parametrize(("phase", "obligations"), [
    (Phase.A4_PLANNING_LEARNINGS, (
        "names of objects", "acronyms and their definitions", "symbols and their referents",
        "do not guess an acronym's expansion",
    )),
    (Phase.A4_PLANNING_LEARNINGS, (
        "every row and column", "identifiers and full option texts", "lists",
        "code and meaning", "test and parameter",
    )),
    (Phase.A4_PLANNING_LEARNINGS, (
        "value and object", "distance and spatial reference", "deadline and event",
        "unit and quantity", "what exactly must be determined",
    )),
    (Phase.A4_PLANNING_LEARNINGS, (
        "do not correct", "do not convert", "do not round", "do not classify",
        "do not supplement", "preserve the relevant ambiguity",
    )),
    (Phase.A4_PLANNING_LEARNINGS, (
        "completeness review", "within this same call", "each group of data",
        "associations", "simultaneous conditions", "next fresh context",
    )),
    (Phase.B4_LEARNINGS_EXTRACTION, (
        "spatial reference", "sign and reference frame", "exact or approximate",
        "never turn an approximation into an equality",
    )),
    (Phase.B4_LEARNINGS_EXTRACTION, (
        "calculated value", "best-fit selection", "do not equate", "different objects or hypotheses",
    )),
    (Phase.B4_LEARNINGS_EXTRACTION, (
        "retain every condition", "under constant pressure", "only supplied data belong to a.3",
        "do not invent a missing reason",
    )),
])
def test_templates_renderizados_explicitam_obrigacoes_de_anotacao(phase: Phase, obligations: tuple[str, ...]) -> None:
    provider = FilePromptTemplateProvider(settings=FakeSettings(), logger=logging.getLogger("test.annotations"))
    prompt = provider.render(phase=phase, variables={
        "user_question": "PEDIDO_TEXTUAL_GENERICO", "task_description": "TAREFA",
        "approved_result": "RESULTADO", "task_history": "HISTORICO", "learnings": "MEMORIA",
    })

    normalized = " ".join(prompt.lower().split())
    for obligation in obligations:
        assert obligation in normalized
    assert "{{" not in prompt
    assert '{"learnings": [' in prompt
