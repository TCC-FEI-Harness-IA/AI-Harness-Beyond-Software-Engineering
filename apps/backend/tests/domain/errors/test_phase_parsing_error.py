from src.domain.enums.budget_limit_enum import BudgetLimitEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.domain.errors.phase_parsing_error import PhaseParsingError
from src.domain.errors.ralph_error import RalphError


def test_herda_de_ralph_error() -> None:
    assert issubclass(PhaseParsingError, RalphError)


def test_carrega_os_atributos_informados() -> None:
    erro = PhaseParsingError(
        phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION,
        raw_output="saida sem json",
        reason="json ausente",
    )

    assert erro.phase is ThinkingPhaseEnum.B1_TASK_RESOLUTION
    assert erro.raw_output == "saida sem json"
    assert erro.reason == "json ausente"


def test_mensagem_referencia_a_fase_e_o_motivo() -> None:
    erro = PhaseParsingError(
        phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION,
        raw_output="saida sem json",
        reason="json ausente",
    )

    assert "B1" in str(erro)
    assert "json ausente" in str(erro)


def test_nao_aponta_limite_por_padrao() -> None:
    erro = PhaseParsingError(phase=ThinkingPhaseEnum.A2_TASK_DECOMPOSITION, raw_output="x", reason="r")

    assert erro.limit is None


def test_pode_apontar_o_limite_operacional_que_motivou_a_recusa() -> None:
    erro = PhaseParsingError(
        phase=ThinkingPhaseEnum.A2_TASK_DECOMPOSITION,
        raw_output="x",
        reason="lote grande demais",
        limit=BudgetLimitEnum.TASKS_PER_SESSION,
    )

    assert erro.limit is BudgetLimitEnum.TASKS_PER_SESSION
