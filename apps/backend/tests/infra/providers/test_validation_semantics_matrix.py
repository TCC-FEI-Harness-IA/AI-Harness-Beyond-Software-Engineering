"""Matriz de avaliação semântica da validação (thinking 04): transporte e contrato estrutural.

Os vereditos de referência da matriz são rubrica para avaliação humana ou com modelo real.
Aqui só se prova que os casos chegam às áreas reais de B.2/C.1 sem vazar o veredito esperado e
que o parser aceita qualquer relatório coerente — aprovação ou reprovação — sem julgar se ele
está semanticamente certo, recusando apenas a incoerência formal.
"""
import json
import logging
from pathlib import Path

import pytest

from src.domain.entities.thinking.validation_context import ValidationContext
from src.domain.enums.output_problem_code_enum import OutputProblemCodeEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum as Phase
from src.domain.errors.phase_parsing_error import PhaseParsingError
from src.infra.adapters.structured_response_parser_adapter import StructuredResponseParserAdapter
from src.infra.providers.file_prompt_template_provider import FilePromptTemplateProvider
from tests.doubles.fake_settings import FakeSettings

_MATRIX = json.loads((Path(__file__).parents[2] / "fixtures/validation_semantics_v1.json").read_text())
_CASES = _MATRIX["cases"]
_PHASES = {"B2": Phase.B2_TASK_VERIFICATION, "C1": Phase.C1_GLOBAL_VERIFICATION}


def _criteria(case: dict) -> str:
    return "\n".join(f"- `{item['id']}`: {item['description']}" for item in case["criteria"])


def _learnings(case: dict) -> str:
    return "\n".join(f"- {learning}" for learning in case["learnings"])


def _variables(case: dict) -> dict[str, str]:
    if case["phase"] == "B2":
        return {"preliminary_result": case["result"], "task_acceptance_criteria": _criteria(case),
                "learnings": _learnings(case), "revision_proposal": "None: this task does not review stored results."}
    stored = "\n\n".join(f"## {item['task_id']} — {item['title']}\n\n{item['content']}"
                         for item in case["stored_results"])
    return {"stored_results": stored, "general_acceptance_criteria": _criteria(case), "learnings": _learnings(case),
            "result_revisions": "No stored result has been revised or suspended."}


def _report(case: dict, unmet: list[str], decision: str) -> str:
    return json.dumps({
        "criteria_evaluation": [
            {"criterion_id": item["id"], "met": item["id"] not in unmet,
             "justification": case["reference_justification"]}
            for item in case["criteria"]
        ],
        "unmet_criteria_ids": unmet,
        "decision": decision,
    }, ensure_ascii=False)


def _parse(case: dict, raw_output: str):
    return StructuredResponseParserAdapter(logger=logging.getLogger(__name__)).parse_output(
        raw_output=raw_output, phase=_PHASES[case["phase"]], finish_reason="stop",
        validation=ValidationContext(expected_criteria_ids=tuple(item["id"] for item in case["criteria"])),
    )


def test_matriz_cobre_aceitacoes_sem_coincidencia_exata_e_reprovacoes_reais() -> None:
    categories = {case["category"] for case in _CASES}

    assert _MATRIX["version"] == 1
    assert {"exact", "approximation", "elimination", "estimate", "identifiable_error", "contradiction",
            "no_contradiction", "missing_content", "presentation_only", "implicit_content",
            "false_equality"} <= categories
    assert {case["reference_decision"] for case in _CASES} == {"approved", "reproved"}
    assert {case["phase"] for case in _CASES} == {"B2", "C1"}
    names = [case["name"] for case in _CASES]
    assert len(names) == len(set(names))
    for case in _CASES:
        assert case["review_checks"], case["name"]
        assert (case["reference_decision"] == "approved") == (case["reference_unmet"] == []), case["name"]


@pytest.mark.parametrize("case", _CASES, ids=lambda case: case["name"])
def test_caso_renderiza_nas_areas_reais_sem_vazar_o_veredito_de_referencia(case: dict) -> None:
    variables = _variables(case)
    prompt = FilePromptTemplateProvider(settings=FakeSettings(), logger=logging.getLogger(__name__)).render(
        phase=_PHASES[case["phase"]], variables=variables,
    )

    assert "{{" not in prompt
    for value in variables.values():
        assert value in prompt
    assert case["reference_justification"] not in prompt
    for check in case["review_checks"]:
        assert check not in prompt
    assert "## Evidence and consistency policy" in prompt


@pytest.mark.parametrize("case", _CASES, ids=lambda case: case["name"])
def test_parser_aceita_relatorio_coerente_nos_dois_sentidos_sem_certificar_a_semantica(case: dict) -> None:
    reference = _parse(case, _report(case, case["reference_unmet"], case["reference_decision"]))
    every_id = [item["id"] for item in case["criteria"]]
    opposite_unmet = [] if case["reference_unmet"] else every_id[:1]
    opposite = _parse(case, _report(case, opposite_unmet, "reproved" if opposite_unmet else "approved"))

    assert reference.diagnostic.content_accepted and opposite.diagnostic.content_accepted
    assert reference.parsed["decision"] != opposite.parsed["decision"]


@pytest.mark.parametrize("case", _CASES, ids=lambda case: case["name"])
def test_parser_recusa_criterio_nao_atendido_com_decisao_aprovada(case: dict) -> None:
    raw_output = _report(case, [case["criteria"][0]["id"]], "approved")

    with pytest.raises(PhaseParsingError) as error:
        _parse(case, raw_output)

    assert error.value.diagnostic.problem.code is OutputProblemCodeEnum.DECISION_CONSISTENCY
    assert error.value.diagnostic.content_accepted is False
