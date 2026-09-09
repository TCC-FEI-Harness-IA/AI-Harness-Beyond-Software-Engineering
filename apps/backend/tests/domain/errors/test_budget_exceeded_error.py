from src.domain.enums.budget_limit_enum import BudgetLimitEnum
from src.domain.errors.budget_exceeded_error import BudgetExceededError
from src.domain.errors.ralph_error import RalphError


def test_herda_de_ralph_error() -> None:
    assert issubclass(BudgetExceededError, RalphError)


def test_carrega_o_limite_informado() -> None:
    erro = BudgetExceededError(limit=BudgetLimitEnum.SESSION_TOKEN_BUDGET)

    assert erro.limit is BudgetLimitEnum.SESSION_TOKEN_BUDGET


def test_mensagem_referencia_o_limite() -> None:
    erro = BudgetExceededError(limit=BudgetLimitEnum.SESSION_TOKEN_BUDGET)

    assert "session_token_budget" in str(erro)
