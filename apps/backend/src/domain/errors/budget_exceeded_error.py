from src.domain.enums.budget_limit_enum import BudgetLimitEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.domain.errors.execution_interrupted_error import ExecutionInterruptedError


class BudgetExceededError(ExecutionInterruptedError):
    """Levantado quando o guardião de custo nega uma chamada ao modelo.

    A negação vale para a fase que pediu a chamada, que pode ver um teto diferente de
    outra fase (a reserva de C.3, por exemplo, só é visível para C.3). Por isso a mensagem
    reproduz o motivo do guardião, em vez de presumir qual orçamento acabou.
    """

    def __init__(self, limit: BudgetLimitEnum, phase: ThinkingPhaseEnum, reason: str | None = None) -> None:
        """Inicializa o erro.

        Args:
            limit: Limite de orçamento responsável pela negação.
            phase: Fase de thinking cuja chamada foi negada.
            reason: Motivo legível informado pelo guardião, quando há.
        """
        super().__init__(
            limit=limit,
            phase=phase,
            detail=reason or f"Orçamento esgotado pelo limite '{limit.value}'.",
        )
