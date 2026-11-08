"""Contratos de prompt dos refinamentos 03 (mudanças 1–4, 5.1, 6 e 7).

Conferem que as instruções relevantes chegam aos templates reais e às mensagens que o orquestrador
acrescenta, que as fases continuam com as mesmas variáveis e que nada específico de benchmark entrou.
Instrução presente não prova obediência: a capacidade de um modelo real de achar o defeito certo sem
reprovar casos válidos só é medida pelas matrizes semânticas (`decomposition_validation_v2.json`,
`technical_validation_v2.json` e `final_answer_fidelity_v1.json`), que estes testes não pontuam.
"""
import logging
import re

import pytest

import src.application.usecases.ralph_thinking_usecase as usecase
from src.domain.entities.thinking.harness_criteria import TECHNICAL_CRITERION_DESCRIPTION
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum as Phase
from src.infra.providers.file_prompt_template_provider import FilePromptTemplateProvider
from tests.doubles.fake_settings import FakeSettings

_LEARNINGS_PHASES = (
    Phase.B1_TASK_RESOLUTION, Phase.B2_TASK_VERIFICATION, Phase.B4_LEARNINGS_EXTRACTION,
    Phase.C1_GLOBAL_VERIFICATION, Phase.C2_ADDITIONAL_PLANNING, Phase.C3_FINAL_ANSWER,
)
_TEMPLATE_PHASES = [phase for phase in Phase if phase not in (Phase.B3_RESULT_STORAGE, Phase.DIRECT_INFERENCE)]
_PLACEHOLDERS = {
    Phase.A2_TASK_DECOMPOSITION: {"user_question", "plan_revision", "max_tasks"},
    Phase.A3_DECOMPOSITION_VALIDATION: {"user_question", "general_acceptance_criteria", "candidate_plan"},
    Phase.B1_TASK_RESOLUTION: {
        "task_description", "task_acceptance_criteria", "learnings", "previous_attempts", "results_under_review"
    },
    Phase.B2_TASK_VERIFICATION: {
        "task_description", "preliminary_result", "task_acceptance_criteria", "revision_proposal", "learnings"
    },
    Phase.B4_LEARNINGS_EXTRACTION: {"task_description", "approved_result", "task_history", "learnings"},
    Phase.C3_FINAL_ANSWER: {"stored_results", "general_acceptance_criteria", "learnings"},
}


def _provider() -> FilePromptTemplateProvider:
    return FilePromptTemplateProvider(settings=FakeSettings(), logger=logging.getLogger(__name__))


def _flat(text: str) -> str:
    return " ".join(text.split())


def _raw(phase: Phase) -> str:
    return _provider().get(phase=phase)


def _template(phase: Phase) -> str:
    return _flat(_raw(phase))


def _section(phase: Phase, heading: str) -> str:
    raw = _raw(phase)
    assert f"## {heading}\n" in raw, (phase, heading)
    return _flat(raw.split(f"## {heading}\n", 1)[1].split("\n## ", 1)[0])


def _paragraph(phase: Phase, start: str) -> str:
    raw = _raw(phase)
    assert start in raw, (phase, start)
    return _flat(raw.split(start, 1)[1].split("\n\n", 1)[0])


@pytest.mark.parametrize("phase", list(_PLACEHOLDERS), ids=lambda phase: phase.value)
def test_refinamentos_nao_mudam_as_variaveis_dos_templates(phase: Phase) -> None:
    assert set(re.findall(r"\{\{(\w+)\}\}", _raw(phase))) == _PLACEHOLDERS[phase]


# ── Mudança 1: A.3 confere condições, referentes e prioridades impostas ─────


def test_a3_confronta_objetivo_e_condicoes_do_pedido_com_a_investigacao_planejada() -> None:
    rubric = _section(Phase.A3_DECOMPOSITION_VALIDATION, "Validation rubric")

    for aspect in ("referents, units, temporal relations, simultaneous conditions and constraints",
                   "investigates the object the request asks about"):
        assert aspect in rubric, aspect
    assert "including in their **integration**" in rubric
    assert "a condition that holds within two separate tasks must still apply when a later task joins" in rubric


def test_a3_reconhece_prioridade_introduzida_pelo_planejador() -> None:
    rubric = _section(Phase.A3_DECOMPOSITION_VALIDATION, "Validation rubric")

    assert "**imposed priorities**" in rubric
    for priority in ('"the most general"', '"the simplest"', '"the most specific"', '"the most complete"'):
        assert priority in rubric, priority
    assert "unless the request supplies it or a task investigates whether it applies" in rubric


