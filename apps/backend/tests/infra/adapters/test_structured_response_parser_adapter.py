import json
import logging
from typing import Any

import pytest

from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.domain.errors.phase_parsing_error import PhaseParsingError
from src.infra.adapters.structured_response_parser_adapter import StructuredResponseParserAdapter

_FASE_A1 = ThinkingPhaseEnum.A1_GENERAL_CRITERIA
_FASE_B4 = ThinkingPhaseEnum.B4_LEARNINGS_EXTRACTION

_CRITERIOS_VALIDOS: dict[str, Any] = {
    "general_acceptance_criteria": [{"id": "AC1", "description": "responder em portugues"}]
}
_TAREFA_VALIDA: dict[str, Any] = {
    "id": "T1",
    "title": "titulo",
    "description": "descricao",
    "expected_input": "entrada",
    "expected_output": "saida",
    "acceptance_criteria": [{"id": "T1-AC1", "description": "criterio"}],
}
_VERIFICACAO_VALIDA: dict[str, Any] = {
    "decision": "approved",
    "criteria_evaluation": [{"criterion_id": "T1-AC1", "met": True, "justification": "atende"}],
    "unmet_criteria_ids": [],
}


def _parser() -> StructuredResponseParserAdapter:
    return StructuredResponseParserAdapter(logger=logging.getLogger("teste.parser"))


def _parse(raw_output: str, phase: ThinkingPhaseEnum = _FASE_A1) -> dict[str, Any]:
    return _parser().parse(raw_output=raw_output, phase=phase)


# ── Extração ─────────────────────────────────────────────────────────────────


def test_extrai_json_puro() -> None:
    assert _parse('{"general_acceptance_criteria": [{"id": "AC1", "description": "d"}]}') == {
        "general_acceptance_criteria": [{"id": "AC1", "description": "d"}]
    }


def test_extrai_json_de_cerca_com_linguagem() -> None:
    bruto = '```json\n{"general_acceptance_criteria": [{"id": "AC1", "description": "d"}]}\n```'

    assert _parse(bruto)["general_acceptance_criteria"][0]["id"] == "AC1"


def test_extrai_json_de_cerca_sem_linguagem() -> None:
    bruto = '```\n{"general_acceptance_criteria": [{"id": "AC1", "description": "d"}]}\n```'

    assert _parse(bruto)["general_acceptance_criteria"][0]["id"] == "AC1"


def test_extrai_json_cercado_por_texto_solto() -> None:
    bruto = (
        "Claro! Segue a resposta:\n"
        '{"general_acceptance_criteria": [{"id": "AC1", "description": "d"}]}\n'
        "Espero ter ajudado."
    )

    assert _parse(bruto)["general_acceptance_criteria"][0]["id"] == "AC1"


def test_texto_sem_nenhum_json_e_recusado() -> None:
    with pytest.raises(PhaseParsingError):
        _parse("nao ha nenhum objeto json nesta resposta")


def test_json_sintaticamente_invalido_e_recusado() -> None:
    with pytest.raises(PhaseParsingError):
        _parse('{"general_acceptance_criteria": [')


def test_string_vazia_e_recusada() -> None:
    with pytest.raises(PhaseParsingError):
        _parse("")


def test_json_que_e_lista_e_recusado() -> None:
    with pytest.raises(PhaseParsingError):
        _parse('[{"general_acceptance_criteria": []}]')


def test_erro_de_parsing_carrega_fase_motivo_e_saida_truncada() -> None:
    bruto = "x" * 900

    with pytest.raises(PhaseParsingError) as erro:
        _parse(bruto, phase=_FASE_B4)

    assert erro.value.phase is _FASE_B4
    assert erro.value.reason
    assert len(erro.value.raw_output) < len(bruto)


def test_fase_sem_saida_estruturada_e_recusada() -> None:
    with pytest.raises(PhaseParsingError):
        _parse('{"result": "x"}', phase=ThinkingPhaseEnum.B3_RESULT_STORAGE)


