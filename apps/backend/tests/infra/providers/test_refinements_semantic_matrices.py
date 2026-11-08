"""Matrizes semânticas dos refinamentos 03: versionamento, transporte e contrato.

`decomposition_validation_v2.json` e `technical_validation_v2.json` estendem as versões 1 sem alterá-las;
`final_answer_fidelity_v1.json` é nova. Estes testes renderizam os templates reais com os casos, conferem
que os campos de referência nunca chegam ao modelo e que o parser aceita relatórios coerentes nos dois
sentidos — inclusive o parecer contraditório de A.3, o que mostra que só uma avaliação com modelo real
mede a qualidade do julgamento. Nenhum caso é pontuado aqui.
"""
import json
import logging
from pathlib import Path

import pytest

from src.domain.entities.thinking.acceptance_criterion import AcceptanceCriterion
from src.domain.entities.thinking.harness_criteria import technical_criterion
from src.domain.entities.thinking.learning import Learning
from src.domain.entities.thinking.task import Task
from src.domain.entities.thinking.validation_context import ValidationContext
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum as Phase
from src.domain.services.learnings_memory import LearningsMemory
from src.infra.adapters.structured_response_parser_adapter import StructuredResponseParserAdapter
from src.infra.providers.file_prompt_template_provider import FilePromptTemplateProvider
from tests.doubles.fake_settings import FakeSettings

_FIXTURES = Path(__file__).parents[2] / "fixtures"
_SRC = Path(__file__).parents[3] / "src"
_TEMPLATE_PHASES = [phase for phase in Phase if phase not in (Phase.B3_RESULT_STORAGE, Phase.DIRECT_INFERENCE)]


def _load(name: str) -> dict:
    return json.loads((_FIXTURES / name).read_text(encoding="utf-8"))


_PLAN_V1, _PLAN_V2 = _load("decomposition_validation_v1.json"), _load("decomposition_validation_v2.json")
_TECH_V1, _TECH_V2 = _load("technical_validation_v1.json"), _load("technical_validation_v2.json")
_FINAL = _load("final_answer_fidelity_v1.json")
_PLAN_CASES = _PLAN_V2["cases"]
_TECH_CASES = _TECH_V2["cases"]
_FINAL_CASES = _FINAL["cases"]
_VALID_PLAN_KINDS = {"valid_supplied_condition", "valid_determine_whether", "valid_open_interpretation",
                     "valid_hypothesis_investigated"}


def _provider() -> FilePromptTemplateProvider:
    return FilePromptTemplateProvider(settings=FakeSettings(), logger=logging.getLogger(__name__))


def _parser() -> StructuredResponseParserAdapter:
    return StructuredResponseParserAdapter(logger=logging.getLogger(__name__))


def _flat(text: str) -> str:
    return " ".join(text.split())


def _rendered_learnings(case: dict) -> str:
    """Renderiza as notas do caso pela memória real, com a procedência que o fluxo mostraria."""
    memory = LearningsMemory()
    memory.append(learnings=[Learning(content=note["content"], source_task_id=note["source"])
                             for note in case["learnings"]])
    return memory.render()


# ── Versionamento ───────────────────────────────────────────────────────────


@pytest.mark.parametrize("v1, v2", [(_PLAN_V1, _PLAN_V2), (_TECH_V1, _TECH_V2)], ids=["A3", "TECH"])
def test_versao_2_estende_a_versao_1_sem_alterar_os_casos_anteriores(v1: dict, v2: dict) -> None:
    assert v1["version"] == 1 and v2["version"] == 2
    assert _load(v2["extends"]) == v1
    names = [case["name"] for case in (*v1["cases"], *v2["cases"])]
    assert len(names) == len(set(names))
    assert "never sent to the model" in v2["purpose"]


# ── A.3: condições, referentes, prioridades, investigação × conclusão ──────


def test_matriz_de_a3_cobre_os_defeitos_e_os_planos_validos_desta_entrega() -> None:
    kinds = {case["kind"] for case in _PLAN_CASES}

    assert {"omitted_condition_in_integration", "changed_referent", "imposed_priority",
            "anticipated_result_pair"} <= kinds
    assert _VALID_PLAN_KINDS <= kinds
    for case in _PLAN_CASES:
        assert case["reference_report"]["approved"] is (case["kind"] in _VALID_PLAN_KINDS), case["name"]


