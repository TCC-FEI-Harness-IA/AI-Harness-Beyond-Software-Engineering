"""Contrato da validação da decomposição (A.3, fluxo versão 2).

O relatório tem decisão booleana real e problemas que apontam o candidato julgado. Uma reprovação
coerente é saída aceita; incoerências, tipos errados e referências que o candidato não tem são violação
de contrato, recuperável pela correção estrutural existente. O parser não decide se o julgamento está
certo, não altera o booleano e não fabrica problemas ou ajustes.
"""
import json
import logging
from typing import Any

import pytest

from src.domain.entities.thinking.validation_context import ValidationContext
from src.domain.enums.output_contract_status_enum import OutputContractStatusEnum
from src.domain.enums.output_defect_enum import OutputDefectEnum
from src.domain.enums.output_problem_code_enum import OutputProblemCodeEnum as Code
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.domain.errors.phase_parsing_error import PhaseParsingError
from src.infra.adapters.structured_response_parser_adapter import StructuredResponseParserAdapter

_A3 = ThinkingPhaseEnum.A3_DECOMPOSITION_VALIDATION
_PLANO = ValidationContext(candidate_plan={"T1": ("T1-AC1", "T1-AC2"), "T2": ("T2-AC1",)})


def _parser() -> StructuredResponseParserAdapter:
    return StructuredResponseParserAdapter(logger=logging.getLogger("teste.parser.a3"))


def _problema(**campos: Any) -> dict[str, Any]:
    return {
        "task_id": "T2",
        "criterion_id": "T2-AC1",
        "problem": "The criterion requires an unestablished conclusion.",
        "adjustment": "Ask for an investigation that keeps the conclusion open.",
    } | campos


def _relatorio(approved: Any, *issues: dict[str, Any]) -> str:
    return json.dumps({"approved": approved, "issues": list(issues)})


def _aceito(raw: str, validation: ValidationContext | None = _PLANO) -> dict[str, Any]:
    return _parser().parse_output(raw_output=raw, phase=_A3, validation=validation).parsed


def _recusa(raw: str, validation: ValidationContext | None = _PLANO) -> PhaseParsingError:
    with pytest.raises(PhaseParsingError) as erro:
        _parser().parse_output(raw_output=raw, phase=_A3, validation=validation)
    return erro.value


# ── Saídas aceitas ──────────────────────────────────────────────────────────

def test_aprovacao_sem_problemas_e_aceita() -> None:
    assert _aceito(_relatorio(True)) == {"approved": True, "issues": []}


def test_reprovacao_coerente_e_saida_aceita_e_nao_erro_de_parsing() -> None:
    parsed = _aceito(_relatorio(False, _problema()))

    assert parsed["approved"] is False
    assert parsed["issues"] == [_problema()]


@pytest.mark.parametrize(
    "task_id, criterion_id",
    [(None, None), ("T1", None), ("T1", "T1-AC2"), ("T2", "T2-AC1")],
    ids=["plano-inteiro", "tarefa", "criterio-de-T1", "criterio-de-T2"],
)
def test_referencias_validas_de_cada_escopo(task_id: str | None, criterion_id: str | None) -> None:
    parsed = _aceito(_relatorio(False, _problema(task_id=task_id, criterion_id=criterion_id)))

    assert parsed["issues"][0]["task_id"] == task_id
    assert parsed["issues"][0]["criterion_id"] == criterion_id


def test_varios_problemas_na_mesma_reprovacao() -> None:
    parsed = _aceito(_relatorio(False, _problema(), _problema(task_id=None, criterion_id=None)))

    assert len(parsed["issues"]) == 2


def test_diagnostico_de_aceite_da_reprovacao() -> None:
    saida = _parser().parse_output(raw_output=_relatorio(False, _problema()), phase=_A3, validation=_PLANO)

    assert saida.diagnostic.contract_status is OutputContractStatusEnum.VALID


# ── Booleano estrito e coerência ────────────────────────────────────────────

@pytest.mark.parametrize("valor", ["true", "false", 1, 0, None, "approved"])
def test_booleano_como_string_numero_ou_nulo_e_recusado(valor: Any) -> None:
    erro = _recusa(_relatorio(valor))

    assert erro.defect is OutputDefectEnum.CONTRACT
    assert erro.diagnostic.problem.code is Code.SCHEMA_TYPE
    assert erro.diagnostic.problem.field == "approved"


def test_decisao_ausente_e_recusada() -> None:
    erro = _recusa(json.dumps({"issues": []}))

    assert erro.diagnostic.problem.code is Code.MISSING_FIELD
    assert erro.diagnostic.problem.field == "approved"


def test_lista_de_problemas_ausente_e_recusada() -> None:
    erro = _recusa(json.dumps({"approved": True}))

    assert erro.diagnostic.problem.code is Code.MISSING_FIELD
    assert erro.diagnostic.problem.field == "issues"


def test_aprovacao_com_problemas_e_incoerente() -> None:
    erro = _recusa(_relatorio(True, _problema()))

    assert erro.diagnostic.problem.code is Code.DECISION_CONSISTENCY
    assert erro.diagnostic.problem.field == "approved"


def test_reprovacao_sem_problemas_e_incoerente() -> None:
    erro = _recusa(_relatorio(False))

    assert erro.diagnostic.problem.code is Code.DECISION_CONSISTENCY