# ── Schema A.1 ───────────────────────────────────────────────────────────────


def _parse_a1(payload: dict[str, Any]) -> dict[str, Any]:
    return _parser().parse(raw_output=json.dumps(payload), phase=_FASE_A1)


def test_a1_valido() -> None:
    assert _parse_a1(_CRITERIOS_VALIDOS) == _CRITERIOS_VALIDOS


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"general_acceptance_criteria": "AC1"},
        {"general_acceptance_criteria": []},
        {"general_acceptance_criteria": ["AC1"]},
        {"general_acceptance_criteria": [{"description": "d"}]},
        {"general_acceptance_criteria": [{"id": "AC1"}]},
        {"general_acceptance_criteria": [{"id": "", "description": "d"}]},
        {"general_acceptance_criteria": [{"id": "AC1", "description": "   "}]},
        {"general_acceptance_criteria": [{"id": 1, "description": "d"}]},
    ],
)
def test_a1_invalido_e_recusado(payload: dict[str, Any]) -> None:
    with pytest.raises(PhaseParsingError):
        _parse_a1(payload)


# ── Schema A.2 / C.2 ─────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "fase",
    [ThinkingPhaseEnum.A2_TASK_DECOMPOSITION, ThinkingPhaseEnum.C2_ADDITIONAL_PLANNING],
)
def test_decomposicao_valida(fase: ThinkingPhaseEnum) -> None:
    payload = {"tasks": [_TAREFA_VALIDA]}

    assert _parser().parse(raw_output=json.dumps(payload), phase=fase) == payload


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"tasks": {}},
        {"tasks": []},
        {"tasks": ["T1"]},
        {"tasks": [{**_TAREFA_VALIDA, "title": ""}]},
        {"tasks": [{k: v for k, v in _TAREFA_VALIDA.items() if k != "expected_input"}]},
        {"tasks": [{**_TAREFA_VALIDA, "acceptance_criteria": []}]},
        {"tasks": [{**_TAREFA_VALIDA, "acceptance_criteria": "criterio"}]},
        {"tasks": [{**_TAREFA_VALIDA, "acceptance_criteria": [{"id": "T1-AC1"}]}]},
    ],
)
def test_decomposicao_invalida_e_recusada(payload: dict[str, Any]) -> None:
    with pytest.raises(PhaseParsingError):
        _parser().parse(
            raw_output=json.dumps(payload),
            phase=ThinkingPhaseEnum.A2_TASK_DECOMPOSITION,
        )


# ── Schema B.1 ───────────────────────────────────────────────────────────────


def test_b1_valido() -> None:
    payload = {"task_id": "T1", "result": "markdown da resolucao"}

    assert _parser().parse(
        raw_output=json.dumps(payload),
        phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION,
    ) == payload


@pytest.mark.parametrize("payload", [{}, {"result": ""}, {"result": "   "}, {"result": ["x"]}])
def test_b1_invalido_e_recusado(payload: dict[str, Any]) -> None:
    with pytest.raises(PhaseParsingError):
        _parser().parse(
            raw_output=json.dumps(payload),
            phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION,
        )


# ── Schema B.2 / C.1 ─────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "fase",
    [ThinkingPhaseEnum.B2_TASK_VERIFICATION, ThinkingPhaseEnum.C1_GLOBAL_VERIFICATION],
)
def test_verificacao_valida(fase: ThinkingPhaseEnum) -> None:
    assert _parser().parse(
        raw_output=json.dumps(_VERIFICACAO_VALIDA),
        phase=fase,
    ) == _VERIFICACAO_VALIDA


def test_verificacao_reprovada_valida() -> None:
    payload = {
        "decision": "reproved",
        "criteria_evaluation": [{"criterion_id": "T1-AC1", "met": False, "justification": "nao atende"}],
        "unmet_criteria_ids": ["T1-AC1"],
    }

    assert _parser().parse(
        raw_output=json.dumps(payload),
        phase=ThinkingPhaseEnum.B2_TASK_VERIFICATION,
    ) == payload


