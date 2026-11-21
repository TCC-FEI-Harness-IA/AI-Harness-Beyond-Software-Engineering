from src.domain.enums.budget_limit_enum import BudgetLimitEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.domain.errors.budget_exceeded_error import BudgetExceededError
from src.domain.errors.execution_interrupted_error import ExecutionInterruptedError
from src.domain.errors.ralph_error import RalphError


def test_herda_de_ralph_error_e_e_uma_interrupcao_de_execucao() -> None:
    assert issubclass(BudgetExceededError, RalphError)
    assert issubclass(BudgetExceededError, ExecutionInterruptedError)


def test_carrega_o_limite_e_a_fase_informados() -> None:
    erro = BudgetExceededError(
        limit=BudgetLimitEnum.SESSION_TOKEN_BUDGET, phase=ThinkingPhaseEnum.C1_GLOBAL_VERIFICATION
    )

    assert erro.limit is BudgetLimitEnum.SESSION_TOKEN_BUDGET
    assert erro.phase is ThinkingPhaseEnum.C1_GLOBAL_VERIFICATION
    assert erro.task_id is None


def test_mensagem_referencia_o_limite_e_a_fase() -> None:
    erro = BudgetExceededError(
        limit=BudgetLimitEnum.SESSION_TOKEN_BUDGET, phase=ThinkingPhaseEnum.C1_GLOBAL_VERIFICATION
    )

    assert "session_token_budget" in str(erro)
    assert "C1" in str(erro)


def test_usa_o_motivo_do_guardiao_quando_informado() -> None:
    erro = BudgetExceededError(
        limit=BudgetLimitEnum.SESSION_TOKEN_BUDGET,
        phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION,
        reason="Orçamento de trabalho esgotado: 75 de 75.",
    )

    assert erro.detail == "Orçamento de trabalho esgotado: 75 de 75."
    assert "Orçamento de trabalho esgotado: 75 de 75." in str(erro)


def test_nao_afirma_que_a_reserva_tambem_acabou() -> None:
    erro = BudgetExceededError(
        limit=BudgetLimitEnum.SESSION_TOKEN_BUDGET, phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION
    )

    assert "reserva" not in str(erro)
