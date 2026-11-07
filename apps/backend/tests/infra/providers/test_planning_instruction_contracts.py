"""Contratos de instrução e entradas; não medem obediência semântica de um LLM.

A matriz é uma rubrica versionada para inspeção humana. O parser só é exercitado quanto
ao contrato estrutural, inclusive mostrando que um critério enviesado ainda é JSON válido.
"""
import json
import logging
from pathlib import Path

import pytest

from src.domain.entities.thinking.validation_context import ValidationContext
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum as Phase
from src.infra.adapters.structured_response_parser_adapter import StructuredResponseParserAdapter
from src.infra.providers.file_prompt_template_provider import FilePromptTemplateProvider
from tests.doubles.fake_settings import FakeSettings

_MATRIX = json.loads((Path(__file__).parents[2] / "fixtures/planning_semantics_v1.json").read_text())
_CASES = _MATRIX["cases"]


def _provider() -> FilePromptTemplateProvider:
    return FilePromptTemplateProvider(settings=FakeSettings(), logger=logging.getLogger(__name__))


def _section(phase: Phase, heading: str) -> str:
    text = _provider().get(phase=phase).split(f"## {heading}\n", 1)[1].split("\n## ", 1)[0]
    return " ".join(text.split())


@pytest.mark.parametrize("case", _CASES, ids=lambda case: case["name"])
def test_matriz_renderiza_dados_literais_nas_areas_reais_sem_injetar_o_exemplo(case: dict) -> None:
    phase = Phase.A2_TASK_DECOMPOSITION if case["phase"] == "A2" else Phase.C2_ADDITIONAL_PLANNING
    variables = {"user_question": case["question"], "max_tasks": "9"}
    if case["phase"] == "C2":
        variables.update(
            unmet_criteria="AC1: " + case["general_criteria"][0],
            global_verification_feedback=case["gap"], stored_results=case["stored_results"],
            learnings=case["learnings"], next_task_number=case["tasks"][0]["id"][1:],
        )
    prompt = _provider().render(phase=phase, variables=variables)

    assert case["question"] in prompt
    assert "{{" not in prompt
    assert case["invalid_criterion"] not in prompt
    assert case["tasks"][0]["description"] not in prompt
    if case["phase"] == "C2":
        for key in ("gap", "stored_results", "learnings"):
            assert case[key] in prompt
    else:
        a1 = _provider().render(phase=Phase.A1_GENERAL_CRITERIA, variables={"user_question": case["question"]})
        assert case["question"] in a1 and "{{" not in a1


@pytest.mark.parametrize("case", _CASES, ids=lambda case: case["name"])
def test_parser_valida_estrutura_da_matriz_sem_certificar_sua_semantica(case: dict) -> None:
    phase = Phase.A2_TASK_DECOMPOSITION if case["phase"] == "A2" else Phase.C2_ADDITIONAL_PLANNING
    parser = StructuredResponseParserAdapter(logger=logging.getLogger(__name__))
    for include_bias in (False, True):
        tasks = json.loads(json.dumps(case["tasks"]))
        if include_bias:
            tasks[0]["acceptance_criteria"][0]["description"] = case["invalid_criterion"]
        output = parser.parse_output(
            raw_output=json.dumps({"tasks": tasks}), phase=phase,
            validation=ValidationContext(max_tasks=9), finish_reason="stop",
        )
        assert output.parsed["tasks"] == tasks
        assert output.diagnostic.content_accepted


def test_a1_extrai_conteudo_sem_converter_metodo_ou_opcao_em_obrigacao() -> None:
    obligations = _section(Phase.A1_GENERAL_CRITERIA, "Instructions")
    assert "content to determine" in obligations
    assert "optional justification" in obligations
    assert "arbitrary line or word limits" in obligations
    assert "numerical tolerance" in obligations
    assert "unrequested proof" in obligations
    assert "distractor" in obligations
    assert "approve or discard them in advance" in obligations


@pytest.mark.parametrize("phase", [Phase.A2_TASK_DECOMPOSITION, Phase.C2_ADDITIONAL_PLANNING])
def test_planejamento_separa_metodo_hipotese_dado_e_resultado(phase: Phase) -> None:
    rules = _section(phase, "Evidence and investigation")
    for distinction in ("Literal data", "Method", "Hypothesis", "Result"):
        assert distinction in rules
    assert "qualitative conclusions" in rules
    assert "establish its applicability" in rules.lower()
    assert "Key Learnings" in rules
    assert "do not guess" in rules


@pytest.mark.parametrize("phase", [Phase.A2_TASK_DECOMPOSITION, Phase.C2_ADDITIONAL_PLANNING])
def test_revisao_dentro_da_geracao_cobre_determinacao_final_sem_certificado_estrutural(phase: Phase) -> None:
    review = _section(phase, "Final plan review")
    assert "Before returning the JSON" in review
    assert "period in months" in review and "distance ratio" in review
    assert "task count" in review and "JSON validity" in review
    assert "C.1" in review
    template = _provider().get(phase=phase)
    assert "solvable independently of the others" not in template
    assert "typically **2 to 4 tasks**" not in template
    assert "no access to" not in template


@pytest.mark.parametrize("phase", [Phase.A2_TASK_DECOMPOSITION, Phase.C2_ADDITIONAL_PLANNING])
def test_escopo_admite_dependencia_e_analise_final_com_explicacao(phase: Phase) -> None:
    scope = _section(phase, "Task scope and criteria")
    assert "logical dependence" in scope
    assert "final determination" in scope
    assert "integration or comparison" in scope
    assert "accompanied by the explanation" in scope
    assert "complementary, never mutually exclusive" in scope
    assert "distractor" in scope and "paraphrases" in scope


def test_c2_distingue_entrada_obtida_de_nova_investigacao_e_admite_correcao_direcionada() -> None:
    gaps = _section(Phase.C2_ADDITIONAL_PLANNING, "Content gaps and corrective investigation")
    assert "concrete contradiction or error" in gaps
    assert "do not decide which conclusion is wrong" in gaps.lower()
    assert "already obtained results as inputs" in gaps
    assert "writing the final answer" in gaps
    assert "do not reopen what has already been verified" not in _provider().get(phase=Phase.C2_ADDITIONAL_PLANNING)


def test_b1_permite_seu_objetivo_final_e_nao_forca_escolha_sem_sustentacao() -> None:
    instructions = _section(Phase.B1_TASK_RESOLUTION, "Instructions")
    assert "When this task owns the final determination" in instructions
    assert "integration or comparison" in instructions
    assert "supported approximation" in instructions
    assert "selecting an option alone" in instructions
    assert "**Do not** solve the final question" not in instructions
    assert 'concluding that "no option is correct"' not in instructions


@pytest.mark.parametrize("phase", [Phase.A1_GENERAL_CRITERIA, Phase.A2_TASK_DECOMPOSITION,
                                   Phase.C2_ADDITIONAL_PLANNING, Phase.B1_TASK_RESOLUTION])
def test_escolha_nao_e_equivalente_a_acerto_nem_ha_tolerancia_inventada(phase: Phase) -> None:
    template = " ".join(_provider().get(phase=phase).split())
    assert "supported approximation" in template
    assert "numerical tolerance" in template
    for old_command in ("as long as one of the options is selected", "only the absence of a selection",
                        "leaving the selection open is not"):
        assert old_command not in template
