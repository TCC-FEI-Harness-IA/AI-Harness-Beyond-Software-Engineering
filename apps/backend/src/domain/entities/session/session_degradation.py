from dataclasses import dataclass
from datetime import datetime

from src.domain.enums.budget_limit_enum import BudgetLimitEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum


@dataclass(frozen=True)
class SessionDegradation:
    """Registra uma degradação ocorrida durante a sessão.

    Legado: versões anteriores do fluxo aceitavam o resultado da última tentativa ou sintetizavam sem
    aprovação global ao atingir um limite. O fluxo atual não gera degradações; a entidade existe para
    que as sessões já gravadas continuem legíveis, sem reclassificação.

    Attributes:
        limit: Limite de orçamento que disparou a degradação.
        phase: Fase de thinking em que a degradação ocorreu.
        task_id: Tarefa associada, quando houver.
        description: Descrição legível da degradação.
        occurred_at: Data e hora de ocorrência em UTC.
    """

    limit: BudgetLimitEnum
    phase: ThinkingPhaseEnum
    task_id: str | None
    description: str
    occurred_at: datetime
