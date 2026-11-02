import dataclasses

import pytest

from src.domain.entities.thinking.output_diagnostic import OutputDiagnostic
from src.domain.entities.thinking.output_problem import OutputProblem
from src.domain.entities.thinking.output_recovery import OutputRecovery
from src.domain.entities.thinking.parsed_output import ParsedOutput
from src.domain.enums.length_interruption_enum import LengthInterruptionEnum
from src.domain.enums.output_contract_status_enum import OutputContractStatusEnum
from src.domain.enums.output_problem_code_enum import OutputProblemCodeEnum
from src.domain.enums.output_syntax_status_enum import OutputSyntaxStatusEnum
from src.domain.enums.recovery_result_enum import RecoveryResultEnum
from src.domain.enums.recovery_strategy_enum import RecoveryStrategyEnum

_SINTAXE = OutputProblem(code=OutputProblemCodeEnum.JSON_SYNTAX, reason="Nenhum objeto JSON válido.")
_TIPO = OutputProblem(
    code=OutputProblemCodeEnum.SCHEMA_TYPE, reason="O campo 'met' deve ser booleano.", field="criteria_evaluation.met",
    affected_ids=("T1-AC1",),
)


def _aceita_stop() -> OutputDiagnostic:
    return OutputDiagnostic.accepted(finish_reason="stop", length_interruption=LengthInterruptionEnum.NOT_DETECTED)


# ── OutputProblem ─────────────────────────────────────────────────────────────


def test_problema_guarda_codigo_motivo_legivel_campo_e_criterios_afetados() -> None:
    assert _TIPO.code is OutputProblemCodeEnum.SCHEMA_TYPE
    assert _TIPO.reason == "O campo 'met' deve ser booleano."
    assert _TIPO.field == "criteria_evaluation.met"
    assert _TIPO.affected_ids == ("T1-AC1",)


def test_problema_sem_campo_nem_criterio_usa_ausencia() -> None:
    assert _SINTAXE.field is None
    assert _SINTAXE.affected_ids == ()


def test_problema_exige_motivo_legivel() -> None:
    with pytest.raises(ValueError, match="motivo"):
        OutputProblem(code=OutputProblemCodeEnum.JSON_SYNTAX, reason="  ")


def test_problema_e_imutavel() -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        _SINTAXE.reason = "outro"  # type: ignore[misc]


# ── OutputDiagnostic ──────────────────────────────────────────────────────────


def test_saida_aceita_tem_sintaxe_e_contrato_validos_sem_problema() -> None:
    diagnostico = _aceita_stop()

    assert diagnostico.syntax_status is OutputSyntaxStatusEnum.VALID
    assert diagnostico.contract_status is OutputContractStatusEnum.VALID
    assert diagnostico.problem is None
    assert diagnostico.repaired_closings is None
    assert diagnostico.finish_reason == "stop"
    assert diagnostico.content_accepted is True


def test_saida_aceita_apos_reparo_registra_os_fechamentos_acrescentados() -> None:
    diagnostico = OutputDiagnostic.accepted(
        finish_reason=None, length_interruption=LengthInterruptionEnum.SUSPECTED, repaired_closings="]}"
    )

    assert diagnostico.syntax_status is OutputSyntaxStatusEnum.REPAIRED
    assert diagnostico.repaired_closings == "]}"
    assert diagnostico.content_accepted is True


def test_json_valido_cortado_por_length_e_aceito_sem_esconder_o_corte() -> None:
    diagnostico = OutputDiagnostic.accepted(
        finish_reason="length", length_interruption=LengthInterruptionEnum.CONFIRMED
    )

    assert diagnostico.content_accepted is True
    assert diagnostico.length_interruption is LengthInterruptionEnum.CONFIRMED
    assert diagnostico.finish_reason == "length"


def test_sintaxe_invalida_deixa_o_contrato_nao_avaliado_e_a_saida_recusada() -> None:
    diagnostico = OutputDiagnostic(
        syntax_status=OutputSyntaxStatusEnum.INVALID,
        contract_status=OutputContractStatusEnum.NOT_EVALUATED,
        finish_reason="length",
        length_interruption=LengthInterruptionEnum.CONFIRMED,
        problem=_SINTAXE,
    )

    assert diagnostico.content_accepted is False


def test_contrato_invalido_tem_sintaxe_valida_e_problema() -> None:
    diagnostico = OutputDiagnostic(
        syntax_status=OutputSyntaxStatusEnum.VALID,
        contract_status=OutputContractStatusEnum.INVALID,
        finish_reason="stop",
        length_interruption=LengthInterruptionEnum.NOT_DETECTED,
        problem=_TIPO,
    )

    assert diagnostico.content_accepted is False


def test_recusa_nao_classificada_preserva_o_motivo_e_nao_inventa_estado_de_sintaxe() -> None:
    diagnostico = OutputDiagnostic.unclassified(reason="falha do parser", finish_reason=None)

    assert diagnostico.syntax_status is None
    assert diagnostico.contract_status is OutputContractStatusEnum.NOT_EVALUATED
    assert diagnostico.problem == OutputProblem(code=OutputProblemCodeEnum.UNCLASSIFIED, reason="falha do parser")
    assert diagnostico.length_interruption is LengthInterruptionEnum.UNKNOWN
    assert diagnostico.content_accepted is False


