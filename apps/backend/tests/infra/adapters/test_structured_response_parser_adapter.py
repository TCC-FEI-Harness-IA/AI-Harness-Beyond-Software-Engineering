import json
import logging
from typing import Any

import pytest

from src.domain.entities.thinking.validation_context import ValidationContext
from src.domain.enums.budget_limit_enum import BudgetLimitEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.domain.errors.phase_parsing_error import PhaseParsingError
from src.infra.adapters.structured_response_parser_adapter import StructuredResponseParserAdapter

_FASE_A1 = ThinkingPhaseEnum.A1_GENERAL_CRITERIA
_FASE_B4 = ThinkingPhaseEnum.B4_LEARNINGS_EXTRACTION
_FASE_A3 = ThinkingPhaseEnum.A3_PLANNING_LEARNINGS

_CRITERIOS_VALIDOS: dict[str, Any] = {
    "general_acceptance_criteria": [{"id": "AC1", "description": "responder em portugues"}]
}
_TAREFA_VALIDA: dict[str, Any] = {
    "id": "T1",
    "title": "titulo",
    "description": "descricao",
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


def test_decomposicao_com_entrada_e_saida_ainda_e_aceita() -> None:
    # Os campos deixaram de ser pedidos, mas um modelo que ainda os envie não tem o lote recusado.
    payload = {"tasks": [{**_TAREFA_VALIDA, "expected_input": "entrada", "expected_output": "saida"}]}

    assert _parser().parse(raw_output=json.dumps(payload), phase=ThinkingPhaseEnum.A2_TASK_DECOMPOSITION) == payload


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"tasks": {}},
        {"tasks": []},
        {"tasks": ["T1"]},
        {"tasks": [{**_TAREFA_VALIDA, "title": ""}]},
        {"tasks": [{k: v for k, v in _TAREFA_VALIDA.items() if k != "description"}]},
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


def _planejar(
    tarefas: list[dict[str, Any]],
    validation: ValidationContext | None = None,
    fase: ThinkingPhaseEnum = ThinkingPhaseEnum.A2_TASK_DECOMPOSITION,
) -> dict[str, Any]:
    return _parser().parse(raw_output=json.dumps({"tasks": tarefas}), phase=fase, validation=validation)


def _tarefa_com_id(task_id: str) -> dict[str, Any]:
    return {**_TAREFA_VALIDA, "id": task_id, "acceptance_criteria": [{"id": f"{task_id}-AC1", "description": "c"}]}


def test_a1_com_ids_de_criterio_repetidos_e_recusado() -> None:
    payload = {
        "general_acceptance_criteria": [
            {"id": "AC1", "description": "um"},
            {"id": "AC1", "description": "dois"},
        ]
    }

    with pytest.raises(PhaseParsingError, match="AC1"):
        _parse_a1(payload)


def test_decomposicao_com_ids_de_tarefa_repetidos_no_lote_e_recusada() -> None:
    with pytest.raises(PhaseParsingError, match="T1"):
        _planejar([_tarefa_com_id("T1"), _tarefa_com_id("T1")])


def test_decomposicao_com_ids_de_criterio_repetidos_na_tarefa_e_recusada() -> None:
    tarefa = {
        **_TAREFA_VALIDA,
        "acceptance_criteria": [{"id": "T1-AC1", "description": "a"}, {"id": "T1-AC1", "description": "b"}],
    }

    with pytest.raises(PhaseParsingError, match="T1-AC1"):
        _planejar([tarefa])


def test_decomposicao_que_reusa_id_de_tarefa_ja_criada_e_recusada() -> None:
    contexto = ValidationContext(known_task_ids=frozenset({"T1"}))

    with pytest.raises(PhaseParsingError, match="T1"):
        _planejar([_tarefa_com_id("T1")], validation=contexto, fase=ThinkingPhaseEnum.C2_ADDITIONAL_PLANNING)


