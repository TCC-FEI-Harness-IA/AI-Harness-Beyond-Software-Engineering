import dataclasses

import pytest

from src.domain.entities.resilience.cost_budget import CostBudget


def _novo_budget() -> CostBudget:
    return CostBudget(
        max_task_attempts=3,
        max_additional_planning_rounds=2,
        max_tasks_per_session=12,
        max_llm_calls_per_session=60,
        session_token_budget=120000,
        final_answer_token_reserve=4000,
        session_timeout_seconds=600,
    )


def test_carrega_todos_os_limites() -> None:
    budget = _novo_budget()

    assert budget.max_task_attempts == 3
    assert budget.max_additional_planning_rounds == 2
    assert budget.max_tasks_per_session == 12
    assert budget.max_llm_calls_per_session == 60
    assert budget.session_token_budget == 120000
    assert budget.final_answer_token_reserve == 4000
    assert budget.session_timeout_seconds == 600


def test_e_imutavel() -> None:
    budget = _novo_budget()

    with pytest.raises(dataclasses.FrozenInstanceError):
        budget.max_task_attempts = 5
