from dataclasses import dataclass

from src.domain.enums.recovery_result_enum import RecoveryResultEnum
from src.domain.enums.recovery_strategy_enum import RecoveryStrategyEnum


@dataclass(frozen=True)
class OutputRecovery:
    """Recuperação aplicada a uma saída recusada pelo parser.

    Fica na invocação que produziu a saída recusada. As chamadas feitas para recuperá-la apontam a
    invocação original da cadeia pelo campo `recovers_invocation_id` de cada `LLMInvocation`.

    Attributes:
        strategy: Estratégia aplicada à saída recusada.
        result: Resultado da recuperação.
        resolved_by_invocation_id: Invocação cuja saída foi aceita, quando a recuperação deu certo.
    """

    strategy: RecoveryStrategyEnum
    result: RecoveryResultEnum
    resolved_by_invocation_id: str | None = None

    def __post_init__(self) -> None:
        """Recusa combinações contraditórias de estratégia, resultado e invocação resolvedora.

        Raises:
            ValueError: Quando a recuperação se contradiz.
        """
        if (self.result is RecoveryResultEnum.RECOVERED) != (self.resolved_by_invocation_id is not None):
            raise ValueError("Só uma recuperação bem-sucedida aponta a invocação que a resolveu.")
        if self.strategy is RecoveryStrategyEnum.NONE and self.result is not RecoveryResultEnum.FAILED:
            raise ValueError("Uma recusa sem estratégia de recuperação só pode terminar em falha.")

    @property
    def is_final(self) -> bool:
        """Informa se a recuperação já tem resultado definitivo.

        Returns:
            bool: `True` quando a recuperação deu certo ou falhou.
        """
        return self.result is not RecoveryResultEnum.PENDING
