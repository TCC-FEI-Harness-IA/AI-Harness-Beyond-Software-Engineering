"""Contratos da política de validação (thinking 04) sobre os templates reais.

Os testes verificam o texto entregue ao modelo: a política comum a B.1/B.2/C.1, as
responsabilidades de cada fase e a remoção das autorizações irrestritas de aprovação. Não
provam que um modelo real reconhece contradições ou aproximações; isso exige avaliação
semântica com a matriz `validation_semantics_v1.json`.
"""
import logging
import re

import pytest

from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum as Phase
from src.infra.providers.file_prompt_template_provider import FilePromptTemplateProvider
from tests.doubles.fake_settings import FakeSettings

_POLICY_HEADING = "Evidence and consistency policy"
_POLICY_PHASES = (Phase.B1_TASK_RESOLUTION, Phase.B2_TASK_VERIFICATION, Phase.C1_GLOBAL_VERIFICATION)
_ALL_PHASES = (
    Phase.A1_GENERAL_CRITERIA, Phase.A2_TASK_DECOMPOSITION, Phase.A3_DECOMPOSITION_VALIDATION,
    Phase.A4_PLANNING_LEARNINGS,
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


# ── Política comum ──────────────────────────────────────────────────────────


def test_politica_de_evidencia_e_identica_em_b1_b2_e_c1() -> None:
    policies = {phase: _section(phase, _POLICY_HEADING) for phase in _POLICY_PHASES}

    assert len(set(policies.values())) == 1, "B.1, B.2 e C.1 devem aplicar o mesmo texto de política"


@pytest.mark.parametrize("phase", _POLICY_PHASES)
def test_politica_distingue_exato_aproximado_contradicao_e_conteudo_ausente(phase: Phase) -> None:
    policy = _section(phase, _POLICY_HEADING)

    for category in ("**Exact result:**", "**Approximation or best fit:**", "**Real contradiction:**",
                     "**Missing essential content:**"):
        assert category in policy
    for ground in ("comparison", "elimination", "available precision", "explicit hypothesis",
                   "order of magnitude", "contextual inference"):
        assert ground in policy
    assert "are not universal conditions" in policy
    assert "a numerical difference alone is not a defect" in policy
    assert "never becomes an equality" in policy


@pytest.mark.parametrize("phase", _POLICY_PHASES)
def test_politica_define_contradicao_real_sem_confundir_objetos_ou_hipoteses_diferentes(phase: Phase) -> None:
    policy = _section(phase, _POLICY_HEADING)

    assert "same object, quantity and conditions" in policy
    assert "contradicts its own conclusion" in policy
    assert "unit or reference is swapped" in policy
    assert "false equality" in policy
    assert "conflicts with the available data" in policy
    assert "different objects, reference frames or hypotheses are not contradictory" in policy


@pytest.mark.parametrize("phase", _POLICY_PHASES)
def test_politica_exige_determinacao_pedida_sem_delegar_calculo_a_c3(phase: Phase) -> None:
    policy = _section(phase, _POLICY_HEADING)

    assert "requested determination or an indispensable analysis is absent" in policy
    assert "eliminations already performed" in policy
    assert "dimensionless distance ratio is not the calculation of a period" in policy
    assert "cannot be delegated to the final presentation (C.3)" in policy


@pytest.mark.parametrize("phase", _POLICY_PHASES)
def test_politica_proibe_regras_universais_nos_dois_sentidos(phase: Phase) -> None:
    policy = _section(phase, _POLICY_HEADING)

    assert "no universal percentage tolerance" in policy
    assert "no ban on approximation in integer problems" in policy
    assert "no rule that any divergence fails" in policy
    assert "no rule that selecting an option passes" in policy


@pytest.mark.parametrize("phase", _ALL_PHASES)
def test_nenhum_template_fixa_tolerancia_percentual(phase: Phase) -> None:
    template = _template(phase)

    percentages = [match for match in re.findall(r"\d+(?:[.,]\d+)?\s?%[\w-]*", template) if match != "100%"]
    assert percentages == [], (phase, percentages)


# ── Autorizações irrestritas removidas ──────────────────────────────────────


@pytest.mark.parametrize("phase", [Phase.B2_TASK_VERIFICATION, Phase.C1_GLOBAL_VERIFICATION,
                                   Phase.C3_FINAL_ANSWER, Phase.C2_ADDITIONAL_PLANNING])
def test_selecao_da_opcao_mais_proxima_nao_e_aprovacao_automatica(phase: Phase) -> None:
    template = _template(phase)

    for old_command in (
        "if the result **explicitly selects a single option** as the one with the closest value",
        "approximations are allowed as long as an option is chosen",
        "The criterion is **not met** only when",
        "including when they chose it as the one whose value is closest to the calculated one, which is a valid "
        "selection",
        "as long as one of the options is selected",
    ):
        assert old_command not in template, (phase, old_command)


# ── B.1 ──────────────────────────────────────────────────────────────────────


def test_b1_separa_resultado_calculado_da_opcao_escolhida_sem_igualdade_falsa() -> None:
    choice = _section(Phase.B1_TASK_RESOLUTION, "Calculated result and chosen option")

    assert "calculated or inferred result" in choice and "selected option" in choice
    assert "never that the two are equal" in choice
    assert "without any calculation reaching the option's value" in choice
    assert "label it as an estimate" in choice


def test_b1_nao_usa_comparacao_de_opcoes_para_mascarar_erro_identificavel() -> None:
    choice = _section(Phase.B1_TASK_RESOLUTION, "Calculated result and chosen option")

    assert "Comparing options does not mask a calculation error" in choice
    assert "already included in a conditional" in choice
    assert "correct the derivation rather than choosing the option nearest to the wrong value" in choice
    assert "obligation to select does not make the analysis correct" in choice


def test_b1_trata_numero_ou_conclusao_do_plano_como_hipotese_a_verificar() -> None:
    instructions = _section(Phase.B1_TASK_RESOLUTION, "Instructions")

    assert "planning-derived values, conclusions or unstated assumptions" in instructions
    assert "hypotheses to verify, not demonstrated truths" in instructions
    assert "Preserve literal inputs copied from the user's request" in instructions
    assert "without forcing a mathematically incorrect calculation" in instructions


def test_b1_retentativa_corrige_defeito_concreto_sem_abandonar_conclusao_sustentada() -> None:
    previous = _section(Phase.B1_TASK_RESOLUTION, "Previous attempts at this task")

    assert "concrete problem" in previous
    assert "make the supporting link explicit instead of switching to another conclusion" in previous
    assert "demonstrates an error in data, conditions or calculation, correct it" in previous


# ── B.2 ──────────────────────────────────────────────────────────────────────


def test_b2_confere_relacoes_entre_formula_condicoes_dados_e_conclusao() -> None:
    technical = _section(Phase.B2_TASK_VERIFICATION, "Technical verification of the local criteria")

    assert "The presence of an explanation is not its correctness" in technical
    for relation in ("applies under the stated conditions", "data and units", "follows from the previous one",
                     "conclusion follows from the calculation or analysis shown"):
        assert relation in technical
    assert "conditioning error" in technical
    assert "Name the concrete defect" in technical


def test_b2_admite_conteudo_implicito_com_o_mesmo_padrao_para_as_opcoes_comparadas() -> None:
    technical = _section(Phase.B2_TASK_VERIFICATION, "Technical verification of the local criteria")

    assert "same standard of implicit content to every option compared" in technical
    assert "collective decision-making" in technical
    assert "only when the criterion explicitly demands that wording" in technical
    assert "Avoid **hyper-literalism**" in _template(Phase.B2_TASK_VERIFICATION)


def test_b2_aprova_selecao_fundamentada_e_reprova_a_que_se_apoia_em_erro() -> None:
    selection = _section(Phase.B2_TASK_VERIFICATION, "Selection criteria")

    assert "grounds the choice" in selection
    assert "lack of an exact match is not, by itself, a reason for rejection" in selection
    assert "closest option to a value obtained through an identifiable error does not meet it" in selection
    assert "creates a non-existent option" in selection


def test_b2_nao_exige_resposta_global_de_tarefa_intermediaria_nem_formato_final() -> None:
    template = _template(Phase.B2_TASK_VERIFICATION)

    assert "An intermediate task is not required to answer the whole question" in template
    assert "marker line" in template and "is not an internal obligation" in template
    assert "Do not ignore, rewrite or waive any criterion received" in template


# ── C.1 ──────────────────────────────────────────────────────────────────────


def test_c1_avalia_suficiencia_e_consistencia_da_uniao() -> None:
    union = _section(Phase.C1_GLOBAL_VERIFICATION, "Consistency of the union")

    assert "compare the results with each other" in union
    assert "Do not decide which result is wrong" in union
    assert "explicit hypotheses" in union and "not a contradiction" in union
    assert "never write that they correspond exactly" in union


def test_c1_aprovacao_cita_evidencia_e_reprovacao_nomeia_o_que_investigar() -> None:
    justification = _section(Phase.C1_GLOBAL_VERIFICATION, "Justification of each verdict")

    assert "When approving, cite the evidence produced" in justification
    assert "grounding of the approximation or selection" in justification
    assert "When rejecting, identify the gap or contradiction and what must be investigated" in justification
    assert "without performing the missing analysis" in justification
    assert "deciding in advance which task is wrong" in justification


def test_c1_nao_aprova_aproximacao_independentemente_do_resto_da_analise() -> None:
    instructions = _section(Phase.C1_GLOBAL_VERIFICATION, "Instructions")

    assert "The approximation is not approved independently of the rest of the analysis" in instructions
    assert "same standard of implicit content to every option" in instructions


@pytest.mark.parametrize("example", [
    "12.6 liters", "select 13", "obtain 23", "20 is selected", "eliminate", "estimate",
    "already conditioned", "The distance between the numbers is not the reason",
    "same objects and conditions", "different explicit hypotheses", "distance ratio", "period in months",
    "measured 8.4 cm corresponds exactly to an option of 8 cm",
])
def test_c1_exemplifica_aceitacoes_sem_coincidencia_exata_e_reprovacoes_reais(example: str) -> None:
    examples = _section(Phase.C1_GLOBAL_VERIFICATION, "Examples of sufficiency, consistency and real gaps")

    assert example in examples


def test_c1_preserva_formato_e_traducao_como_apresentacao() -> None:
    template = _template(Phase.C1_GLOBAL_VERIFICATION)

    assert "The absence of `FINAL_ANSWER: C` in the results is not a content gap" in template
    assert "do not make a language criterion unmet" in template


# ── C.2 e C.3 ──────────────────────────────────────────────────────────────


def test_c2_investiga_a_lacuna_sem_tarefa_de_escolher_a_mais_proxima() -> None:
    gaps = _section(Phase.C2_ADDITIONAL_PLANNING, "Content gaps and corrective investigation")

    assert 'only "choose the closest option"' in gaps
    assert "would cover the known defect" in gaps
    assert "previously approved result may be investigated when the feedback gives a concrete reason" in gaps
    assert "which prior claim it confirms or corrects" in gaps
    assert "do not decide which conclusion is wrong" in gaps.lower()


def test_c3_apresenta_aproximacao_e_estimativa_sem_converter_em_igualdade() -> None:
    template = _template(Phase.C3_FINAL_ANSWER)

    assert "chose it by best fit, approximation or elimination" in template
    assert "Present an approximate result as approximate and an estimate as an estimate" in template
    assert "never turn a best fit into an exact equality" in template
    assert "without new analytical reasoning" in template


# ── A.1 e A.2 harmonizados ──────────────────────────────────────────────────


@pytest.mark.parametrize("phase", [Phase.A1_GENERAL_CRITERIA, Phase.A2_TASK_DECOMPOSITION,
                                   Phase.C2_ADDITIONAL_PLANNING])
def test_planejamento_nao_exige_coincidencia_exata_nem_aprova_selecao_por_si(phase: Phase) -> None:
    template = _template(phase)

    assert "exact coincidence" in template
    assert "direct calculation" in template
    assert "Selecting an option alone" in template or "selection of an option as evidence" in template
    assert "estimate" in template