def test_decomposicao_dentro_do_teto_e_aceita() -> None:
    contexto = ValidationContext(max_tasks=2, known_task_ids=frozenset({"T1"}))

    resultado = _planejar([_tarefa_com_id("T2"), _tarefa_com_id("T3")], validation=contexto)

    assert [tarefa["id"] for tarefa in resultado["tasks"]] == ["T2", "T3"]


def test_decomposicao_acima_do_teto_e_recusada_apontando_o_limite_de_tarefas() -> None:
    contexto = ValidationContext(max_tasks=1)

    with pytest.raises(PhaseParsingError, match="no máximo 1") as erro:
        _planejar([_tarefa_com_id("T1"), _tarefa_com_id("T2")], validation=contexto)

    assert erro.value.limit is BudgetLimitEnum.TASKS_PER_SESSION


def test_recusas_estruturais_nao_apontam_limite() -> None:
    with pytest.raises(PhaseParsingError) as erro:
        _planejar([])

    assert erro.value.limit is None


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

_FASES_DE_VERIFICACAO = [ThinkingPhaseEnum.B2_TASK_VERIFICATION, ThinkingPhaseEnum.C1_GLOBAL_VERIFICATION]


def _esperando(*ids: str) -> ValidationContext:
    return ValidationContext(expected_criteria_ids=tuple(ids))


def _avaliacao(criterion_id: str, met: bool = True) -> dict[str, Any]:
    return {"criterion_id": criterion_id, "met": met, "justification": "porque sim"}


def _relatorio(
    *avaliacoes: dict[str, Any], decision: str | None = None, unmet: list[str] | None = None
) -> dict[str, Any]:
    falhas = [a["criterion_id"] for a in avaliacoes if not a["met"]]
    return {
        "decision": decision or ("reproved" if falhas else "approved"),
        "criteria_evaluation": list(avaliacoes),
        "unmet_criteria_ids": falhas if unmet is None else unmet,
    }


def _verificar(
    payload: dict[str, Any],
    esperados: tuple[str, ...] = ("T1-AC1",),
    fase: ThinkingPhaseEnum = ThinkingPhaseEnum.B2_TASK_VERIFICATION,
) -> dict[str, Any]:
    return _parser().parse(raw_output=json.dumps(payload), phase=fase, validation=_esperando(*esperados))


@pytest.mark.parametrize("fase", _FASES_DE_VERIFICACAO)
def test_verificacao_valida(fase: ThinkingPhaseEnum) -> None:
    assert _verificar(_VERIFICACAO_VALIDA, fase=fase) == _VERIFICACAO_VALIDA


def test_verificacao_reprovada_valida() -> None:
    payload = _relatorio(_avaliacao("T1-AC1", met=False))

    assert _verificar(payload) == payload


def test_verificacao_aceita_avaliacoes_em_ordem_diferente_da_dos_criterios() -> None:
    payload = _relatorio(_avaliacao("AC2"), _avaliacao("AC1"), _avaliacao("AC3", met=False))

    assert _verificar(payload, esperados=("AC1", "AC2", "AC3")) == payload


@pytest.mark.parametrize("fase", _FASES_DE_VERIFICACAO)
def test_verificacao_exige_o_contexto_de_validacao(fase: ThinkingPhaseEnum) -> None:
    with pytest.raises(ValueError, match="contexto de validação"):
        _parser().parse(raw_output=json.dumps(_VERIFICACAO_VALIDA), phase=fase)


@pytest.mark.parametrize("fase", _FASES_DE_VERIFICACAO)
def test_verificacao_exige_os_criterios_esperados_no_contexto(fase: ThinkingPhaseEnum) -> None:
    with pytest.raises(ValueError, match="contexto de validação"):
        _parser().parse(raw_output=json.dumps(_VERIFICACAO_VALIDA), phase=fase, validation=ValidationContext())


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
        _verificar(payload)


def test_relatorio_sem_avaliacoes_e_recusado_mesmo_aprovado() -> None:
    payload = {"decision": "approved", "criteria_evaluation": [], "unmet_criteria_ids": []}

    with pytest.raises(PhaseParsingError, match="T1-AC1"):
        _verificar(payload)