def test_par_determinar_se_e_demonstrar_tem_a_mesma_pergunta_e_julgamentos_opostos() -> None:
    by_name = {case["name"]: case for case in _PLAN_CASES}
    determine, demonstrate = by_name["determine_whether_threshold_is_exceeded"], by_name[
        "demonstrate_threshold_is_exceeded"]

    assert determine["question"] == demonstrate["question"]
    assert determine["reference_report"]["approved"] is True
    assert demonstrate["reference_report"]["approved"] is False


@pytest.mark.parametrize("case", _PLAN_CASES, ids=lambda case: case["name"])
def test_caso_de_a3_renderiza_sem_vazar_parecer_esperado_nem_relatorios(case: dict) -> None:
    prompt = _provider().render(phase=Phase.A3_DECOMPOSITION_VALIDATION, variables={
        "user_question": case["question"],
        "general_acceptance_criteria": "\n".join(case["general_criteria"]),
        "candidate_plan": json.dumps(case["tasks"], ensure_ascii=False),
    })

    assert case["question"] in prompt and "{{" not in prompt
    assert case["expected_review"] not in prompt
    for issue in case["reference_report"]["issues"]:
        assert issue["problem"] not in prompt and issue["adjustment"] not in prompt


@pytest.mark.parametrize("case", _PLAN_CASES, ids=lambda case: case["name"])
def test_parser_aceita_o_relatorio_de_referencia_de_a3(case: dict) -> None:
    plan = {task["id"]: tuple(c["id"] for c in task["acceptance_criteria"]) for task in case["tasks"]}
    output = _parser().parse_output(
        raw_output=json.dumps(case["reference_report"]), phase=Phase.A3_DECOMPOSITION_VALIDATION,
        validation=ValidationContext(candidate_plan=plan), finish_reason="stop",
    )

    assert output.parsed["approved"] is case["reference_report"]["approved"]


def test_parser_aceita_o_parecer_contraditorio_que_so_a_avaliacao_semantica_detecta() -> None:
    [case] = [case for case in _PLAN_CASES if "contradictory_report" in case]
    plan = {task["id"]: tuple(c["id"] for c in task["acceptance_criteria"]) for task in case["tasks"]}

    output = _parser().parse_output(
        raw_output=json.dumps(case["contradictory_report"]), phase=Phase.A3_DECOMPOSITION_VALIDATION,
        validation=ValidationContext(candidate_plan=plan), finish_reason="stop",
    )

    # Estruturalmente válido: o parser não lê "no blocking defect" nem converte a reprovação.
    assert output.parsed["approved"] is False
    assert case["reference_report"]["approved"] is True


# ── TECH: relação decisiva, procedência e comparações ──────────────────────


def _task(case: dict) -> Task:
    return Task(
        id=case["task"]["id"], title=case["task"]["title"], description=case["task"]["description"],
        acceptance_criteria=tuple(AcceptanceCriterion(**criterion) for criterion in case["criteria"]),
    )


def test_matriz_tecnica_v2_isola_tech_nos_negativos_e_cobre_as_categorias_da_entrega() -> None:
    categories = {(case["category"], case["polarity"]) for case in _TECH_CASES}

    assert {("decisive_relation", "negative"), ("unsupported_planning_premise", "negative"),
            ("inherited_condition", "negative"), ("inherited_condition", "positive"),
            ("comparison_consistency", "negative"), ("comparison_consistency", "positive"),
            ("comparison_objective", "negative"), ("comparison_categories", "negative"),
            ("approximation", "positive")} <= categories
    for case in _TECH_CASES:
        assert case["task"]["id"] == "T2", case["name"]
        assert list(case["reference"]["met"]) == [c.id for c in _task(case).verification_criteria()]
        tech_met = case["reference"]["met"][technical_criterion("T2").id]
        assert tech_met is (case["polarity"] == "positive"), case["name"]
        assert all(met for criterion_id, met in case["reference"]["met"].items() if not criterion_id.endswith("-TECH"))
        assert case["reference"]["decision"] == ("approved" if tech_met else "reproved")
        assert {note["source"] for note in case["learnings"]} <= {None, "T1"}