@pytest.mark.parametrize(
    ("campos", "trecho"),
    [
        (
            {"syntax_status": OutputSyntaxStatusEnum.INVALID, "contract_status": OutputContractStatusEnum.INVALID,
             "problem": _SINTAXE},
            "não avaliado",
        ),
        (
            {"syntax_status": None, "contract_status": OutputContractStatusEnum.VALID, "problem": None},
            "não avaliado",
        ),
        (
            {"syntax_status": OutputSyntaxStatusEnum.VALID, "contract_status": OutputContractStatusEnum.VALID,
             "problem": _TIPO},
            "problema",
        ),
        (
            {"syntax_status": OutputSyntaxStatusEnum.VALID, "contract_status": OutputContractStatusEnum.INVALID,
             "problem": None},
            "problema",
        ),
        (
            {"syntax_status": OutputSyntaxStatusEnum.VALID, "contract_status": OutputContractStatusEnum.NOT_EVALUATED,
             "problem": _TIPO},
            "não avaliado",
        ),
        (
            {"syntax_status": OutputSyntaxStatusEnum.INVALID,
             "contract_status": OutputContractStatusEnum.NOT_EVALUATED, "problem": _TIPO},
            "json_syntax",
        ),
        (
            {"syntax_status": OutputSyntaxStatusEnum.VALID, "contract_status": OutputContractStatusEnum.INVALID,
             "problem": _SINTAXE},
            "json_syntax",
        ),
        (
            {"syntax_status": OutputSyntaxStatusEnum.REPAIRED, "contract_status": OutputContractStatusEnum.VALID,
             "problem": None},
            "fechamentos",
        ),
        (
            {"syntax_status": OutputSyntaxStatusEnum.VALID, "contract_status": OutputContractStatusEnum.VALID,
             "problem": None, "repaired_closings": "}"},
            "fechamentos",
        ),
    ],
)
def test_diagnostico_incoerente_e_recusado(campos: dict, trecho: str) -> None:
    with pytest.raises(ValueError, match=trecho):
        OutputDiagnostic(
            finish_reason="stop",
            length_interruption=LengthInterruptionEnum.NOT_DETECTED,
            **campos,
        )


# ── ParsedOutput ──────────────────────────────────────────────────────────────


def test_saida_parseada_carrega_a_estrutura_e_o_diagnostico_de_aceite() -> None:
    diagnostico = _aceita_stop()

    saida = ParsedOutput(parsed={"result": "x"}, diagnostic=diagnostico)

    assert saida.parsed == {"result": "x"}
    assert saida.diagnostic is diagnostico


def test_saida_parseada_nao_aceita_diagnostico_de_recusa() -> None:
    with pytest.raises(ValueError, match="aceit"):
        ParsedOutput(parsed={}, diagnostic=OutputDiagnostic.unclassified(reason="x", finish_reason=None))


# ── OutputRecovery ────────────────────────────────────────────────────────────


def test_recuperacao_pendente_ainda_nao_e_final() -> None:
    recuperacao = OutputRecovery(strategy=RecoveryStrategyEnum.CORRECTION_PROMPT, result=RecoveryResultEnum.PENDING)

    assert recuperacao.resolved_by_invocation_id is None
    assert recuperacao.is_final is False


def test_recuperacao_bem_sucedida_aponta_a_invocacao_que_resolveu() -> None:
    recuperacao = OutputRecovery(
        strategy=RecoveryStrategyEnum.CORRECTION_PROMPT,
        result=RecoveryResultEnum.RECOVERED,
        resolved_by_invocation_id="inv-3",
    )

    assert recuperacao.is_final is True
    assert recuperacao.resolved_by_invocation_id == "inv-3"


def test_falha_terminal_sem_estrategia_e_final() -> None:
    recuperacao = OutputRecovery(strategy=RecoveryStrategyEnum.NONE, result=RecoveryResultEnum.FAILED)

    assert recuperacao.is_final is True


@pytest.mark.parametrize(
    ("estrategia", "resultado", "resolvida_por", "trecho"),
    [
        (RecoveryStrategyEnum.CORRECTION_PROMPT, RecoveryResultEnum.RECOVERED, None, "resolveu"),
        (RecoveryStrategyEnum.CORRECTION_PROMPT, RecoveryResultEnum.FAILED, "inv-2", "resolveu"),
        (RecoveryStrategyEnum.CORRECTION_PROMPT, RecoveryResultEnum.PENDING, "inv-2", "resolveu"),
        (RecoveryStrategyEnum.NONE, RecoveryResultEnum.PENDING, None, "sem estratégia"),
        (RecoveryStrategyEnum.NONE, RecoveryResultEnum.RECOVERED, "inv-2", "sem estratégia"),
    ],
)
def test_recuperacao_incoerente_e_recusada(
    estrategia: RecoveryStrategyEnum, resultado: RecoveryResultEnum, resolvida_por: str | None, trecho: str
) -> None:
    with pytest.raises(ValueError, match=trecho):
        OutputRecovery(strategy=estrategia, result=resultado, resolved_by_invocation_id=resolvida_por)
