"""Guardas dos limites generalistas; não certificam o julgamento semântico de um LLM."""
import logging

import pytest

from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum as Phase
from src.infra.providers.file_prompt_template_provider import FilePromptTemplateProvider
from tests.doubles.fake_settings import FakeSettings


def _template(phase: Phase) -> str:
    provider = FilePromptTemplateProvider(settings=FakeSettings(), logger=logging.getLogger(__name__))
    return " ".join(provider.get(phase=phase).split())


def test_b1_preserva_dados_literais_e_verifica_apenas_antecipacoes_do_planejamento() -> None:
    template = _template(Phase.B1_TASK_RESOLUTION)

    assert "Preserve literal inputs copied from the user's request" in template
    assert "do not demote supplied data to assumptions" in template
    assert "planning-derived values, conclusions or unstated assumptions" in template
    assert "A number or conclusion stated in the task description or in a criterion is a hypothesis" not in template


@pytest.mark.parametrize("phase", [Phase.B1_TASK_RESOLUTION, Phase.B2_TASK_VERIFICATION,
                                   Phase.C1_GLOBAL_VERIFICATION])
def test_politica_nao_embute_valores_e_situacoes_dos_casos_de_regressao(phase: Phase) -> None:
    template = _template(phase)

    # Conferimos o template fixo: os mesmos dados continuam permitidos no pedido do usuário.
    for regression_example in ("17.76 months", "calculated 47", "option 44", "religious rite",
                               "interpreting rainfall and drought", "different barriers"):
        assert regression_example not in template, (phase, regression_example)
    assert "no rule that selecting an option passes" in template
    assert "no universal percentage tolerance" in template
