from src.domain.enums.budget_limit_enum import BudgetLimitEnum
from src.domain.errors.ralph_error import RalphError


class BudgetExceededError(RalphError):
    """Levantado quando o orçamento é esgotado inclusive a reserva de C.3.

    Attributes:
        limit: Limite de orçamento responsável pelo esgotamento.
    """

    def __init__(self, limit: BudgetLimitEnum) -> None:
        """Inicializa o erro.

        Args:
            limit: Limite de orçamento responsável pelo esgotamento.
        """
        self.limit = limit
        super().__init__(f"Orçamento esgotado, inclusive a reserva. Limite: '{limit.value}'.")