def test_a3_distingue_dado_fornecido_de_conclusao_e_nao_exige_repetir_o_enunciado() -> None:
    section = _section(Phase.A3_DECOMPOSITION_VALIDATION, "Supplied data, investigation and conclusion")

    assert "copying it into a task or criterion where it is pertinent is required" in section
    assert "does not need to repeat the whole question" in section
    assert "notes extracted from the question after approval do not justify" in section


def test_a3_exemplo_de_condicao_perdida_pede_preservar_sem_dar_o_resultado() -> None:
    rubric = _section(Phase.A3_DECOMPOSITION_VALIDATION, "Validation rubric")

    assert "mandatory stops on only one of the vehicles" in rubric
    assert "without stating the resulting difference" in rubric


# ── Mudança 2: investigação × conclusão; reprovar só defeito bloqueante ────


def test_a3_admite_investigacoes_abertas_de_interpretacao_comparacao_e_hipotese() -> None:
    section = _section(Phase.A3_DECOMPOSITION_VALIDATION, "Supplied data, investigation and conclusion")

    for kind in ("interpret", "compare", "formulate a conceptual opposition", "check a hypothesis",
                 "decide whether a correction is needed"):
        assert kind in section, kind
    assert "Asking for an interpretation is not prescribing one" in section


def test_a3_tem_exemplos_contrastivos_de_investigacao_e_conclusao_imposta() -> None:
    section = _section(Phase.A3_DECOMPOSITION_VALIDATION, "Supplied data, investigation and conclusion")

    assert "Identify the divergence between the two statements and justify the interpretation." in section
    assert "Show that the first statement represents category X" in section
    assert "Check whether the procedure needs to be corrected." in section
    assert "The procedure must be considered incorrect" in section


def test_a3_reprova_so_com_defeito_bloqueante_e_ajuste_real() -> None:
    decision = _section(Phase.A3_DECOMPOSITION_VALIDATION, "Decision")

    assert "makes the specification wrong, incomplete or infeasible" in decision
    for not_blocking in ("Style preferences", "a different but harmless number of tasks",
                         "an alternative wording"):
        assert not_blocking in decision, not_blocking
    assert "If your own analysis concludes that a point needs no adjustment, it is not an issue" in decision
    assert "the problematic requirement, the rule it violates" in decision
    assert "do not solve the request or introduce a correct answer for the planner to reproduce" in decision
    # Preservados da versão anterior (testados em test_decomposition_validation_contracts.py).
    assert "`null` when the issue concerns the whole plan" in decision
    assert "not which result to reach" in decision


def test_a2_mantem_coerencia_com_a_rubrica_de_condicoes_e_prioridades() -> None:
    evidence = _section(Phase.A2_TASK_DECOMPOSITION, "Evidence and investigation")

    assert "**Conditions in the integration:**" in evidence
    assert "including the task that joins partial findings" in evidence
    assert "**Priorities:**" in evidence and '"the most general"' in evidence


def test_c2_harmoniza_a_revisao_final_sem_passar_por_a3() -> None:
    review = _section(Phase.C2_ADDITIONAL_PLANNING, "Final plan review")

    assert "a condition stated for part of the problem survives in the task that joins the findings" in review
    assert "a priority (such as \"the most general\") that the request does not supply" in review
    assert "validation stage" not in _template(Phase.C2_ADDITIONAL_PLANNING).lower()


# ── Mudança 3: TECH confere a relação decisiva ─────────────────────────────


def test_b2_tech_exige_conferencia_proporcional_da_relacao_decisiva() -> None:
    tech = _section(Phase.B2_TASK_VERIFICATION, "Technical validity criterion (`<task id>-TECH`)")

    assert "**Decisive relation.**" in tech
    for check in ("substitute a solution into its equation", "check the link between quantities",
                  "an applicability condition", "the direction of a comparison",
                  "the correspondence between a feature and a definition"):
        assert check in tech, check
    for weak in ("A long explanation", "the mention of a numerical method", "calling a value plausible",
                 "restating the conclusion"):
        assert weak in tech, weak
    assert "does not replace that check" in tech


def test_b2_tech_reprova_sem_entregar_a_resolucao_e_preserva_aproximacoes() -> None:
    tech = _section(Phase.B2_TASK_VERIFICATION, "Technical validity criterion (`<task id>-TECH`)")

    assert "without writing the corrected resolution or completing the missing analysis yourself" in tech
    assert "does not impose a universal tolerance, an exact equality or a second complete solution" in tech
    assert "a claimed root that, substituted back" in tech


