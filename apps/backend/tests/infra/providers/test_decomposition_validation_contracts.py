"""Contrato do template fixo de A.3 — Task Decomposition Validator.

Verifica as entradas e as regras do template, não a qualidade semântica de um modelo: saídas
roteirizadas e a presença de instruções não demonstram que planos ruins serão identificados.
"""
import json
import logging
import re
from pathlib import Path

import pytest

from src.domain.entities.thinking.validation_context import ValidationContext
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum as Phase
from src.infra.adapters.structured_response_parser_adapter import StructuredResponseParserAdapter
from src.infra.providers.file_prompt_template_provider import FilePromptTemplateProvider
from tests.doubles.fake_settings import FakeSettings

_A3 = Phase.A3_DECOMPOSITION_VALIDATION
_MATRIX = json.loads((Path(__file__).parents[2] / "fixtures/decomposition_validation_v1.json").read_text())
_CASES = _MATRIX["cases"]


def _provider() -> FilePromptTemplateProvider:
    return FilePromptTemplateProvider(settings=FakeSettings(), logger=logging.getLogger(__name__))


def _normalized(text: str) -> str:
    return " ".join(text.split())


def _section(heading: str) -> str:
    text = _provider().get(phase=_A3).split(f"## {heading}\n", 1)[1].split("\n## ", 1)[0]
    return _normalized(text)


def test_recebe_pedido_criterios_gerais_e_somente_o_candidato_atual() -> None:
    template = _provider().get(phase=_A3)

    assert set(re.findall(r"\{\{(\w+)\}\}", template)) == {
        "user_question", "general_acceptance_criteria", "candidate_plan"
    }
    assert "<candidate_plan>\n{{candidate_plan}}\n</candidate_plan>" in template
    assert "{{learnings}}" not in template
    assert "previous" not in template.lower()


def test_pedido_original_e_a_referencia_principal_e_conflito_com_a1_e_relatado_sem_reescrever() -> None:
    assert "primary reference" in _section("Question")
    criteria = _section("General acceptance criteria")
    assert "the question prevails" in criteria
    assert "without rewriting these criteria" in criteria


def test_rubrica_fixa_com_as_sete_dimensoes() -> None:
    rubric = _section("Validation rubric")

    for dimension in ("Fidelity", "Neutrality", "Applicability", "Criteria", "Coherence", "Coverage", "Necessity"):
        assert f"**{dimension}:**" in rubric
    assert "Do not judge the plan only by the criteria it wrote for itself" in rubric


def test_nao_resolve_nem_impoe_conclusao_alternativa() -> None:
    template = _normalized(_provider().get(phase=_A3))

    assert "do not solve the question" in template
    assert "do not calculate an alternative conclusion" in template
    assert "not which result to reach" in template
    assert "do not rewrite the plan yourself" in template


def test_nao_rejeita_automaticamente_dados_metodos_hipoteses_dependencias_e_aproximacoes() -> None:
    allowed = _section("What is not a defect")

    for item in ("numbers, formulas", "pertinent method", "explicit, justifiable hypothesis",
                 "logical dependence", "approximation, estimate or best-fit choice"):
        assert item in allowed
    assert "planning an investigation" in allowed and "anticipating its result" in allowed


def test_formato_de_saida_usa_booleano_real_e_referencias_anulaveis() -> None:
    output = _section("Output format")

    assert '"approved": false' in output and '"approved": true, "issues": []' in output
    assert "real JSON booleans" in output
    decision = _section("Decision")
    assert "`null` when the issue concerns the whole plan" in decision
    assert "never fill it without its `task_id`" in decision


@pytest.mark.parametrize("case", _CASES, ids=lambda case: case["name"])
def test_matriz_sintetica_renderiza_entradas_sem_injetar_o_parecer_esperado(case: dict) -> None:
    prompt = _provider().render(phase=_A3, variables={
        "user_question": case["question"],
        "general_acceptance_criteria": "\n".join(case["general_criteria"]),
        "candidate_plan": json.dumps(case["tasks"], ensure_ascii=False),
    })

    assert case["question"] in prompt
    assert "{{" not in prompt
    assert case["expected_review"] not in prompt


@pytest.mark.parametrize("case", _CASES, ids=lambda case: case["name"])
def test_parser_aceita_o_parecer_de_referencia_da_matriz_sem_certificar_a_semantica(case: dict) -> None:
    plan = {task["id"]: tuple(c["id"] for c in task["acceptance_criteria"]) for task in case["tasks"]}
    output = StructuredResponseParserAdapter(logger=logging.getLogger(__name__)).parse_output(
        raw_output=json.dumps(case["reference_report"]), phase=_A3,
        validation=ValidationContext(candidate_plan=plan), finish_reason="stop",
    )

    assert output.parsed["approved"] is case["reference_report"]["approved"]
    assert output.diagnostic.content_accepted


def test_matriz_cobre_planos_ruins_e_validos() -> None:
    kinds = {case["kind"] for case in _CASES}

    assert {"omitted_condition", "anticipated_result", "redundant_task"} <= kinds
    assert {"valid_numeric_data", "valid_method_and_hypothesis", "valid_dependencies", "valid_approximation"} <= kinds
