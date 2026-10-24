from src.domain.enums.budget_limit_enum import BudgetLimitEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.domain.errors.execution_interrupted_error import ExecutionInterruptedError
from src.domain.errors.ralph_error import RalphError


def test_herda_de_ralph_error() -> None:
    assert issubclass(ExecutionInterruptedError, RalphError)


def test_carrega_limite_fase_detalhe_e_tarefa() -> None:
    erro = ExecutionInterruptedError(
        limit=BudgetLimitEnum.TASK_ATTEMPTS,
        phase=ThinkingPhaseEnum.B2_TASK_VERIFICATION,
        detail="A tarefa esgotou as tentativas.",
        task_id="T2",
    )

    assert erro.limit is BudgetLimitEnum.TASK_ATTEMPTS
    assert erro.phase is ThinkingPhaseEnum.B2_TASK_VERIFICATION
    assert erro.detail == "A tarefa esgotou as tentativas."
    assert erro.task_id == "T2"


def test_a_tarefa_e_opcional() -> None:
    erro = ExecutionInterruptedError(
        limit=BudgetLimitEnum.ADDITIONAL_PLANNING_ROUNDS,
        phase=ThinkingPhaseEnum.C2_ADDITIONAL_PLANNING,
        detail="Sem rodadas.",
    )

    assert erro.task_id is None


def test_mensagem_cita_limite_fase_tarefa_e_detalhe() -> None:
    erro = ExecutionInterruptedError(
        limit=BudgetLimitEnum.TASK_ATTEMPTS,
        phase=ThinkingPhaseEnum.B2_TASK_VERIFICATION,
        detail="A tarefa esgotou as tentativas.",
        task_id="T2",
    )

    mensagem = str(erro)
    assert "task_attempts" in mensagem
    assert "B2" in mensagem
    assert "T2" in mensagem
    assert "A tarefa esgotou as tentativas." in mensagem


def test_mensagem_sem_tarefa_nao_menciona_tarefa() -> None:
    erro = ExecutionInterruptedError(
        limit=BudgetLimitEnum.SESSION_TIMEOUT,
        phase=ThinkingPhaseEnum.C1_GLOBAL_VERIFICATION,
        detail="Tempo esgotado.",
    )

    assert "tarefa" not in str(erro)