@pytest.mark.parametrize("case", _TECH_CASES, ids=lambda case: case["name"])
def test_caso_tecnico_chega_a_b2_com_procedencia_e_sem_referencia(case: dict) -> None:
    task = _task(case)
    learnings = _rendered_learnings(case)
    prompt = _provider().render(phase=Phase.B2_TASK_VERIFICATION, variables={
        "task_description": f"### {task.id} — {task.title}\n\n{task.description}",
        "preliminary_result": case["preliminary_result"],
        "task_acceptance_criteria": "\n".join(f"- `{c.id}`: {c.description}" for c in task.verification_criteria()),
        "revision_proposal": "None: this task does not review stored results.",
        "learnings": learnings,
    })

    assert "{{" not in prompt and learnings in prompt
    for note in case["learnings"]:
        label = "Question" if note["source"] is None else f"Task {note['source']}"
        assert f"- [{label}] {note['content']}" in prompt
    assert case["reference"]["rationale"] not in prompt
    assert all(check not in prompt for check in case["review_checks"])


@pytest.mark.parametrize("case", _TECH_CASES, ids=lambda case: case["name"])
def test_parser_aceita_referencia_tecnica_e_o_oposto(case: dict) -> None:
    tech = technical_criterion("T2").id
    for met in (case["reference"]["met"], {**case["reference"]["met"], tech: not case["reference"]["met"][tech]}):
        unmet = [criterion_id for criterion_id, value in met.items() if not value]
        report = json.dumps({
            "criteria_evaluation": [{"criterion_id": criterion_id, "met": value, "justification": "conferido"}
                                    for criterion_id, value in met.items()],
            "unmet_criteria_ids": unmet, "decision": "reproved" if unmet else "approved",
        })
        parsed = _parser().parse_output(raw_output=report, phase=Phase.B2_TASK_VERIFICATION,
                                        validation=ValidationContext(expected_criteria_ids=tuple(met))).parsed
        assert parsed["decision"] == ("approved" if all(met.values()) else "reproved")


# ── C.3: apresentação fiel ─────────────────────────────────────────────────


def test_matriz_de_apresentacao_cobre_marcador_traducao_codigo_e_melhor_ajuste() -> None:
    assert _FINAL["version"] == 1
    assert {case["kind"] for case in _FINAL_CASES} == {
        "identifier_in_marker_line", "translation_fidelity", "object_code_pairing", "best_fit_choice"
    }
    for case in _FINAL_CASES:
        assert case["reference_answer"] != case["invalid_presentation"]
        assert case["review_checks"]


@pytest.mark.parametrize("case", _FINAL_CASES, ids=lambda case: case["name"])
def test_caso_de_apresentacao_chega_a_c3_sem_resposta_de_referencia(case: dict) -> None:
    learnings = _rendered_learnings(case)
    prompt = _provider().render(phase=Phase.C3_FINAL_ANSWER, variables={
        "stored_results": case["stored_results"],
        "general_acceptance_criteria": "\n".join(case["general_criteria"]),
        "learnings": learnings,
    })

    assert "{{" not in prompt
    assert case["stored_results"] in prompt and learnings in prompt
    for reference in (case["reference_answer"], case["invalid_presentation"], *case["review_checks"]):
        assert reference not in prompt


@pytest.mark.parametrize("case", _FINAL_CASES, ids=lambda case: case["name"])
def test_parser_de_c3_aceita_a_apresentacao_fiel_e_a_infiel(case: dict) -> None:
    for answer in (case["reference_answer"], case["invalid_presentation"]):
        parsed = _parser().parse_output(raw_output=json.dumps({"final_answer": answer}),
                                        phase=Phase.C3_FINAL_ANSWER).parsed
        # O parser não confere fidelidade: a troca de identificador só é medida na avaliação semântica.
        assert parsed["final_answer"] == answer


# ── Isolamento: nada das matrizes entra na produção ────────────────────────


@pytest.mark.parametrize("phase", _TEMPLATE_PHASES, ids=lambda phase: phase.value)
def test_nenhum_template_contem_exemplos_ou_referencias_das_novas_matrizes(phase: Phase) -> None:
    template = _flat(_provider().get(phase=phase))

    for case in _PLAN_CASES:
        assert _flat(case["expected_review"]) not in template
        assert all(task["title"] not in template for task in case["tasks"])
    for case in _TECH_CASES:
        assert _flat(case["preliminary_result"]) not in template and case["task"]["title"] not in template
        assert case["reference"]["rationale"] not in template
    for case in _FINAL_CASES:
        assert _flat(case["reference_answer"]) not in template
        assert _flat(case["invalid_presentation"]) not in template


def test_codigo_de_producao_nao_le_as_matrizes() -> None:
    names = ("decomposition_validation_v2", "technical_validation_v2", "final_answer_fidelity_v1", "tests/fixtures")
    for path in _SRC.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert not any(name in text for name in names), path