def test_b1_conhece_a_conferencia_da_relacao_decisiva() -> None:
    tech = _section(Phase.B1_TASK_RESOLUTION, "Technical validity (`<task id>-TECH`)")

    assert "Check the decisive relation" in tech
    assert "substitute a solution into its equation" in tech
    assert "Describing a method or calling a value plausible is not a check" in tech


def test_descricao_central_de_tech_harmoniza_relacao_decisiva_e_procedencia() -> None:
    description = _flat(TECHNICAL_CRITERION_DESCRIPTION)

    assert "the decisive relation is actually checked" in description
    assert (
        "appearing in the task description or in the Key Learnings does not by itself support a premise" in description
    )
    assert "a result of an earlier task used within its stated scope and conditions" in description
    assert "compared candidates are held to the same conditions and standard of support" in description
    assert "It covers only this task's objective" in description


# ── Mudança 4: procedência visível e hipóteses preservadas ─────────────────


def test_paragrafo_de_procedencia_e_identico_em_todas_as_fases_que_recebem_aprendizados() -> None:
    paragraphs = {phase: _paragraph(phase, "**Origin labels.**") for phase in _LEARNINGS_PHASES}

    assert len(set(paragraphs.values())) == 1
    text = next(iter(paragraphs.values()))
    assert "`[Question]`" in text and "`[Task T1]`" in text and "`[Tasks T1, T3]`" in text
    assert "The label states origin, not truth" in text
    assert "A claim does not become supported because it appears in these notes or in a task description" in text
    assert "The label is not part of the note" in text


@pytest.mark.parametrize("phase", _LEARNINGS_PHASES, ids=lambda phase: phase.value)
def test_paragrafo_de_procedencia_fica_na_area_key_learnings(phase: Phase) -> None:
    assert "**Origin labels.**" in _section(phase, "Key Learnings")


def test_b2_premissas_nao_ganham_suporte_por_estarem_no_contexto_e_sem_refazer_tarefas() -> None:
    tech = _section(Phase.B2_TASK_VERIFICATION, "Technical validity criterion (`<task id>-TECH`)")

    assert "A premise is not supported merely because it appears in the task description or in Key Learnings" in tech
    assert "a conditional result does not become unconditional" in tech
    assert "Do not require redoing earlier tasks" in tech
    assert "do not reject a note merely because it came from another task" in tech


def test_b1_premissas_do_planejamento_precisam_de_justificativa_e_heranca_conserva_condicoes() -> None:
    tech = _section(Phase.B1_TASK_RESOLUTION, "Technical validity (`<task id>-TECH`)")

    assert "is not supported merely by being there" in tech
    assert "an inherited result keeps its scope, conditions and qualifiers" in tech
    assert "a conditional estimate does not become a guarantee" in tech
    assert "You do not need to redo earlier tasks" in tech


def test_b4_copia_so_o_conteudo_sem_rotulo_e_preserva_hipoteses_sem_inventar() -> None:
    template = _template(Phase.B4_LEARNINGS_EXTRACTION)

    assert "copy only the text of the note after its origin label, never the label" in template
    assert "**Hypotheses and qualifiers:**" in template
    assert "an estimate under an assumption stays an estimate under that assumption, not a guarantee" in template
    assert "Do not add a qualifier that the approved result does not state" in template
    assert "The history of corrections" in template and "is not a fact about the problem" in template
    assert "origin labels (`[Question]`, `[Task T1]`)" in _section(Phase.B4_LEARNINGS_EXTRACTION, "Instructions")


# ── Mudança 5.1: retentativas enfrentam a objeção ─────────────────────────


def test_b1_nova_tentativa_enfrenta_a_objecao_e_revisa_restricoes_proprias() -> None:
    area = _section(Phase.B1_TASK_RESOLUTION, "Previous attempts at this task")

    assert "Confront each objection" in area
    assert "show concretely why it does not invalidate the earlier conclusion" in area
    assert "Rewording the same reasoning, or switching to another candidate without a new basis" in area
    assert "show what changed and why the defect no longer occurs" in area
    assert "re-examine the restrictions you assumed yourself" in area
    assert "do not relax explicit data or tolerances to keep a preferred candidate" in area
    assert "an unlimited exhaustive search is not required" in area


