"""Contratos dos templates para o critério técnico `<task_id>-TECH` (nova fase de validação — 02).

Verificam as áreas e as instruções entregues ao modelo e o transporte da matriz sintética
`technical_validation_v1.json`. Instrução presente não prova obediência: um modelo real pode aprovar
uma derivação errada ou reprovar uma aproximação legítima; isso só uma avaliação semântica mede.
"""
import json
import logging
import re
from pathlib import Path

import pytest

from src.domain.entities.thinking.acceptance_criterion import AcceptanceCriterion
from src.domain.entities.thinking.harness_criteria import technical_criterion
from src.domain.entities.thinking.task import Task
from src.domain.entities.thinking.validation_context import ValidationContext
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum as Phase
from src.infra.adapters.structured_response_parser_adapter import StructuredResponseParserAdapter
from src.infra.providers.file_prompt_template_provider import FilePromptTemplateProvider
from tests.doubles.fake_settings import FakeSettings

_MATRIX = json.loads((Path(__file__).parents[2] / "fixtures/technical_validation_v1.json").read_text())
_CASES = _MATRIX["cases"]
_TECH_HEADING_B2 = "Technical validity criterion (`<task id>-TECH`)"
_TECH_HEADING_B1 = "Technical validity (`<task id>-TECH`)"


def _provider() -> FilePromptTemplateProvider:
    return FilePromptTemplateProvider(settings=FakeSettings(), logger=logging.getLogger(__name__))


def _flat(text: str) -> str:
    return " ".join(text.split())


def _raw(phase: Phase) -> str:
    return _provider().get(phase=phase)


def _template(phase: Phase) -> str:
    return _flat(_raw(phase))


def _section(phase: Phase, heading: str) -> str:
    template = _raw(phase)
    assert f"## {heading}\n" in template, (phase, heading)
    return _flat(template.split(f"## {heading}\n", 1)[1].split("\n## ", 1)[0])


def _headings(phase: Phase) -> list[str]:
    return re.findall(r"^## (.+)$", _raw(phase), flags=re.MULTILINE)


# ── B.2: entradas explícitas em áreas separadas ────────────────────────────


def test_b2_recebe_tarefa_resultado_criterios_revisao_e_aprendizados_em_areas_separadas() -> None:
    template = _raw(Phase.B2_TASK_VERIFICATION)

    assert set(re.findall(r"\{\{(\w+)\}\}", template)) == {
        "task_description", "preliminary_result", "task_acceptance_criteria", "revision_proposal", "learnings"
    }
    areas = ["Task", "Preliminary result", "Acceptance criteria for this task", "Proposed revision", "Key Learnings"]
    placeholders = ["task_description", "preliminary_result", "task_acceptance_criteria", "revision_proposal",
                    "learnings"]
    for area, placeholder in zip(areas, placeholders):
        assert f"{{{{{placeholder}}}}}" in _section(Phase.B2_TASK_VERIFICATION, area), area
    assert _headings(Phase.B2_TASK_VERIFICATION)[:5] == areas


def test_b2_descricao_explica_o_escopo_sem_substituir_resultado_nem_virar_criterio() -> None:
    area = _section(Phase.B2_TASK_VERIFICATION, "Task")

    assert "explains the scope and the objective of the task" in area
    assert "it is not the result under evaluation" in area
    assert "it is not an additional set of criteria" in area


def test_b2_lista_efetiva_inclui_tech_fixo_e_rev_quando_houver() -> None:
    area = _section(Phase.B2_TASK_VERIFICATION, "Acceptance criteria for this task")

    assert "criteria written in planning" in area
    assert "`<task id>-TECH`" in area and "the harness adds to every task" in area
    assert "`<task id>-REV`" in area
    assert "Evaluate every one of them" in area


def test_b2_aprova_somente_com_todos_os_criterios_incluindo_tech_e_rev() -> None:
    instructions = _section(Phase.B2_TASK_VERIFICATION, "Instructions")

    assert "`approved` only when **all** criteria were met, including `<task id>-TECH`" in instructions
    assert "`<task id>-REV`" in instructions


def test_b2_verifica_sem_resolver_completar_ou_editar_criterios() -> None:
    instructions = _section(Phase.B2_TASK_VERIFICATION, "Instructions")

    assert "do not write the corrected resolution" in instructions
    assert "do not complete a missing step yourself" in instructions
    assert "do not edit, add or remove criteria" in instructions
    assert "Do not ignore, rewrite or waive any criterion received" in instructions


def test_b2_registra_defeito_de_planejamento_sem_retornar_ao_planejamento_nem_dispensar_criterio() -> None:
    instructions = _section(Phase.B2_TASK_VERIFICATION, "Instructions")

    assert "state the planning defect explicitly in its justification" in instructions
    assert "cannot send the task back to planning" in instructions


