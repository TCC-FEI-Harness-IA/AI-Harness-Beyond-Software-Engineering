"""Contratos da fidelidade da síntese final (thinking 06) sobre os templates reais.

Verificam o texto entregue ao modelo em C.3 e a harmonização de C.1: a conferência de fidelidade
dentro da própria chamada de C.3, a distinção entre pareamento literal e seleção analítica e a
detecção, em C.1, de um vínculo indispensável à apresentação que não está disponível. Não provam
que um modelo real escreve uma resposta fiel; isso exige avaliação semântica com modelo real.
"""
import logging
import re

import pytest

from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum as Phase
from src.infra.providers.file_prompt_template_provider import FilePromptTemplateProvider
from tests.doubles.fake_settings import FakeSettings

_FIDELITY_HEADING = "Fidelity check before answering"
_IDENTIFIER_HEADING = "Identifiers and faithful presentation"
_ALL_PHASES = (
    Phase.A1_GENERAL_CRITERIA, Phase.A2_TASK_DECOMPOSITION, Phase.A3_PLANNING_LEARNINGS,
    Phase.B1_TASK_RESOLUTION, Phase.B2_TASK_VERIFICATION, Phase.B4_LEARNINGS_EXTRACTION,
    Phase.C1_GLOBAL_VERIFICATION, Phase.C2_ADDITIONAL_PLANNING, Phase.C3_FINAL_ANSWER,
)


def _provider() -> FilePromptTemplateProvider:
    return FilePromptTemplateProvider(settings=FakeSettings(), logger=logging.getLogger(__name__))


def _flat(text: str) -> str:
    return " ".join(text.split())


def _template(phase: Phase) -> str:
    return _flat(_provider().get(phase=phase))


def _section(phase: Phase, heading: str) -> str:
    template = _provider().get(phase=phase)
    assert f"## {heading}\n" in template, (phase, heading)
    return _flat(template.split(f"## {heading}\n", 1)[1].split("\n## ", 1)[0])


# ── C.3: conferência dentro da mesma chamada ────────────────────────────────


def test_c3_confere_a_fidelidade_antes_de_preencher_final_answer_na_mesma_resposta() -> None:
    template = _provider().get(phase=Phase.C3_FINAL_ANSWER)
    check = _section(Phase.C3_FINAL_ANSWER, _FIDELITY_HEADING)

    assert template.index(f"## {_FIDELITY_HEADING}") < template.index("## Output format")
    assert "within this same response, before writing `final_answer`" in check
    assert "identify the approved content that answers each part of the request" in check
    assert "not a separate stage" in check


def test_c3_preserva_significado_direcao_sinais_unidades_referencias_hipoteses_e_qualificacoes() -> None:
    check = _section(Phase.C3_FINAL_ANSWER, _FIDELITY_HEADING)

    for aspect in ("meaning", "direction of every comparison", "signs", "units", "reference frame",
                   "references", "hypotheses", "conditions", "qualifiers"):
        assert aspect in check, aspect
    for qualifier in ("approximately", "under hypothesis", "best fit", "estimate"):
        assert qualifier in check, qualifier
    assert "Translation and concision change the wording, never these aspects." in check


def test_c3_diferencia_resultado_calculado_de_escolha_aprovada_sem_endurecer_a_validacao() -> None:
    check = _section(Phase.C3_FINAL_ANSWER, _FIDELITY_HEADING)

    assert "calculated result" in check and "choice approved by best fit, approximation or elimination" in check
    assert "even without numerical equality and without a calculation that produces the chosen value" in check
    assert "do not re-validate it with stricter standards" in check
    assert "never write that they are equal" in check


def test_c3_confere_identificadores_pelo_pareamento_literal_das_notas() -> None:
    check = _section(Phase.C3_FINAL_ANSWER, _FIDELITY_HEADING)

    for label in ("letter and text of an option", "number of a test", "name of an entity", "product code", "month"):
        assert label in check, label
    assert "must label the very object the results determined" in check
    assert "use them for a literal check" in check
    assert "position of an item in a list" in check


def test_c3_separa_pareamento_literal_de_selecao_analitica() -> None:
    check = _section(Phase.C3_FINAL_ANSWER, _FIDELITY_HEADING)

    assert "Literal pairing is not analytical selection" in check
    for forbidden in ("choose the option closest to a value when the results did not make that comparison",
                      "complete a calculation", "resolve a residual conflict between results",
                      "invent an identifier"):
        assert forbidden in check, forbidden
    assert "Global approval does not authorize inventing information" in check


