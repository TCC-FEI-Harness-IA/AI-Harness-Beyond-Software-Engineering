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


_CAMPOS_POSITIVOS = (
    "max_task_attempts",
    "max_additional_planning_rounds",
    "max_tasks_per_session",
    "max_llm_calls_per_session",
    "session_token_budget",
    "final_answer_token_reserve",
    "session_timeout_seconds",
)


@pytest.mark.parametrize("campo", _CAMPOS_POSITIVOS)
@pytest.mark.parametrize("valor", [0, -1])
def test_recusa_limite_nao_positivo(campo: str, valor: int) -> None:
    argumentos = dataclasses.asdict(_novo_budget()) | {campo: valor}

    with pytest.raises(ValueError) as erro:
        CostBudget(**argumentos)

    assert campo in str(erro.value)


def test_recusa_reserva_maior_ou_igual_ao_orcamento() -> None:
    argumentos = dataclasses.asdict(_novo_budget()) | {
        "session_token_budget": 1000,
        "final_answer_token_reserve": 1000,
    }

    with pytest.raises(ValueError) as erro:
        CostBudget(**argumentos)

    assert "final_answer_token_reserve" in str(erro.value)
    assert "session_token_budget" in str(erro.value)


def test_aceita_reserva_menor_que_o_orcamento() -> None:
    budget = CostBudget(**(dataclasses.asdict(_novo_budget()) | {
        "session_token_budget": 1000,
        "final_answer_token_reserve": 999,
    }))

    assert budget.final_answer_token_reserve == 999
