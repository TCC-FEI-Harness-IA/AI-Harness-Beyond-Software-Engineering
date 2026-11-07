"""Diagnósticos estruturados produzidos pelo parser para cada saída avaliada.

Os casos de falha reproduzem as quatro classes observadas no benchmark: string cortada pelo limite
de comprimento (Q056, Química ITA), JSON inválido com término `stop` (Q042, Matemática ITA), campo com
tipo errado (Q163) e decisão incompatível com as avaliações (Q037).
"""
import json
import logging
from typing import Any

import pytest

from src.domain.entities.thinking.output_diagnostic import OutputDiagnostic
from src.domain.entities.thinking.output_problem import OutputProblem
from src.domain.entities.thinking.validation_context import ValidationContext
from src.domain.enums.budget_limit_enum import BudgetLimitEnum
from src.domain.enums.length_interruption_enum import LengthInterruptionEnum
from src.domain.enums.output_contract_status_enum import OutputContractStatusEnum
from src.domain.enums.output_problem_code_enum import OutputProblemCodeEnum
from src.domain.enums.output_syntax_status_enum import OutputSyntaxStatusEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.domain.errors.phase_parsing_error import PhaseParsingError
from src.infra.adapters.structured_response_parser_adapter import StructuredResponseParserAdapter

_A1 = ThinkingPhaseEnum.A1_GENERAL_CRITERIA
_A2 = ThinkingPhaseEnum.A2_TASK_DECOMPOSITION
_B1 = ThinkingPhaseEnum.B1_TASK_RESOLUTION
_B2 = ThinkingPhaseEnum.B2_TASK_VERIFICATION
_B4 = ThinkingPhaseEnum.B4_LEARNINGS_EXTRACTION
_CRITERIOS = {"general_acceptance_criteria": [{"id": "AC1", "description": "responder em portugues"}]}
_TAREFA = {
    "id": "T1",
    "title": "titulo",
    "description": "descricao",
    "acceptance_criteria": [{"id": "T1-AC1", "description": "criterio"}],
}
_VALIDACAO_B2 = ValidationContext(expected_criteria_ids=("T1-AC1", "T1-AC2"))


def _parser() -> StructuredResponseParserAdapter:
    return StructuredResponseParserAdapter(logger=logging.getLogger("teste.parser.diagnostico"))


def _recusa(
    raw_output: str,
    phase: ThinkingPhaseEnum = _A1,
    finish_reason: str | None = "stop",
    validation: ValidationContext | None = None,
) -> PhaseParsingError:
    with pytest.raises(PhaseParsingError) as erro:
        _parser().parse_output(raw_output=raw_output, phase=phase, finish_reason=finish_reason, validation=validation)
    assert erro.value.diagnostic is not None
    return erro.value


def _verificacao(**sobrescritas: Any) -> str:
    documento: dict[str, Any] = {
        "decision": "reproved",
        "criteria_evaluation": [
            {"criterion_id": "T1-AC1", "met": True, "justification": "ok"},
            {"criterion_id": "T1-AC2", "met": False, "justification": "falta"},
        ],
        "unmet_criteria_ids": ["T1-AC2"],
    }
    documento.update(sobrescritas)
    return json.dumps(documento)


# ── Saídas aceitas ────────────────────────────────────────────────────────────


def test_saida_valida_e_aceita_com_diagnostico_de_aceite() -> None:
    saida = _parser().parse_output(raw_output=json.dumps(_CRITERIOS), phase=_A1, finish_reason="stop")

    assert saida.parsed == _CRITERIOS
    assert saida.diagnostic == OutputDiagnostic.accepted(
        finish_reason="stop", length_interruption=LengthInterruptionEnum.NOT_DETECTED
    )


def test_parse_continua_devolvendo_apenas_a_estrutura() -> None:
    assert _parser().parse(raw_output=json.dumps(_CRITERIOS), phase=_A1) == _CRITERIOS