def test_b2_nao_aprova_criterio_com_resultado_imposto_invalido_mesmo_com_tech_atendido() -> None:
    technical = _section(Phase.B2_TASK_VERIFICATION, "Technical verification of the local criteria")

    assert "consider the criterion **met (`met: true`)**" not in technical
    assert "mark that planned criterion **not met (`met: false`)**" in technical
    assert "state the planning defect in its justification" in technical
    assert "`<task id>-TECH` may be met by the technically correct result" in technical
    assert "the task remains `reproved` while any planned criterion is not met" in technical
    assert "Do not force an incorrect calculation to satisfy an invalid planned requirement" in technical


def test_b2_distingue_resultado_imposto_invalido_de_aproximacao_ou_melhor_ajuste_fundamentados() -> None:
    technical = _section(Phase.B2_TASK_VERIFICATION, "Technical verification of the local criteria")
    selection = _section(Phase.B2_TASK_VERIFICATION, "Selection criteria")

    assert "A criterion asking for a supported approximation or best-fit selection" in technical
    assert "does not mandate a particular unsupported result" in technical
    assert "do not introduce a universal exact-match requirement" in technical
    assert "lack of an exact match is not, by itself, a reason for rejection" in selection
    assert "closest option to a value obtained through an identifiable error does not meet it" in selection


# ── B.2: critério técnico ───────────────────────────────────────────────────


def test_b2_tech_avalia_o_objetivo_da_tarefa_independente_dos_criterios_planejados_e_de_rev() -> None:
    tech = _section(Phase.B2_TASK_VERIFICATION, _TECH_HEADING_B2)

    assert "accomplishes **this task's objective**" in tech
    assert "data, methods and conditions that apply" in tech
    assert "can meet every planned criterion and still fail it" in tech
    assert "independent of `<task id>-REV`" in tech


def test_b2_conferencia_da_base_analitica_precede_aproximacao_e_melhor_ajuste() -> None:
    headings = _headings(Phase.B2_TASK_VERIFICATION)
    tech = _section(Phase.B2_TASK_VERIFICATION, _TECH_HEADING_B2)

    assert headings.index(_TECH_HEADING_B2) < headings.index("Evidence and consistency policy")
    assert headings.index(_TECH_HEADING_B2) < headings.index("Selection criteria")
    assert "Check the analytical basis **before** accepting an approximation" in tech
    for dimension in ("**Premises:**", "**Referents and conditions:**", "**Method:**", "**Support:**",
                      "**Consistency:**", "**Approximations and hypotheses:**"):
        assert dimension in tech
    assert "temporal stage" in tech
    assert "contributions and conditions relevant to the analysis" in tech
    assert "the presence of an explanation is not enough" in tech


def test_b2_distincoes_de_premissa_fonte_proximidade_e_hipotese() -> None:
    tech = _section(Phase.B2_TASK_VERIFICATION, _TECH_HEADING_B2)

    assert "A supplied datum is not an inferred result" in tech
    assert "the absence of information does not demonstrate its negation" in tech
    assert "a convenient hypothesis does not become a fact without support" in tech
    assert "Narrative coherence does not establish attribution to a source" in tech
    assert "Do not invent a verifiable reference" in tech
    assert "do not require an external lookup or a bibliographic citation" in tech
    assert "does not establish that the value came from a valid model" in tech
    assert "being conceivable or not forbidden is not enough" in tech
    assert "same standard of implicit content and of support to every hypothesis or option compared" in tech
    assert "Keep pertinent contextual inferences" in tech


def test_b2_preserva_aproximacoes_e_restricoes_explicitas_do_usuario() -> None:
    tech = _section(Phase.B2_TASK_VERIFICATION, _TECH_HEADING_B2)

    assert "Approximations, estimates, elimination and best fit remain valid when supported" in tech
    assert "there is no universal tolerance" in tech
    assert "no requirement to calculate directly up to every answer" in tech
    assert "Explicit constraints of the user, including a required precision or exactness, remain mandatory" in tech
    assert "an anticipation written by the planner is not an obligation of the user" in tech


def test_b2_conferencia_por_outro_angulo_e_opcional_e_nao_exige_segunda_solucao() -> None:
    tech = _section(Phase.B2_TASK_VERIFICATION, _TECH_HEADING_B2)

    assert "When simple and pertinent to the task, cross-check the result from another angle" in tech
    for angle in ("direction of a variation", "limiting case", "compatibility between parts of the text",
                  "temporal relation", "referent or unit", "consequence of a generalization"):
        assert angle in tech
    assert "not a mandatory list of techniques" in tech
    assert "do not need to produce a second complete solution" in tech


