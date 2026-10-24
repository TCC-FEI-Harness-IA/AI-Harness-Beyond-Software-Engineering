import logging

from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.infra.config.settings import Settings
from src.infra.providers.file_prompt_template_provider import FilePromptTemplateProvider

_PLACEHOLDERS_POR_FASE = {
    ThinkingPhaseEnum.A1_GENERAL_CRITERIA: {"user_question"},
    ThinkingPhaseEnum.A2_TASK_DECOMPOSITION: {"user_question", "max_tasks"},
    ThinkingPhaseEnum.A3_PLANNING_LEARNINGS: {"user_question"},
    ThinkingPhaseEnum.B1_TASK_RESOLUTION: {"task_description", "task_acceptance_criteria"},
    ThinkingPhaseEnum.B2_TASK_VERIFICATION: {"preliminary_result", "task_acceptance_criteria"},
    ThinkingPhaseEnum.B4_LEARNINGS_EXTRACTION: set(),
    ThinkingPhaseEnum.C1_GLOBAL_VERIFICATION: {"stored_results", "general_acceptance_criteria"},
    ThinkingPhaseEnum.C2_ADDITIONAL_PLANNING: {"unmet_criteria", "stored_results", "next_task_number", "max_tasks"},
    ThinkingPhaseEnum.C3_FINAL_ANSWER: {"stored_results", "general_acceptance_criteria"},
}


def _provider() -> FilePromptTemplateProvider:
    return FilePromptTemplateProvider(settings=Settings(), logger=logging.getLogger("teste.templates"))


def test_os_nove_templates_existem_no_diretorio_configurado() -> None:
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


_FASES_DE_VERIFICACAO = [ThinkingPhaseEnum.B2_TASK_VERIFICATION, ThinkingPhaseEnum.C1_GLOBAL_VERIFICATION]
_FASES_DE_PLANEJAMENTO = [ThinkingPhaseEnum.A2_TASK_DECOMPOSITION, ThinkingPhaseEnum.C2_ADDITIONAL_PLANNING]


def test_templates_de_verificacao_exigem_uma_avaliacao_exata_por_criterio() -> None:
    provider = _provider()

    for fase in _FASES_DE_VERIFICACAO:
        template = provider.get(phase=fase).lower()
        assert "exatamente uma avaliação" in template
        assert "não omita" in template
        assert "não repita" in template
        assert "invente identificadores" in template


def test_templates_de_verificacao_exigem_pendencias_iguais_as_avaliacoes_negativas() -> None:
    provider = _provider()

    for fase in _FASES_DE_VERIFICACAO:
        template = provider.get(phase=fase)
        assert "`met` igual a `false`" in template
        assert "`unmet_criteria_ids` deve conter exatamente" in template
        assert "`approved` somente quando" in template


def test_templates_de_planejamento_informam_o_teto_de_tarefas_do_lote() -> None:
    provider = _provider()

    for fase in _FASES_DE_PLANEJAMENTO:
        renderizado = provider.render(
            phase=fase,
            variables={
                "user_question": "q",
                "unmet_criteria": "u",
                "stored_results": "s",
                "next_task_number": "2",
                "max_tasks": "7",
            },
        )
        assert "no máximo 7 tarefas" in renderizado
        assert "não funda" in renderizado


def test_template_de_aprendizados_do_planejamento_manda_preservar_o_que_chama_a_atencao() -> None:
    template = _provider().get(phase=ThinkingPhaseEnum.A3_PLANNING_LEARNINGS).lower()

    assert "valores" in template and "unidades de medida" in template
    assert "alternativas" in template
    assert "fórmulas" in template
    assert "restrições" in template
    assert "literalmente" in template


def test_template_de_aprendizados_do_planejamento_proibe_resolver_a_pergunta() -> None:
    template = _provider().get(phase=ThinkingPhaseEnum.A3_PLANNING_LEARNINGS).lower()

    assert "não resolva" in template
    assert "nenhuma conclusão" in template


def test_template_de_aprendizados_do_planejamento_devolve_lista_vazia_quando_nada_se_aplica() -> None:
    template = _provider().get(phase=ThinkingPhaseEnum.A3_PLANNING_LEARNINGS)

    assert "lista vazia" in template
    assert '{"learnings": [' in template
