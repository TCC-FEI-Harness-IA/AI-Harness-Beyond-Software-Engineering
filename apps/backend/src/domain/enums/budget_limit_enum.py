from enum import StrEnum


class BudgetLimitEnum(StrEnum):
    """Enum dos limites operacionais que podem interromper uma sessão.

    Em sessões gravadas por versões anteriores, os mesmos limites disparavam degradações.
    """

    TASK_ATTEMPTS = "task_attempts"
    ADDITIONAL_PLANNING_ROUNDS = "additional_planning_rounds"
    TASKS_PER_SESSION = "tasks_per_session"
    LLM_CALLS_PER_SESSION = "llm_calls_per_session"
    SESSION_TOKEN_BUDGET = "session_token_budget"
    SESSION_TIMEOUT = "session_timeout"