def test_avaliacao_faltante_e_recusada() -> None:
    payload = _relatorio(_avaliacao("AC1"))

    with pytest.raises(PhaseParsingError, match="AC2"):
        _verificar(payload, esperados=("AC1", "AC2"))


def test_avaliacao_repetida_e_recusada() -> None:
    payload = _relatorio(_avaliacao("AC1"), _avaliacao("AC1"))

    with pytest.raises(PhaseParsingError, match="mais de uma vez"):
        _verificar(payload, esperados=("AC1",))


def test_avaliacao_de_criterio_desconhecido_e_recusada() -> None:
    payload = _relatorio(_avaliacao("AC1"), _avaliacao("INEXISTENTE"))

    with pytest.raises(PhaseParsingError, match="INEXISTENTE"):
        _verificar(payload, esperados=("AC1",))


def test_aprovado_com_avaliacao_negativa_e_recusado() -> None:
    payload = _relatorio(_avaliacao("T1-AC1", met=False), decision="approved", unmet=[])

    with pytest.raises(PhaseParsingError, match="incoerente"):
        _verificar(payload)


def test_aprovado_com_pendencias_e_incoerente() -> None:
    payload = {**_VERIFICACAO_VALIDA, "unmet_criteria_ids": ["T1-AC1"]}

    with pytest.raises(PhaseParsingError, match="incoerente"):
        _verificar(payload)


def test_reprovado_sem_pendencias_e_incoerente() -> None:
    payload = {**_VERIFICACAO_VALIDA, "decision": "reproved"}

    with pytest.raises(PhaseParsingError, match="incoerente"):
        _verificar(payload, fase=ThinkingPhaseEnum.C1_GLOBAL_VERIFICATION)


def test_reprovado_com_todas_as_avaliacoes_positivas_e_recusado() -> None:
    payload = _relatorio(_avaliacao("T1-AC1"), decision="reproved", unmet=["T1-AC1"])

    with pytest.raises(PhaseParsingError, match="pendências"):
        _verificar(payload)


def test_pendencia_desconhecida_e_recusada() -> None:
    payload = _relatorio(_avaliacao("AC1", met=False), decision="reproved", unmet=["AC1", "DESCONHECIDO"])

    with pytest.raises(PhaseParsingError, match="pendências"):
        _verificar(payload, esperados=("AC1",))


def test_pendencia_repetida_e_recusada() -> None:
    payload = _relatorio(_avaliacao("AC1", met=False), decision="reproved", unmet=["AC1", "AC1"])

    with pytest.raises(PhaseParsingError, match="repet"):
        _verificar(payload, esperados=("AC1",))


def test_pendencias_que_nao_correspondem_as_avaliacoes_negativas_sao_recusadas() -> None:
    payload = _relatorio(_avaliacao("AC1"), _avaliacao("AC2", met=False), decision="reproved", unmet=["AC1"])

    with pytest.raises(PhaseParsingError, match="pendências"):
        _verificar(payload, esperados=("AC1", "AC2"))


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


# ── Schema A.3 ───────────────────────────────────────────────────────────────


def test_a3_valido() -> None:
    payload = {"learnings": ["Alternativas: A) 2; B) 4", "Velocidade: 20 m/s"]}

    assert _parser().parse(raw_output=json.dumps(payload), phase=_FASE_A3) == payload


def test_a3_aceita_lista_de_aprendizados_vazia() -> None:
    payload: dict[str, Any] = {"learnings": []}

    assert _parser().parse(raw_output=json.dumps(payload), phase=_FASE_A3) == payload


@pytest.mark.parametrize("payload", [{}, {"learnings": "fato"}, {"learnings": [{"content": "fato"}]}])
def test_a3_invalido_e_recusado(payload: dict[str, Any]) -> None:
    with pytest.raises(PhaseParsingError) as erro:
        _parser().parse(raw_output=json.dumps(payload), phase=_FASE_A3)

    assert erro.value.phase is _FASE_A3


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
