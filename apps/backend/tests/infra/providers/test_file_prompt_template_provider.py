import logging
from pathlib import Path

import pytest

from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.domain.errors.prompt_template_not_found_error import PromptTemplateNotFoundError
from src.infra.providers.file_prompt_template_provider import FilePromptTemplateProvider
from tests.doubles.fake_settings import FakeSettings

_ARQUIVOS_POR_FASE = {
    ThinkingPhaseEnum.A1_GENERAL_CRITERIA: "a1_general_criteria.md",
    ThinkingPhaseEnum.A2_TASK_DECOMPOSITION: "a2_task_decomposition.md",
    ThinkingPhaseEnum.A3_PLANNING_LEARNINGS: "a3_planning_learnings.md",
    ThinkingPhaseEnum.B1_TASK_RESOLUTION: "b1_task_resolution.md",
    ThinkingPhaseEnum.B2_TASK_VERIFICATION: "b2_task_verification.md",
    ThinkingPhaseEnum.B4_LEARNINGS_EXTRACTION: "b4_learnings_extraction.md",
    ThinkingPhaseEnum.C1_GLOBAL_VERIFICATION: "c1_global_verification.md",
    ThinkingPhaseEnum.C2_ADDITIONAL_PLANNING: "c2_additional_planning.md",
    ThinkingPhaseEnum.C3_FINAL_ANSWER: "c3_final_answer.md",
}


def _provider(tmp_path: Path) -> FilePromptTemplateProvider:
    return FilePromptTemplateProvider(
        settings=FakeSettings(ralph_prompt_templates_path=str(tmp_path)),
        logger=logging.getLogger("teste.template_provider"),
    )


@pytest.mark.parametrize(("fase", "arquivo"), sorted(_ARQUIVOS_POR_FASE.items()))
def test_le_o_arquivo_correspondente_a_cada_fase(tmp_path: Path, fase: ThinkingPhaseEnum, arquivo: str) -> None:
    (tmp_path / arquivo).write_text(f"conteudo de {arquivo}", encoding="utf-8")

    assert _provider(tmp_path).get(phase=fase) == f"conteudo de {arquivo}"


def test_template_inexistente_no_disco_e_recusado(tmp_path: Path) -> None:
    with pytest.raises(PromptTemplateNotFoundError) as erro:
        _provider(tmp_path).get(phase=ThinkingPhaseEnum.A1_GENERAL_CRITERIA)

    assert erro.value.template_name == "a1_general_criteria.md"
    assert erro.value.path == str(tmp_path)


@pytest.mark.parametrize("fase", [ThinkingPhaseEnum.B3_RESULT_STORAGE, ThinkingPhaseEnum.DIRECT_INFERENCE])
def test_fase_sem_template_e_recusada(tmp_path: Path, fase: ThinkingPhaseEnum) -> None:
    with pytest.raises(PromptTemplateNotFoundError) as erro:
        _provider(tmp_path).get(phase=fase)

    assert erro.value.template_name == fase.value


def test_le_o_disco_uma_unica_vez_por_instancia(tmp_path: Path) -> None:
    arquivo = tmp_path / "a1_general_criteria.md"
    arquivo.write_text("conteudo original", encoding="utf-8")
    provider = _provider(tmp_path)

    primeira = provider.get(phase=ThinkingPhaseEnum.A1_GENERAL_CRITERIA)
    arquivo.write_text("conteudo alterado no disco", encoding="utf-8")
    segunda = provider.get(phase=ThinkingPhaseEnum.A1_GENERAL_CRITERIA)

    assert primeira == "conteudo original"
    assert segunda == "conteudo original"


def test_render_substitui_todos_os_placeholders(tmp_path: Path) -> None:
    (tmp_path / "a1_general_criteria.md").write_text(
        "Pergunta: {{user_question}}\nEco: {{user_question}}\nIdioma: {{language}}",
        encoding="utf-8",
    )

    renderizado = _provider(tmp_path).render(
        phase=ThinkingPhaseEnum.A1_GENERAL_CRITERIA,
        variables={"user_question": "qual numero e primo?", "language": "portugues"},
    )

    assert renderizado == "Pergunta: qual numero e primo?\nEco: qual numero e primo?\nIdioma: portugues"


def test_render_recusa_placeholder_ausente_nomeando_o(tmp_path: Path) -> None:
    (tmp_path / "a1_general_criteria.md").write_text("Pergunta: {{user_question}}", encoding="utf-8")

    with pytest.raises(ValueError, match="user_question"):
        _provider(tmp_path).render(phase=ThinkingPhaseEnum.A1_GENERAL_CRITERIA, variables={})


def test_render_ignora_variavel_extra(tmp_path: Path) -> None:
    (tmp_path / "a1_general_criteria.md").write_text("Pergunta: {{user_question}}", encoding="utf-8")

    renderizado = _provider(tmp_path).render(
        phase=ThinkingPhaseEnum.A1_GENERAL_CRITERIA,
        variables={"user_question": "pergunta", "sobra": "ignorada"},
    )

    assert renderizado == "Pergunta: pergunta"


def test_render_de_template_sem_placeholder_devolve_o_texto_intacto(tmp_path: Path) -> None:
    (tmp_path / "b4_learnings_extraction.md").write_text("Compile os fatos.", encoding="utf-8")

    renderizado = _provider(tmp_path).render(phase=ThinkingPhaseEnum.B4_LEARNINGS_EXTRACTION, variables={})

    assert renderizado == "Compile os fatos."


def test_render_propaga_a_ausencia_do_arquivo(tmp_path: Path) -> None:
    with pytest.raises(PromptTemplateNotFoundError):
        _provider(tmp_path).render(phase=ThinkingPhaseEnum.C3_FINAL_ANSWER, variables={})
