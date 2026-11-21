"""Configuração compartilhada da suíte de testes."""
import base64
from collections.abc import Callable

import pytest

from src.domain.entities.resilience.cost_budget import CostBudget

_LIMITES_PEQUENOS: dict[str, int] = {
    "max_task_attempts": 2,
    "max_planning_attempts": 2,
    "max_additional_planning_rounds": 1,
    "max_tasks_per_session": 5,
    "max_llm_calls_per_session": 3,
    "session_token_budget": 1000,
    "final_answer_token_reserve": 200,
    "session_timeout_seconds": 10,
}


@pytest.fixture
def budget_factory() -> Callable[..., CostBudget]:
    """Fábrica de `CostBudget` com limites pequenos e explícitos.

    Returns:
        Callable[..., CostBudget]: Função que monta um budget, aceitando sobrescritas
        de qualquer limite pelo nome do campo.
    """

    def _factory(**overrides: int) -> CostBudget:
        return CostBudget(**(_LIMITES_PEQUENOS | overrides))

    return _factory


@pytest.fixture(autouse=True)
def segredos_de_teste(monkeypatch: pytest.MonkeyPatch) -> None:
    """Segredos de infraestrutura fictícios, para `create_app()` subir sem os valores reais.

    Nunca há chave OpenRouter do servidor: a única credencial LLM é a do usuário, no cookie cifrado.
    """
    monkeypatch.setenv("AUTH_INTERNAL_TOKEN", "segredo-interno-de-teste-com-mais-de-32-caracteres")
    monkeypatch.setenv("LLM_CREDENTIAL_ENCRYPTION_KEY", base64.urlsafe_b64encode(b"k" * 32).decode())
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