def test_json_valido_terminado_por_length_e_aceito_sem_esconder_o_corte() -> None:
    saida = _parser().parse_output(raw_output=json.dumps(_CRITERIOS), phase=_A1, finish_reason="length")

    assert saida.parsed == _CRITERIOS
    assert saida.diagnostic.content_accepted is True
    assert saida.diagnostic.syntax_status is OutputSyntaxStatusEnum.VALID
    assert saida.diagnostic.finish_reason == "length"
    assert saida.diagnostic.length_interruption is LengthInterruptionEnum.CONFIRMED


def test_reparo_local_de_fechamentos_fica_registrado_como_valido_apos_reparo() -> None:
    bruto = json.dumps(_CRITERIOS)[:-2]

    saida = _parser().parse_output(raw_output=bruto, phase=_A1, finish_reason="stop")

    assert saida.parsed == _CRITERIOS
    assert saida.diagnostic.syntax_status is OutputSyntaxStatusEnum.REPAIRED
    assert saida.diagnostic.repaired_closings == "]}"
    assert saida.diagnostic.contract_status is OutputContractStatusEnum.VALID
    assert saida.diagnostic.length_interruption is LengthInterruptionEnum.NOT_DETECTED


def test_reparo_sem_motivo_de_termino_registra_indicio_de_corte_e_nao_corte_confirmado() -> None:
    saida = _parser().parse_output(raw_output=json.dumps(_CRITERIOS)[:-1], phase=_A1, finish_reason=None)

    assert saida.diagnostic.syntax_status is OutputSyntaxStatusEnum.REPAIRED
    assert saida.diagnostic.finish_reason is None
    assert saida.diagnostic.length_interruption is LengthInterruptionEnum.SUSPECTED


def test_saida_completa_sem_motivo_de_termino_tem_interrupcao_desconhecida() -> None:
    saida = _parser().parse_output(raw_output=json.dumps(_CRITERIOS), phase=_A1, finish_reason=None)

    assert saida.diagnostic.length_interruption is LengthInterruptionEnum.UNKNOWN


def test_reprovacao_valida_de_b2_e_resultado_semantico_e_nao_erro_de_protocolo() -> None:
    saida = _parser().parse_output(raw_output=_verificacao(), phase=_B2, validation=_VALIDACAO_B2)

    assert saida.parsed["decision"] == "reproved"
    assert saida.diagnostic.content_accepted is True
    assert saida.diagnostic.problem is None


# ── As quatro classes de falha do benchmark ──────────────────────────────────


def test_q056_string_terminada_pelo_limite_de_comprimento() -> None:
    bruto = '{"tasks": [{"id": "T1", "title": "Calcular a entalpia de forma'

    erro = _recusa(bruto, phase=_A2, finish_reason="length")

    assert erro.diagnostic == OutputDiagnostic(
        syntax_status=OutputSyntaxStatusEnum.INVALID,
        contract_status=OutputContractStatusEnum.NOT_EVALUATED,
        finish_reason="length",
        length_interruption=LengthInterruptionEnum.CONFIRMED,
        problem=OutputProblem(code=OutputProblemCodeEnum.JSON_SYNTAX, reason=erro.reason),
    )


def test_q042_json_invalido_com_termino_stop_nao_e_truncamento() -> None:
    bruto = '{"general_acceptance_criteria": [{"id": "AC1" "description": "x"}]}'

    erro = _recusa(bruto, finish_reason="stop")

    assert erro.diagnostic.syntax_status is OutputSyntaxStatusEnum.INVALID
    assert erro.diagnostic.contract_status is OutputContractStatusEnum.NOT_EVALUATED
    assert erro.diagnostic.problem.code is OutputProblemCodeEnum.JSON_SYNTAX
    assert erro.diagnostic.finish_reason == "stop"
    assert erro.diagnostic.length_interruption is LengthInterruptionEnum.NOT_DETECTED