def test_b2_tech_nao_cobra_outras_tarefas_formato_final_justificativa_externa_ou_exatidao() -> None:
    tech = _section(Phase.B2_TASK_VERIFICATION, _TECH_HEADING_B2)

    assert "covers only this task's objective" in tech
    for limit in ("analyses that belong to other tasks", "the final answer format",
                  "an external justification that was not requested",
                  "an exactness incompatible with a supported estimate"):
        assert limit in tech


def test_b2_justificativa_aponta_dado_premissa_e_relacao_e_orienta_a_nova_tentativa() -> None:
    tech = _section(Phase.B2_TASK_VERIFICATION, _TECH_HEADING_B2)

    assert "point to the relevant datum or passage, the decisive premise and the relation actually checked" in tech
    assert "Saying that the explanation is complete or restating its conclusion is not a justification" in tech
    assert "name the datum, relation, hypothesis or step that fails and what the next attempt must investigate" in tech


def test_b2_exemplo_de_saida_avalia_tech_como_os_demais_criterios() -> None:
    output = _section(Phase.B2_TASK_VERIFICATION, "Output format")

    assert '"criterion_id": "T2-TECH", "met": false' in output
    assert '"unmet_criteria_ids": ["T2-TECH"]' in output
    assert '"decision": "reproved"' in output


# ── B.1: o executor conhece TECH antes de resolver ─────────────────────────


def test_b1_conhece_tech_e_a_lista_efetiva_antes_de_resolver() -> None:
    area = _section(Phase.B1_TASK_RESOLUTION, "Acceptance criteria for this task")
    tech = _section(Phase.B1_TASK_RESOLUTION, _TECH_HEADING_B1)

    assert "`<task id>-TECH`" in area and "`<task id>-REV`" in area
    assert "the validator will evaluate this resolution" in area
    assert "Meeting the planned criteria does not replace it" in tech


def test_b1_confere_a_base_analitica_antes_de_aproximar_ou_escolher_por_melhor_ajuste() -> None:
    headings = _headings(Phase.B1_TASK_RESOLUTION)
    tech = _section(Phase.B1_TASK_RESOLUTION, _TECH_HEADING_B1)

    assert headings.index(_TECH_HEADING_B1) < headings.index("Evidence and consistency policy")
    assert headings.index(_TECH_HEADING_B1) < headings.index("Calculated result and chosen option")
    assert "Before choosing an approximation, an estimate or a best-fit option, check the analytical basis" in tech
    for rule in ("never presented as a fact", "the absence of information does not demonstrate its negation",
                 "temporal stage", "the method applies under the stated conditions",
                 "actually support the conclusion", "do not invent a verifiable reference",
                 "same standard of support and implicit content to every hypothesis or option compared"):
        assert rule in tech, rule
    assert "covers only this task's objective" in tech


def test_b1_e_b2_mantem_o_mesmo_placeholder_de_criterios_e_b1_nao_recebe_area_nova() -> None:
    assert set(re.findall(r"\{\{(\w+)\}\}", _raw(Phase.B1_TASK_RESOLUTION))) == {
        "task_description", "task_acceptance_criteria", "learnings", "previous_attempts", "results_under_review"
    }


# ── Planejadores, A.3, B.4 e fase C ────────────────────────────────────────


@pytest.mark.parametrize("phase", [Phase.A2_TASK_DECOMPOSITION, Phase.C2_ADDITIONAL_PLANNING])
def test_planejadores_nao_emitem_identificadores_reservados(phase: Phase) -> None:
    template = _template(phase)

    assert "`-TECH` and `-REV` are reserved" in template
    assert "every task automatically receives `<task id>-TECH`" in template


def test_a3_nao_reprova_plano_pela_ausencia_do_criterio_tecnico_sintetico() -> None:
    allowed = _section(Phase.A3_DECOMPOSITION_VALIDATION, "What is not a defect")

    assert "the absence of a technical-validity criterion" in allowed
    assert "adds `<task id>-TECH` to every task at execution" in allowed


def test_b4_nao_transforma_tech_rev_ou_vereditos_em_fatos() -> None:
    template = _template(Phase.B4_LEARNINGS_EXTRACTION)

    assert "harness criteria (`T1-TECH`, `T1-REV`)" in template
    assert "the validator and its verdicts" in template


@pytest.mark.parametrize("phase", [Phase.C1_GLOBAL_VERIFICATION, Phase.C3_FINAL_ANSWER])
def test_c1_e_c3_nao_recebem_tech_como_criterio_global(phase: Phase) -> None:
    assert "TECH" not in _raw(phase)


