from dataclasses import dataclass


@dataclass(frozen=True)
class CostBudget:
    """Snapshot imutável dos limites de custo configurados para uma sessão.

    Attributes:
        max_task_attempts: Tentativas máximas de B.1/B.2 para a mesma tarefa.
        max_additional_planning_rounds: Execuções máximas de C.2 por sessão.
        max_tasks_per_session: Total máximo de tarefas por sessão.
        max_llm_calls_per_session: Teto absoluto de chamadas ao modelo.
        session_token_budget: Teto de tokens (entrada + saída) da sessão inteira.
        final_answer_token_reserve: Reserva de tokens nunca consumida pelo loop.
        session_timeout_seconds: Tempo máximo de parede da sessão.
    """

    max_task_attempts: int
    max_additional_planning_rounds: int
    max_tasks_per_session: int
    max_llm_calls_per_session: int
    session_token_budget: int
    final_answer_token_reserve: int
    session_timeout_seconds: int