def test_q163_campo_com_tipo_errado_nao_e_convertido_por_suposicao() -> None:
    bruto = _verificacao(
        criteria_evaluation=[
            {"criterion_id": "T1-AC1", "met": "true", "justification": "ok"},
            {"criterion_id": "T1-AC2", "met": False, "justification": "falta"},
        ]
    )

    erro = _recusa(bruto, phase=_B2, validation=_VALIDACAO_B2)

    assert erro.diagnostic.syntax_status is OutputSyntaxStatusEnum.VALID
    assert erro.diagnostic.contract_status is OutputContractStatusEnum.INVALID
    assert erro.diagnostic.problem == OutputProblem(
        code=OutputProblemCodeEnum.SCHEMA_TYPE,
        reason="The 'met' field must be a boolean.",
        field="criteria_evaluation[].met",
        affected_ids=("T1-AC1",),
    )


def test_q037_decisao_incompativel_com_as_avaliacoes_nao_e_forcada() -> None:
    bruto = _verificacao(decision="approved")

    erro = _recusa(bruto, phase=_B2, validation=_VALIDACAO_B2)

    assert erro.diagnostic.contract_status is OutputContractStatusEnum.INVALID
    assert erro.diagnostic.problem.code is OutputProblemCodeEnum.DECISION_CONSISTENCY
    assert erro.diagnostic.problem.field == "decision"
    assert erro.diagnostic.problem.affected_ids == ("T1-AC2",)
    assert "inconsistent" in erro.diagnostic.problem.reason


def test_sintaxe_invalida_e_truncada_tem_um_unico_problema_e_o_corte_a_parte() -> None:
    erro = _recusa('{"general_acceptance_criteria": [{"id": "AC1", "descr', finish_reason="length")

    assert erro.diagnostic.problem.code is OutputProblemCodeEnum.JSON_SYNTAX
    assert erro.diagnostic.length_interruption is LengthInterruptionEnum.CONFIRMED


def test_sintaxe_invalida_sem_motivo_de_termino_registra_so_o_indicio() -> None:
    erro = _recusa('{"general_acceptance_criteria": [{"id": "AC1", "descr', finish_reason=None)

    assert erro.diagnostic.finish_reason is None
    assert erro.diagnostic.length_interruption is LengthInterruptionEnum.SUSPECTED


def test_sintaxe_invalida_fechada_sem_motivo_de_termino_tem_interrupcao_desconhecida() -> None:
    erro = _recusa('{"general_acceptance_criteria": [{"id": "AC1" "description": "x"}]}', finish_reason=None)

    assert erro.diagnostic.length_interruption is LengthInterruptionEnum.UNKNOWN


def test_saida_sem_nenhum_objeto_json_e_erro_de_sintaxe() -> None:
    erro = _recusa("Não consigo responder.", finish_reason=None)

    assert erro.diagnostic.problem.code is OutputProblemCodeEnum.JSON_SYNTAX
    assert erro.diagnostic.length_interruption is LengthInterruptionEnum.UNKNOWN


# ── Demais códigos do contrato ───────────────────────────────────────────────


def _problema(
    bruto: str, phase: ThinkingPhaseEnum = _A1, validation: ValidationContext | None = None
) -> OutputProblem:
    erro = _recusa(bruto, phase=phase, validation=validation)
    assert erro.diagnostic.syntax_status is OutputSyntaxStatusEnum.VALID
    assert erro.diagnostic.contract_status is OutputContractStatusEnum.INVALID
    assert erro.diagnostic.problem.reason == erro.reason
    return erro.diagnostic.problem


