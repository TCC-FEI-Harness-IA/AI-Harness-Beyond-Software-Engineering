from dataclasses import dataclass
from datetime import datetime

from src.domain.enums.budget_limit_enum import BudgetLimitEnum
from src.domain.enums.session_failure_reason_enum import SessionFailureReasonEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum


@dataclass(frozen=True)
class SessionFailure:
    """Motivo estruturado pelo qual uma sessão terminou sem conclusão.

    Diferencia o limite de recursos que interrompeu o fluxo de um erro técnico, e guarda o
    que ainda estava pendente no momento, para que a interrupção seja diagnosticável.

    Attributes:
        reason: Classe da falha: limite de recursos ou erro técnico.
        phase: Fase de thinking em que o fluxo terminou.
        description: Descrição legível da causa, com o consumo conhecido quando disponível.
        occurred_at: Data e hora da falha em UTC.
        limit: Limite responsável, exigido quando o motivo é limite de recursos.
        task_id: Tarefa em andamento, quando a falha é de uma tarefa.
        pending_criteria_ids: Critérios gerais que a última verificação global deu como pendentes.
    """

    reason: SessionFailureReasonEnum
    phase: ThinkingPhaseEnum
    description: str
    occurred_at: datetime
    limit: BudgetLimitEnum | None = None
    task_id: str | None = None
    pending_criteria_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Valida a invariante entre motivo e limite.

        Raises:
            ValueError: Quando uma falha por limite de recursos não identifica o limite,
                ou quando um erro técnico aponta um limite.
        """
        is_resource_limit = self.reason is SessionFailureReasonEnum.RESOURCE_LIMIT
        if is_resource_limit and self.limit is None:
            raise ValueError("Uma falha 'resource_limit' deve identificar o 'limit' responsável.")
        if not is_resource_limit and self.limit is not None:
            raise ValueError("Uma falha 'technical_error' não pode apontar um 'limit'.")