def test_politica_compartilhada_continua_identica_em_b1_b2_e_c1() -> None:
    policies = {_section(phase, "Evidence and consistency policy")
                for phase in (Phase.B1_TASK_RESOLUTION, Phase.B2_TASK_VERIFICATION, Phase.C1_GLOBAL_VERIFICATION)}

    assert len(policies) == 1


# ── Matriz sintética: transporte e contrato, sem vazar a referência ────────


def _task(case: dict) -> Task:
    return Task(
        id=case["task"]["id"], title=case["task"]["title"], description=case["task"]["description"],
        acceptance_criteria=tuple(AcceptanceCriterion(**criterion) for criterion in case["criteria"]),
    )


def _variables(case: dict) -> dict[str, str]:
    task = _task(case)
    return {
        "task_description": f"### {task.id} — {task.title}\n\n{task.description}",
        "preliminary_result": case["preliminary_result"],
        "task_acceptance_criteria": "\n".join(f"- `{c.id}`: {c.description}" for c in task.verification_criteria()),
        "revision_proposal": "None: this task does not review stored results.",
        "learnings": "\n".join(f"- {learning}" for learning in case["learnings"]),
    }


def test_matriz_tem_casos_negativos_e_controles_positivos_com_referencia_completa() -> None:
    assert _MATRIX["version"] == 1
    polarities = {case["polarity"] for case in _CASES}
    categories = {case["category"] for case in _CASES}

    assert polarities == {"negative", "positive"}
    assert {"unsupported_premise", "method_applicability", "direction_check", "temporal_stage",
            "best_fit_over_error"} <= categories
    assert {"intermediate_scope", "estimate", "supported_hypothesis", "approximation", "contextual_inference",
            "scope_limits"} <= categories
    for case in _CASES:
        expected = [c.id for c in _task(case).verification_criteria()]
        assert list(case["reference"]["met"]) == expected, case["name"]
        tech_met = case["reference"]["met"][technical_criterion(case["task"]["id"]).id]
        assert tech_met is (case["polarity"] == "positive"), case["name"]
        planned = {criterion_id: met for criterion_id, met in case["reference"]["met"].items()
                   if not criterion_id.endswith("-TECH")}
        assert all(planned.values()), "os casos negativos isolam a falha em TECH"
        assert case["reference"]["decision"] == ("approved" if tech_met else "reproved")
        assert case["review_checks"], case["name"]


@pytest.mark.parametrize("case", _CASES, ids=lambda case: case["name"])
def test_caso_chega_as_areas_reais_de_b2_sem_vazar_referencia(case: dict) -> None:
    variables = _variables(case)
    prompt = _provider().render(phase=Phase.B2_TASK_VERIFICATION, variables=variables)

    assert "{{" not in prompt
    for value in variables.values():
        assert value in prompt
    assert f"`{case['task']['id']}-TECH`: {technical_criterion(case['task']['id']).description}" in prompt
    assert case["reference"]["rationale"] not in prompt
    for check in case["review_checks"]:
        assert check not in prompt


@pytest.mark.parametrize("case", _CASES, ids=lambda case: case["name"])
def test_parser_aceita_o_relatorio_de_referencia_e_o_oposto_sem_julgar_semantica(case: dict) -> None:
    parser = StructuredResponseParserAdapter(logger=logging.getLogger(__name__))
    expected = tuple(case["reference"]["met"])
    tech = technical_criterion(case["task"]["id"]).id

    def report(met: dict[str, bool]) -> str:
        unmet = [criterion_id for criterion_id, value in met.items() if not value]
        return json.dumps({
            "criteria_evaluation": [{"criterion_id": criterion_id, "met": value, "justification": "conferido"}
                                    for criterion_id, value in met.items()],
            "unmet_criteria_ids": unmet, "decision": "reproved" if unmet else "approved",
        })

    opposite = {**case["reference"]["met"], tech: not case["reference"]["met"][tech]}
    for met in (case["reference"]["met"], opposite):
        parsed = parser.parse_output(raw_output=report(met), phase=Phase.B2_TASK_VERIFICATION,
                                     validation=ValidationContext(expected_criteria_ids=expected)).parsed
        assert parsed["decision"] == ("approved" if all(met.values()) else "reproved")


@pytest.mark.parametrize("phase", [phase for phase in Phase
                                   if phase not in (Phase.B3_RESULT_STORAGE, Phase.DIRECT_INFERENCE)])
def test_nenhum_template_contem_os_exemplos_ou_referencias_da_matriz(phase: Phase) -> None:
    template = _template(phase)

    for case in _CASES:
        assert _flat(case["preliminary_result"]) not in template
        assert case["reference"]["rationale"] not in template
        assert case["task"]["title"] not in template
