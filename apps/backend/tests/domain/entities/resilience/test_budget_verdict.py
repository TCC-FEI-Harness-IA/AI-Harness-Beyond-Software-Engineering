import dataclasses

import pytest

from src.domain.entities.resilience.budget_verdict import BudgetVerdict
from src.domain.enums.budget_limit_enum import BudgetLimitEnum


def test_defaults_de_um_veredito_autorizado() -> None:
    veredito = BudgetVerdict(authorized=True)

    assert veredito.authorized is True
    assert veredito.limit is None
    assert veredito.reason is None


def test_carrega_o_limite_e_o_motivo_quando_negado() -> None:
    veredito = BudgetVerdict(
        authorized=False,
        limit=BudgetLimitEnum.SESSION_TOKEN_BUDGET,
        reason="orçamento esgotado",
    )

    assert veredito.authorized is False
    assert veredito.limit is BudgetLimitEnum.SESSION_TOKEN_BUDGET
    assert veredito.reason == "orçamento esgotado"


def test_e_imutavel() -> None:
    veredito = BudgetVerdict(authorized=True)

    with pytest.raises(dataclasses.FrozenInstanceError):
        veredito.authorized = False


def test_autorizado_com_limite_e_invalido() -> None:
    with pytest.raises(ValueError) as erro:
        BudgetVerdict(authorized=True, limit=BudgetLimitEnum.SESSION_TIMEOUT)

    assert "limit" in str(erro.value)


def test_autorizado_com_motivo_e_invalido() -> None:
    with pytest.raises(ValueError) as erro:
        BudgetVerdict(authorized=True, reason="qualquer motivo")

    assert "reason" in str(erro.value)


def test_negado_sem_limite_e_invalido() -> None:
    with pytest.raises(ValueError) as erro:
        BudgetVerdict(authorized=False)

    assert "limit" in str(erro.value)


def test_negado_sem_motivo_continua_valido_desde_que_tenha_limite() -> None:
    veredito = BudgetVerdict(authorized=False, limit=BudgetLimitEnum.LLM_CALLS_PER_SESSION)

    assert veredito.limit is BudgetLimitEnum.LLM_CALLS_PER_SESSION
    assert veredito.reason is None
