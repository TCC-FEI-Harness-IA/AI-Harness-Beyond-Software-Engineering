from src.domain.enums.budget_limit_enum import BudgetLimitEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.domain.errors.ralph_error import RalphError


class ExecutionInterruptedError(RalphError):
    """Levantado quando um limite operacional impede o fluxo de seguir sem violar o método.

    O paper não define limites de recursos. Quando um deles é atingido, o harness encerra a
    sessão sem conclusão, em vez de promover material não aprovado ou sintetizar sem aprovação
    global. Este é um tratamento operacional adicional, não uma regra do paper.

    Attributes:
        limit: Limite responsável pela interrupção.
        phase: Fase de thinking em que o fluxo foi interrompido.
        detail: Descrição legível do que impediu a continuação.
        task_id: Tarefa afetada, quando a interrupção é de uma tarefa.
    """

    def __init__(
        self,
        limit: BudgetLimitEnum,
        phase: ThinkingPhaseEnum,
        detail: str,
        task_id: str | None = None,
    ) -> None:
        """Inicializa o erro.

        Args:
            limit: Limite responsável pela interrupção.
            phase: Fase de thinking em que o fluxo foi interrompido.
            detail: Descrição legível do que impediu a continuação.
            task_id: Tarefa afetada, quando a interrupção é de uma tarefa.
        """
        self.limit = limit
        self.phase = phase
        self.detail = detail
        self.task_id = task_id
        task = f", tarefa '{task_id}'" if task_id is not None else ""
        super().__init__(
            f"Execução interrompida pelo limite '{limit.value}' na fase '{phase.value}'{task}: {detail}"
        )
