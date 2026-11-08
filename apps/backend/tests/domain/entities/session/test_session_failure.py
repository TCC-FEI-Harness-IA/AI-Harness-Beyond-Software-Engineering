import dataclasses
from datetime import UTC, datetime

import pytest

from src.domain.entities.session.session_failure import SessionFailure
from src.domain.enums.budget_limit_enum import BudgetLimitEnum
from src.domain.enums.session_failure_reason_enum import SessionFailureReasonEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum

_QUANDO = datetime(2026, 8, 31, 12, 0, tzinfo=UTC)


def _falha_de_recurso(**overrides: object) -> SessionFailure:
    campos: dict[str, object] = {
        "reason": SessionFailureReasonEnum.RESOURCE_LIMIT,
        "phase": ThinkingPhaseEnum.B2_TASK_VERIFICATION,
        "description": "tentativas esgotadas",
        "occurred_at": _QUANDO,
        "limit": BudgetLimitEnum.TASK_ATTEMPTS,
        "task_id": "T1",
        "pending_criteria_ids": ("AC2",),
    }
    return SessionFailure(**(campos | overrides))


def test_carrega_os_campos_informados() -> None:
    falha = _falha_de_recurso()

    assert falha.reason is SessionFailureReasonEnum.RESOURCE_LIMIT
    assert falha.phase is ThinkingPhaseEnum.B2_TASK_VERIFICATION
    assert falha.description == "tentativas esgotadas"
    assert falha.occurred_at == _QUANDO
    assert falha.limit is BudgetLimitEnum.TASK_ATTEMPTS
    assert falha.task_id == "T1"
    assert falha.pending_criteria_ids == ("AC2",)


def test_erro_tecnico_nao_tem_limite_nem_tarefa_nem_pendencias_por_padrao() -> None:
    falha = SessionFailure(
        reason=SessionFailureReasonEnum.TECHNICAL_ERROR,
        phase=ThinkingPhaseEnum.A1_GENERAL_CRITERIA,
        description="provedor fora do ar",
        occurred_at=_QUANDO,
    )

    assert falha.limit is None
    assert falha.task_id is None
    assert falha.pending_criteria_ids == ()


def test_limite_de_recurso_exige_o_limite() -> None:
    with pytest.raises(ValueError, match="resource_limit"):
        _falha_de_recurso(limit=None)


def test_erro_tecnico_nao_pode_apontar_limite() -> None:
    with pytest.raises(ValueError, match="technical_error"):
        _falha_de_recurso(reason=SessionFailureReasonEnum.TECHNICAL_ERROR)


def test_e_imutavel() -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        _falha_de_recurso().description = "outra"