# ── Campos de cada problema ─────────────────────────────────────────────────

@pytest.mark.parametrize("campo", ["task_id", "criterion_id", "problem", "adjustment"])
def test_campo_ausente_no_problema_e_recusado(campo: str) -> None:
    problema = _problema()
    del problema[campo]

    erro = _recusa(_relatorio(False, problema))

    assert erro.diagnostic.problem.code is Code.MISSING_FIELD
    assert erro.diagnostic.problem.field == f"issues[].{campo}"


@pytest.mark.parametrize("campo", ["problem", "adjustment"])
@pytest.mark.parametrize("valor", ["", "   "])
def test_texto_vazio_e_recusado(campo: str, valor: str) -> None:
    erro = _recusa(_relatorio(False, _problema(**{campo: valor})))

    assert erro.diagnostic.problem.code is Code.EMPTY_VALUE
    assert erro.diagnostic.problem.field == f"issues[].{campo}"


@pytest.mark.parametrize("campo", ["problem", "adjustment"])
def test_texto_nulo_e_recusado(campo: str) -> None:
    erro = _recusa(_relatorio(False, _problema(**{campo: None})))

    assert erro.diagnostic.problem.code is Code.SCHEMA_TYPE


@pytest.mark.parametrize("campo", ["task_id", "criterion_id"])
@pytest.mark.parametrize("valor", [1, "", "  ", ["T1"]])
def test_referencia_que_nao_e_texto_nem_nula_e_recusada(campo: str, valor: Any) -> None:
    erro = _recusa(_relatorio(False, _problema(**{campo: valor})))

    assert erro.diagnostic.problem.code in {Code.SCHEMA_TYPE, Code.EMPTY_VALUE}
    assert erro.diagnostic.problem.field == f"issues[].{campo}"


def test_problema_que_nao_e_objeto_e_recusado() -> None:
    erro = _recusa(json.dumps({"approved": False, "issues": ["T2 antecipa a conclusão"]}))

    assert erro.diagnostic.problem.code is Code.SCHEMA_TYPE
    assert erro.diagnostic.problem.field == "issues[]"


# ── Referências ao candidato julgado ────────────────────────────────────────

def test_criterio_com_tarefa_nula_e_recusado() -> None:
    erro = _recusa(_relatorio(False, _problema(task_id=None, criterion_id="T1-AC1")))

    assert erro.diagnostic.problem.code is Code.TASK_REFERENCES
    assert erro.diagnostic.problem.affected_ids == ("T1-AC1",)


def test_tarefa_inexistente_no_candidato_e_recusada() -> None:
    erro = _recusa(_relatorio(False, _problema(task_id="T9", criterion_id=None)))

    assert erro.diagnostic.problem.code is Code.TASK_REFERENCES
    assert erro.diagnostic.problem.affected_ids == ("T9",)
    assert "T1, T2" in erro.reason


def test_criterio_de_outra_tarefa_e_recusado() -> None:
    erro = _recusa(_relatorio(False, _problema(task_id="T1", criterion_id="T2-AC1")))

    assert erro.diagnostic.problem.code is Code.CRITERIA_IDS
    assert erro.diagnostic.problem.affected_ids == ("T2-AC1",)
    assert "T1-AC1, T1-AC2" in erro.reason


def test_criterio_inexistente_e_recusado() -> None:
    erro = _recusa(_relatorio(False, _problema(task_id="T2", criterion_id="T2-AC7")))

    assert erro.diagnostic.problem.code is Code.CRITERIA_IDS


def test_exige_a_referencia_estrutural_do_candidato() -> None:
    with pytest.raises(ValueError):
        _parser().parse_output(raw_output=_relatorio(True), phase=_A3, validation=None)
    with pytest.raises(ValueError):
        _parser().parse_output(raw_output=_relatorio(True), phase=_A3, validation=ValidationContext())


def test_nao_aceita_um_lote_substituto_nem_fabrica_aprovacao() -> None:
    # Um plano corrigido pelo validador não faz parte do contrato: o campo extra é ignorado e nada muda.
    saida = {"approved": False, "issues": [_problema()], "tasks": [{"id": "T1"}]}

    parsed = _aceito(json.dumps(saida))

    assert parsed["approved"] is False
    assert parsed["issues"] == [_problema()]


def test_json_ilegivel_continua_sendo_erro_de_sintaxe() -> None:
    erro = _recusa('{"approved": false, "issues": [')

    assert erro.defect in {OutputDefectEnum.SYNTAX, OutputDefectEnum.CONTRACT}


# ── A.4: extração de aprendizados, com o contrato anterior da A.3 ──────────

def test_a4_mantem_o_contrato_de_aprendizados() -> None:
    saida = _parser().parse_output(
        raw_output=json.dumps({"learnings": ["Velocidade do carro: 20 m/s"]}),
        phase=ThinkingPhaseEnum.A4_PLANNING_LEARNINGS,
    )

    assert saida.parsed == {"learnings": ["Velocidade do carro: 20 m/s"]}


def test_a3_nova_nao_aceita_a_saida_historica_de_extracao() -> None:
    erro = _recusa(json.dumps({"learnings": ["Velocidade do carro: 20 m/s"]}))

    assert erro.diagnostic.problem.code is Code.MISSING_FIELD
