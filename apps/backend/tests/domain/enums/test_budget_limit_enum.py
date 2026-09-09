from src.domain.enums.budget_limit_enum import BudgetLimitEnum

_ESPERADOS = {
    "task_attempts",
    "additional_planning_rounds",
    "tasks_per_session",
    "llm_calls_per_session",
    "session_token_budget",
    "session_timeout",
}


def test_declara_exatamente_os_limites_suportados() -> None:
    assert {member.value for member in BudgetLimitEnum} == _ESPERADOS


def test_valores_de_cada_membro() -> None:
    assert BudgetLimitEnum.TASK_ATTEMPTS == "task_attempts"
    assert BudgetLimitEnum.ADDITIONAL_PLANNING_ROUNDS == "additional_planning_rounds"
    assert BudgetLimitEnum.TASKS_PER_SESSION == "tasks_per_session"
    assert BudgetLimitEnum.LLM_CALLS_PER_SESSION == "llm_calls_per_session"
    assert BudgetLimitEnum.SESSION_TOKEN_BUDGET == "session_token_budget"
    assert BudgetLimitEnum.SESSION_TIMEOUT == "session_timeout"


def test_e_uma_str_enum() -> None:
    assert isinstance(BudgetLimitEnum.TASK_ATTEMPTS, str)