def test_instrucao_de_retentativa_do_orquestrador_enfrenta_a_objecao_sem_campo_novo() -> None:
    instruction = _flat(usecase._RETRY_INSTRUCTION_CONTENT)

    assert "Confront each objection" in instruction
    assert "rewording the same reasoning or switching to another candidate without a new basis does not resolve it" in (
        instruction
    )
    assert "show what changed and why the defect no longer occurs" in instruction
    assert "restrictions you assumed yourself" in instruction
    assert "{unmet}" in instruction


def test_instrucao_de_revisao_do_plano_mira_o_defeito_e_nao_vira_dado_do_usuario() -> None:
    instruction = _flat(usecase._PLAN_REVISION_INSTRUCTION)

    assert "removes the concrete defect named by each issue" in instruction
    assert "The original question remains the reference" in instruction
    assert "does not turn a conclusion or a requirement absent from the question into user data" in instruction
    assert "keep the unknown results open" in instruction


def test_a2_area_do_parecer_tambem_explica_que_o_relatorio_nao_e_dado_do_usuario() -> None:
    area = _section(Phase.A2_TASK_DECOMPOSITION, "Previous candidate and validation report")

    assert "The report is not user data" in area
    assert "keeping the question above as the reference" in area


def test_b2_avalia_o_resultado_atual_sem_precisar_dos_pareceres_anteriores() -> None:
    instructions = _section(Phase.B2_TASK_VERIFICATION, "Instructions")

    assert "You evaluate only the current result; earlier verdicts are not provided and are not needed" in instructions
    assert "A reworded explanation that keeps a defective premise, relation or calculation still fails" in instructions


# ── Mudança 6: comparações consistentes ─────────────────────────────────────


def test_politica_de_comparacao_e_identica_em_b1_e_b2() -> None:
    sections = {_section(phase, "Comparison consistency")
                for phase in (Phase.B1_TASK_RESOLUTION, Phase.B2_TASK_VERIFICATION)}

    assert len(sections) == 1
    section = sections.pop()
    assert "under the same relevant conditions and the same standard of support" in section
    assert "consistency does not mean demanding irrelevant features from all of them" in section
    assert "A feature shared by the candidates does not distinguish them" in section
    assert "do not replace the requested objective with another priority" in section
    assert '"the best account of the aspect asked" separate from "the other statements are false"' in section
    assert "Do not invent criteria to force a unique answer" in section
    assert "a linear dependence is a polynomial dependence of degree one, not its negation" in section
    assert "Best fit, elimination and approximation remain valid when supported" in section


# ── Mudança 7: C.3 preserva a conclusão e os identificadores ───────────────


def test_c3_confere_identificadores_inclusive_na_linha_marcadora_e_corrige_o_rascunho() -> None:
    check = _section(Phase.C3_FINAL_ANSWER, "Fidelity check before answering")

    assert "**Final identifier check.**" in check
    assert "in any line the request requires, such as a final marker line" in check
    assert "A marker line presents the approved conclusion; it is not a new choice" in check
    assert "correct the draft from the results" in check


def test_c3_copia_o_identificador_que_os_resultados_ja_associam_e_usa_notas_so_para_conferir() -> None:
    check = _section(Phase.C3_FINAL_ANSWER, "Fidelity check before answering")

    assert "When the stored results themselves attach an identifier to the determined content" in check
    assert "they never replace the results as the source of the analytic answer" in check
    assert "periods" in check


def test_c3_tem_exemplos_de_codigo_e_de_linha_marcadora() -> None:
    examples = _section(Phase.C3_FINAL_ANSWER, "Examples of valid and invalid presentation")

    assert "`P-1 — pump; V-3 — valve`" in examples
    assert "the marker contradicts the approved item" in examples


def test_c3_continua_apresentacao_sem_fase_ou_chamada_nova() -> None:
    template = _template(Phase.C3_FINAL_ANSWER)

    assert "This stage is about **presentation, not reasoning**" in template
    assert "It is part of the presentation, not a separate stage" in template
    assert "stored_results" in _raw(Phase.C3_FINAL_ANSWER)
    assert "global verification report" not in template.lower()


# ── Generalidade ────────────────────────────────────────────────────────────


@pytest.mark.parametrize("phase", _TEMPLATE_PHASES, ids=lambda phase: phase.value)
def test_refinamentos_nao_embutem_casos_do_benchmark(phase: Phase) -> None:
    template = _template(phase).lower()

    for case in ("boric", "bórico", "butadiene", "s-trans", "plasmid", "isotop", "toll", "pedágio",
                 "parfit", "singer", "schrödinger", "pkc", "gpqa", "mmlu"):
        assert case not in template, (phase, case)