@pytest.mark.parametrize(
    ("bruto", "phase", "codigo", "campo", "ids"),
    [
        ("{}", _B1, OutputProblemCodeEnum.MISSING_FIELD, "result", ()),
        ('{"result": 3}', _B1, OutputProblemCodeEnum.SCHEMA_TYPE, "result", ()),
        ('{"result": "   "}', _B1, OutputProblemCodeEnum.EMPTY_VALUE, "result", ()),
        ("{}", _A1, OutputProblemCodeEnum.MISSING_FIELD, "general_acceptance_criteria", ()),
        ('{"general_acceptance_criteria": {}}', _A1, OutputProblemCodeEnum.SCHEMA_TYPE,
         "general_acceptance_criteria", ()),
        ('{"general_acceptance_criteria": []}', _A1, OutputProblemCodeEnum.EMPTY_VALUE,
         "general_acceptance_criteria", ()),
        ('{"general_acceptance_criteria": ["x"]}', _A1, OutputProblemCodeEnum.SCHEMA_TYPE,
         "general_acceptance_criteria[]", ()),
        ('{"general_acceptance_criteria": [{"id": "AC1"}]}', _A1, OutputProblemCodeEnum.MISSING_FIELD,
         "general_acceptance_criteria[].description", ("AC1",)),
        ('{"general_acceptance_criteria": [{"id": "AC1", "description": "a"}, {"id": "AC1", "description": "b"}]}',
         _A1, OutputProblemCodeEnum.DUPLICATE_ID, "general_acceptance_criteria[].id", ("AC1",)),
        ('{"tasks": ["x"]}', _A2, OutputProblemCodeEnum.SCHEMA_TYPE, "tasks[]", ()),
        ('{"tasks": [{"id": "T1", "title": "t", "description": "d"}]}', _A2, OutputProblemCodeEnum.MISSING_FIELD,
         "tasks[].acceptance_criteria", ("T1",)),
        ('{"tasks": [{"id": "T1", "title": "t", "description": "d", "acceptance_criteria": [{"id": 5, '
         '"description": "c"}]}]}', _A2, OutputProblemCodeEnum.SCHEMA_TYPE, "tasks[].acceptance_criteria[].id", ()),
        (json.dumps({"tasks": [_TAREFA, _TAREFA]}), _A2, OutputProblemCodeEnum.DUPLICATE_ID, "tasks[].id", ("T1",)),
        (json.dumps({"tasks": [dict(_TAREFA, acceptance_criteria=_TAREFA["acceptance_criteria"] * 2)]}), _A2,
         OutputProblemCodeEnum.DUPLICATE_ID, "tasks[].acceptance_criteria[].id", ("T1-AC1",)),
        ('{"learnings": [1]}', _B4, OutputProblemCodeEnum.SCHEMA_TYPE, "learnings[]", ()),
        ('{"learnings": "x"}', _B4, OutputProblemCodeEnum.SCHEMA_TYPE, "learnings", ()),
        ("{}", ThinkingPhaseEnum.C3_FINAL_ANSWER, OutputProblemCodeEnum.MISSING_FIELD, "final_answer", ()),
    ],
)
def test_codigo_e_campo_afetado_de_cada_violacao_do_contrato(
    bruto: str, phase: ThinkingPhaseEnum, codigo: OutputProblemCodeEnum, campo: str, ids: tuple[str, ...]
) -> None:
    problema = _problema(bruto, phase=phase)

    assert problema.code is codigo
    assert problema.field == campo
    assert problema.affected_ids == ids