def test_verificacao_aceita_lista_de_avaliacoes_vazia() -> None:
    payload = {"decision": "approved", "criteria_evaluation": [], "unmet_criteria_ids": []}

    assert _parser().parse(
        raw_output=json.dumps(payload),
        phase=ThinkingPhaseEnum.C1_GLOBAL_VERIFICATION,
    ) == payload


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {**_VERIFICACAO_VALIDA, "decision": "talvez"},
        {**_VERIFICACAO_VALIDA, "criteria_evaluation": "tudo certo"},
        {**_VERIFICACAO_VALIDA, "criteria_evaluation": ["T1-AC1"]},
        {**_VERIFICACAO_VALIDA, "criteria_evaluation": [{"met": True, "justification": "j"}]},
        {
            **_VERIFICACAO_VALIDA,
            "criteria_evaluation": [{"criterion_id": "T1-AC1", "met": "sim", "justification": "j"}],
        },
        {**_VERIFICACAO_VALIDA, "criteria_evaluation": [{"criterion_id": "T1-AC1", "met": True}]},
        {**_VERIFICACAO_VALIDA, "unmet_criteria_ids": "T1-AC1"},
        {**_VERIFICACAO_VALIDA, "decision": "reproved", "unmet_criteria_ids": [1]},
    ],
)
def test_verificacao_invalida_e_recusada(payload: dict[str, Any]) -> None:
    with pytest.raises(PhaseParsingError):
        _parser().parse(
            raw_output=json.dumps(payload),
            phase=ThinkingPhaseEnum.B2_TASK_VERIFICATION,
        )


def test_aprovado_com_pendencias_e_incoerente() -> None:
    payload = {**_VERIFICACAO_VALIDA, "unmet_criteria_ids": ["T1-AC1"]}

    with pytest.raises(PhaseParsingError, match="incoerente"):
        _parser().parse(
            raw_output=json.dumps(payload),
            phase=ThinkingPhaseEnum.B2_TASK_VERIFICATION,
        )


def test_reprovado_sem_pendencias_e_incoerente() -> None:
    payload = {**_VERIFICACAO_VALIDA, "decision": "reproved"}

    with pytest.raises(PhaseParsingError, match="incoerente"):
        _parser().parse(
            raw_output=json.dumps(payload),
            phase=ThinkingPhaseEnum.C1_GLOBAL_VERIFICATION,
        )


# ── Schema B.4 ───────────────────────────────────────────────────────────────


def test_b4_valido() -> None:
    payload = {"learnings": ["fato seco 1", "fato seco 2"]}

    assert _parser().parse(raw_output=json.dumps(payload), phase=_FASE_B4) == payload


def test_b4_aceita_lista_de_aprendizados_vazia() -> None:
    payload: dict[str, Any] = {"learnings": []}

    assert _parser().parse(raw_output=json.dumps(payload), phase=_FASE_B4) == payload


@pytest.mark.parametrize("payload", [{}, {"learnings": "fato"}, {"learnings": [{"content": "fato"}]}])
def test_b4_invalido_e_recusado(payload: dict[str, Any]) -> None:
    with pytest.raises(PhaseParsingError):
        _parser().parse(raw_output=json.dumps(payload), phase=_FASE_B4)


# ── Schema C.3 ───────────────────────────────────────────────────────────────


def test_c3_valido() -> None:
    payload = {"final_answer": "D) Nenhuma das anteriores"}

    assert _parser().parse(
        raw_output=json.dumps(payload),
        phase=ThinkingPhaseEnum.C3_FINAL_ANSWER,
    ) == payload


@pytest.mark.parametrize("payload", [{}, {"final_answer": ""}, {"final_answer": "  "}, {"final_answer": 42}])
def test_c3_invalido_e_recusado(payload: dict[str, Any]) -> None:
    with pytest.raises(PhaseParsingError):
        _parser().parse(
            raw_output=json.dumps(payload),
            phase=ThinkingPhaseEnum.C3_FINAL_ANSWER,
        )
