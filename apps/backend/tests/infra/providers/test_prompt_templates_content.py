import logging

from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.infra.config.settings import Settings
from src.infra.providers.file_prompt_template_provider import FilePromptTemplateProvider

_PLACEHOLDERS_POR_FASE = {
    ThinkingPhaseEnum.A1_GENERAL_CRITERIA: {"user_question"},
    ThinkingPhaseEnum.A2_TASK_DECOMPOSITION: {"user_question"},
    ThinkingPhaseEnum.B1_TASK_RESOLUTION: {"task_description", "task_acceptance_criteria"},
    ThinkingPhaseEnum.B2_TASK_VERIFICATION: {"preliminary_result", "task_acceptance_criteria"},
    ThinkingPhaseEnum.B4_LEARNINGS_EXTRACTION: set(),
    ThinkingPhaseEnum.C1_GLOBAL_VERIFICATION: {"stored_results", "general_acceptance_criteria"},
    ThinkingPhaseEnum.C2_ADDITIONAL_PLANNING: {"unmet_criteria", "stored_results", "next_task_number"},
    ThinkingPhaseEnum.C3_FINAL_ANSWER: {"stored_results", "general_acceptance_criteria"},
}


def _provider() -> FilePromptTemplateProvider:
    return FilePromptTemplateProvider(settings=Settings(), logger=logging.getLogger("teste.templates"))


def test_os_oito_templates_existem_no_diretorio_configurado() -> None:
    provider = _provider()

    for fase in _PLACEHOLDERS_POR_FASE:
        assert provider.get(phase=fase).strip()


def test_todo_template_exige_saida_em_json() -> None:
    provider = _provider()

    for fase in _PLACEHOLDERS_POR_FASE:
        template = provider.get(phase=fase)
        assert "## Formato de saída" in template
        assert "JSON" in template


def test_cada_template_declara_exatamente_os_placeholders_que_o_fluxo_entrega() -> None:
    provider = _provider()

    for fase, placeholders in _PLACEHOLDERS_POR_FASE.items():
        renderizado = provider.render(
            phase=fase,
            variables={placeholder: f"<{placeholder}>" for placeholder in placeholders},
        )
        for placeholder in placeholders:
            assert f"<{placeholder}>" in renderizado
        assert "{{" not in renderizado