@pytest.mark.parametrize(
    ("sobrescritas", "codigo", "campo", "ids"),
    [
        ({"decision": None}, OutputProblemCodeEnum.MISSING_FIELD, "decision", ()),
        ({"decision": 1}, OutputProblemCodeEnum.SCHEMA_TYPE, "decision", ()),
        ({"decision": "talvez"}, OutputProblemCodeEnum.INVALID_VALUE, "decision", ()),
        ({"criteria_evaluation": None}, OutputProblemCodeEnum.MISSING_FIELD, "criteria_evaluation", ()),
        ({"criteria_evaluation": ["x"]}, OutputProblemCodeEnum.SCHEMA_TYPE, "criteria_evaluation[]", ()),
        ({"criteria_evaluation": [{"met": True, "justification": "j"}]}, OutputProblemCodeEnum.MISSING_FIELD,
         "criteria_evaluation[].criterion_id", ()),
        ({"criteria_evaluation": [{"criterion_id": "T1-AC1", "met": True}]}, OutputProblemCodeEnum.MISSING_FIELD,
         "criteria_evaluation[].justification", ("T1-AC1",)),
        ({"criteria_evaluation": [{"criterion_id": "T1-AC1", "justification": "j"}]},
         OutputProblemCodeEnum.MISSING_FIELD, "criteria_evaluation[].met", ("T1-AC1",)),
        ({"unmet_criteria_ids": [2]}, OutputProblemCodeEnum.SCHEMA_TYPE, "unmet_criteria_ids[]", ()),
        ({"criteria_evaluation": [{"criterion_id": "T1-AC1", "met": True, "justification": "j"}]},
         OutputProblemCodeEnum.CRITERIA_IDS, "criteria_evaluation[].criterion_id", ("T1-AC2",)),
        ({"criteria_evaluation": [
            {"criterion_id": "T1-AC1", "met": True, "justification": "j"},
            {"criterion_id": "T1-AC2", "met": False, "justification": "j"},
            {"criterion_id": "T9-AC9", "met": True, "justification": "j"},
        ]}, OutputProblemCodeEnum.CRITERIA_IDS, "criteria_evaluation[].criterion_id", ("T9-AC9",)),
        ({"criteria_evaluation": [
            {"criterion_id": "T1-AC2", "met": False, "justification": "j"},
            {"criterion_id": "T1-AC2", "met": False, "justification": "j"},
        ]}, OutputProblemCodeEnum.CRITERIA_IDS, "criteria_evaluation[].criterion_id", ("T1-AC2",)),
        ({"unmet_criteria_ids": []}, OutputProblemCodeEnum.DECISION_CONSISTENCY, "decision", ()),
        ({"unmet_criteria_ids": ["T1-AC2", "T1-AC2"]}, OutputProblemCodeEnum.DUPLICATE_ID, "unmet_criteria_ids",
         ("T1-AC2",)),
        ({"unmet_criteria_ids": ["T1-AC1"]}, OutputProblemCodeEnum.DECISION_CONSISTENCY, "unmet_criteria_ids",
         ("T1-AC1", "T1-AC2")),
    ],
)
def test_codigos_da_verificacao(
    sobrescritas: dict[str, Any], codigo: OutputProblemCodeEnum, campo: str, ids: tuple[str, ...]
) -> None:
    documento = json.loads(_verificacao())
    for chave, valor in sobrescritas.items():
        if valor is None:
            documento.pop(chave)
        else:
            documento[chave] = valor

    problema = _problema(json.dumps(documento), phase=_B2, validation=_VALIDACAO_B2)

    assert problema.code is codigo
    assert problema.field == campo
    assert problema.affected_ids == ids


def test_identificador_de_tarefa_reutilizado_tem_codigo_proprio() -> None:
    problema = _problema(
        json.dumps({"tasks": [_TAREFA]}), phase=_A2, validation=ValidationContext(known_task_ids=frozenset({"T1"}))
    )

    assert problema.code is OutputProblemCodeEnum.TASK_IDS
    assert problema.field == "tasks[].id"
    assert problema.affected_ids == ("T1",)


def test_lote_acima_do_teto_preserva_o_limite_e_ganha_codigo_proprio() -> None:
    erro = _recusa(
        json.dumps({"tasks": [_TAREFA, dict(_TAREFA, id="T2")]}),
        phase=_A2,
        validation=ValidationContext(max_tasks=1),
    )

    assert erro.limit is BudgetLimitEnum.TASKS_PER_SESSION
    assert erro.diagnostic.problem.code is OutputProblemCodeEnum.TASK_LIMIT
    assert erro.diagnostic.problem.field == "tasks"


def test_fase_sem_saida_estruturada_tem_codigo_proprio_e_nao_avalia_sintaxe() -> None:
    erro = _recusa('{"result": "x"}', phase=ThinkingPhaseEnum.B3_RESULT_STORAGE)

    assert erro.diagnostic.syntax_status is None
    assert erro.diagnostic.contract_status is OutputContractStatusEnum.NOT_EVALUATED
    assert erro.diagnostic.problem.code is OutputProblemCodeEnum.UNSUPPORTED_PHASE


def test_contrato_invalido_apos_reparo_mantem_a_sintaxe_reparada() -> None:
    erro = _recusa('{"result": 3', phase=_B1, finish_reason="stop")

    assert erro.diagnostic.syntax_status is OutputSyntaxStatusEnum.REPAIRED
    assert erro.diagnostic.repaired_closings == "}"
    assert erro.diagnostic.problem.code is OutputProblemCodeEnum.SCHEMA_TYPE
