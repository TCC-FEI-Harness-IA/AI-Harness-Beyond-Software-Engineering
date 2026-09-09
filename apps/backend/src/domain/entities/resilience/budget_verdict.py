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
