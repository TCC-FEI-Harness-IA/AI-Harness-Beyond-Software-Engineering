import dataclasses
from datetime import UTC, datetime

import pytest

from src.domain.entities.session.llm_invocation import LLMInvocation
from src.domain.enums.invocation_outcome_enum import InvocationOutcomeEnum
from src.domain.enums.model_provider_enum import ModelProviderEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum

_INICIO = datetime(2026, 8, 31, 12, 0, tzinfo=UTC)


def _iniciada() -> LLMInvocation:
    return LLMInvocation(
        id="inv-1",
        phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION,
        task_id="T1",
        context_id="ctx-1",
        model_name="vendor/modelo",
        provider=ModelProviderEnum.OPEN_ROUTER,
        started_at=_INICIO,
    )


def test_uma_invocacao_nova_esta_iniciada_e_sem_consumo_conhecido() -> None:
    invocacao = _iniciada()

    assert invocacao.outcome is InvocationOutcomeEnum.STARTED
    assert invocacao.duration_ms == 0
    assert invocacao.tokens_input is None
    assert invocacao.tokens_output is None
    assert invocacao.finish_reason is None
    assert invocacao.provider_response_id is None
    assert invocacao.usage_known is False


def test_complete_devolve_uma_copia_com_o_desfecho_e_o_consumo() -> None:
    inicial = _iniciada()

    concluida = inicial.complete(
        outcome=InvocationOutcomeEnum.SUCCESS,
        duration_ms=812,
        tokens_input=40,
        tokens_output=12,
        finish_reason="stop",
        provider_response_id="resp-1",
    )

    assert concluida is not inicial
    assert inicial.outcome is InvocationOutcomeEnum.STARTED
    assert concluida.outcome is InvocationOutcomeEnum.SUCCESS
    assert concluida.duration_ms == 812
    assert concluida.tokens_input == 40
    assert concluida.tokens_output == 12
    assert concluida.finish_reason == "stop"
    assert concluida.provider_response_id == "resp-1"
    assert concluida.id == "inv-1"
    assert concluida.usage_known is True


def test_consumo_ausente_continua_desconhecido_e_nao_vira_zero() -> None:
    concluida = _iniciada().complete(
        outcome=InvocationOutcomeEnum.PROVIDER_ERROR,
        duration_ms=30,
        tokens_input=None,
        tokens_output=None,
    )

    assert concluida.tokens_input is None
    assert concluida.tokens_output is None
    assert concluida.usage_known is False


def test_so_o_consumo_de_saida_conhecido_ja_conta_como_conhecido() -> None:
    concluida = _iniciada().complete(
        outcome=InvocationOutcomeEnum.EMPTY_COMPLETION,
        duration_ms=30,
        tokens_input=None,
        tokens_output=140,
    )

    assert concluida.usage_known is True


def test_nao_se_completa_uma_invocacao_para_o_desfecho_iniciada() -> None:
    with pytest.raises(ValueError, match="started"):
        _iniciada().complete(
            outcome=InvocationOutcomeEnum.STARTED, duration_ms=0, tokens_input=None, tokens_output=None
        )


def test_nao_se_completa_duas_vezes() -> None:
    concluida = _iniciada().complete(
        outcome=InvocationOutcomeEnum.SUCCESS, duration_ms=1, tokens_input=1, tokens_output=1
    )

    with pytest.raises(ValueError, match="já foi concluída"):
        concluida.complete(outcome=InvocationOutcomeEnum.SUCCESS, duration_ms=1, tokens_input=1, tokens_output=1)


def test_e_imutavel() -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        _iniciada().duration_ms = 5