def test_c3_nao_inventa_identificador_ausente_nem_apresenta_erro_tecnico() -> None:
    check = _section(Phase.C3_FINAL_ANSWER, _FIDELITY_HEADING)

    assert "present the approved content without guessing the identifier" in check
    assert "never present an internal error message as the answer" in check


def test_c3_mantem_a_conclusao_coerente_com_a_justificativa_apresentada() -> None:
    check = _section(Phase.C3_FINAL_ANSWER, _FIDELITY_HEADING)

    assert "every formula, comparison and explanation you present points in the same direction" in check


def test_c3_nao_menciona_o_processo_interno_nem_inventa_formato() -> None:
    template = _template(Phase.C3_FINAL_ANSWER)

    assert "The check is internal" in template
    assert "do not mention stages, tasks, criteria, learnings or other internal details of the process" in template
    assert "Do not invent line or word limits" in template
    assert "optional does not mean mandatory" in template


def test_c3_mantem_as_garantias_anteriores_e_o_schema() -> None:
    template = _template(Phase.C3_FINAL_ANSWER)

    for phrase in ("do not replace the stored results", "introduce new facts that are not in the stored results",
                   "translating is presentation, not new reasoning",
                   "chose it by best fit, approximation or elimination",
                   "Present an approximate result as approximate and an estimate as an estimate",
                   "never turn a best fit into an exact equality", "without new analytical reasoning",
                   "Do not repair, recalculate or reconcile results here"):
        assert phrase in template, phrase
    assert template.endswith('{"final_answer": "markdown of the answer to the user"}')
    assert set(re.findall(r"{{(\w+)}}", template)) == {"stored_results", "general_acceptance_criteria", "learnings"}


def test_c3_declara_que_recebe_os_resultados_como_aprovados_na_ultima_c1() -> None:
    intro = _flat(_provider().get(phase=Phase.C3_FINAL_ANSWER).split("## Stored results\n", 1)[0])

    assert "exactly as the last global verification (C.1) approved them" in intro
    assert "superseded" in intro
    assert _section(Phase.C3_FINAL_ANSWER, "Stored results") == "{{stored_results}}"


def test_c3_tem_exemplos_de_fidelidade_e_de_extrapolacao_indevida() -> None:
    examples = _section(Phase.C3_FINAL_ANSWER, "Examples of valid and invalid presentation")

    assert "sample 2" in examples and "A) 1, B) 2, C) 3" in examples
    assert "best fit" in examples and "Invalid" in examples
    assert "MWh" in examples


# ── C.1: vínculo indispensável à apresentação ────────────────────────────────


def test_c1_nao_aprova_automaticamente_vinculo_ausente_entre_item_e_identificador() -> None:
    section = _section(Phase.C1_GLOBAL_VERIFICATION, _IDENTIFIER_HEADING)

    assert "the identifier is part of the content" in section
    assert "the Key Learnings record literally which identifier labels it" in section
    assert "mark the criterion as `met: false`" in section
    assert "C.2 can plan a task that establishes the link from the question" in section
    assert "Do not guess the link yourself" in section


def test_c1_nao_inventa_lacuna_de_identificador_quando_o_pedido_so_exige_conteudo() -> None:
    section = _section(Phase.C1_GLOBAL_VERIFICATION, _IDENTIFIER_HEADING)

    assert "do not create that gap" in section
    assert "marker line, the language or the format" in section and "C.3" in section


def test_c1_lembra_que_a_aprovacao_nao_autoriza_c3_a_inventar() -> None:
    section = _section(Phase.C1_GLOBAL_VERIFICATION, _IDENTIFIER_HEADING)

    assert "approval does not authorize C.3 to invent" in section
    assert "only literal pairing and presentation" in section


def test_c1_preserva_a_politica_e_os_exemplos_de_formato() -> None:
    template = _template(Phase.C1_GLOBAL_VERIFICATION)

    assert "FINAL_ANSWER: C" in template
    assert "select 13 liters as the best fit" in template
    assert "do not count as coverage" in template


# ── Generalidade: sem acoplamento ao benchmark e sem fase nova ──────────────


@pytest.mark.parametrize("phase", _ALL_PHASES)
def test_templates_nao_acoplam_a_sintese_ao_benchmark(phase: Phase) -> None:
    template = _template(phase)

    assert "question.options" not in template
    assert re.search(r"\bQ\d{3}\b", template) is None
    for case in ("cálcio", "calcium", "FUVEST", "ENEM"):
        assert case not in template, (phase, case)


def test_nao_ha_fase_de_thinking_depois_da_sintese() -> None:
    phases = [phase for phase in Phase if phase is not Phase.DIRECT_INFERENCE]

    assert phases[-1] is Phase.C3_FINAL_ANSWER
    assert len(phases) == 10
