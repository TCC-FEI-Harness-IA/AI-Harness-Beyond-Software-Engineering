import dataclasses
from datetime import UTC, datetime

import pytest

from src.domain.entities.session.session_degradation import SessionDegradation
from src.domain.enums.budget_limit_enum import BudgetLimitEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum

_OCORRIDO_EM = datetime.now(tz=UTC)


def _nova_degradacao() -> SessionDegradation:
    return SessionDegradation(
        limit=BudgetLimitEnum.TASK_ATTEMPTS,
        phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION,
        task_id="t1",
        description="tentativas esgotadas",
        occurred_at=_OCORRIDO_EM,
    )


def test_carrega_todos_os_campos() -> None:
    degradacao = _nova_degradacao()

    assert degradacao.limit is BudgetLimitEnum.TASK_ATTEMPTS
    assert degradacao.phase is ThinkingPhaseEnum.B1_TASK_RESOLUTION
    assert degradacao.task_id == "t1"
    assert degradacao.description == "tentativas esgotadas"
    assert degradacao.occurred_at == _OCORRIDO_EM


def test_e_imutavel() -> None:
    degradacao = _nova_degradacao()

    with pytest.raises(dataclasses.FrozenInstanceError):
        degradacao.description = "outra descricao"
