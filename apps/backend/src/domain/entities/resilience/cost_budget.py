from dataclasses import dataclass, fields

_MINIMUM_LIMIT_VALUE = 0


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

    def __post_init__(self) -> None:
        """Valida os limites congelados no início da sessão.

        Raises:
            ValueError: Quando algum limite não é positivo ou quando a reserva da
                resposta final não é menor que o orçamento de tokens da sessão.
        """
        for field in fields(self):
            value = getattr(self, field.name)
            if value <= _MINIMUM_LIMIT_VALUE:
                raise ValueError(f"O limite '{field.name}' deve ser maior que zero. Valor: '{value}'.")

        if self.final_answer_token_reserve >= self.session_token_budget:
            raise ValueError(
                "O limite 'final_answer_token_reserve' deve ser menor que 'session_token_budget'. "
                f"Valores: '{self.final_answer_token_reserve}' e '{self.session_token_budget}'."
            )
