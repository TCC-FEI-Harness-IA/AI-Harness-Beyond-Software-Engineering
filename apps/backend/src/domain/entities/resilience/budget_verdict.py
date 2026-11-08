from dataclasses import dataclass

from src.domain.enums.budget_limit_enum import BudgetLimitEnum


@dataclass(frozen=True)
class BudgetVerdict:
    """Representa a resposta do `ICostGuard` a um pedido de autorização.

    Attributes:
        authorized: Indica se a operação está autorizada a prosseguir.
        limit: Limite responsável pela negação, quando não autorizado.
        reason: Motivo legível da negação, quando não autorizado.
    """

    authorized: bool
    limit: BudgetLimitEnum | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        """Valida a invariante entre autorização, limite e motivo.

        Raises:
            ValueError: Quando um veredito autorizado carrega `limit` ou `reason`,
                ou quando um veredito negado não identifica o `limit` responsável.
        """
        if self.authorized:
            if self.limit is not None:
                raise ValueError("Um veredito autorizado não pode carregar 'limit'.")
            if self.reason is not None:
                raise ValueError("Um veredito autorizado não pode carregar 'reason'.")
        elif self.limit is None:
            raise ValueError("Um veredito negado deve identificar o 'limit' responsável.")
