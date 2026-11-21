import pytest

from src.domain.enums.length_interruption_enum import LengthInterruptionEnum
from src.domain.enums.output_contract_status_enum import OutputContractStatusEnum
from src.domain.enums.output_problem_code_enum import OutputProblemCodeEnum
from src.domain.enums.output_syntax_status_enum import OutputSyntaxStatusEnum
from src.domain.enums.recovery_result_enum import RecoveryResultEnum
from src.domain.enums.recovery_strategy_enum import RecoveryStrategyEnum


def test_estados_da_sintaxe_sao_valido_invalido_e_valido_apos_reparo() -> None:
    assert [estado.value for estado in OutputSyntaxStatusEnum] == ["valid", "invalid", "valid_after_repair"]


def test_estados_do_contrato_incluem_nao_avaliado() -> None:
    assert [estado.value for estado in OutputContractStatusEnum] == ["valid", "invalid", "not_evaluated"]


def test_codigos_de_problema_cobrem_as_classes_de_falha_do_benchmark() -> None:
    valores = {codigo.value for codigo in OutputProblemCodeEnum}

    assert {"json_syntax", "schema_type", "missing_field", "criteria_ids", "decision_consistency"} <= valores
    assert {"unsupported_phase", "empty_value", "invalid_value", "duplicate_id", "task_ids", "task_limit",
            "unclassified"} <= valores


def test_interrupcao_por_comprimento_separa_confirmacao_de_indicio() -> None:
    assert [estado.value for estado in LengthInterruptionEnum] == ["confirmed", "suspected", "not_detected", "unknown"]


@pytest.mark.parametrize(
    ("finish_reason", "termina_incompleta", "esperado"),
    [
        ("length", True, LengthInterruptionEnum.CONFIRMED),
        ("length", False, LengthInterruptionEnum.CONFIRMED),
        ("stop", True, LengthInterruptionEnum.NOT_DETECTED),
        ("stop", False, LengthInterruptionEnum.NOT_DETECTED),
        ("content_filter", True, LengthInterruptionEnum.NOT_DETECTED),
        (None, True, LengthInterruptionEnum.SUSPECTED),
        (None, False, LengthInterruptionEnum.UNKNOWN),
    ],
)
def test_classificacao_da_interrupcao_so_confirma_com_o_provedor(
    finish_reason: str | None, termina_incompleta: bool, esperado: LengthInterruptionEnum
) -> None:
    assert LengthInterruptionEnum.classify(finish_reason=finish_reason, ends_incomplete=termina_incompleta) is esperado


def test_estrategias_e_resultados_de_recuperacao() -> None:
    assert [estrategia.value for estrategia in RecoveryStrategyEnum] == ["correction_prompt", "none"]
    assert [resultado.value for resultado in RecoveryResultEnum] == ["pending", "recovered", "failed"]
