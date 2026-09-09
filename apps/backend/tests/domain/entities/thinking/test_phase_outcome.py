import dataclasses

import pytest

from src.domain.entities.llm.genai_model import GenaiModel
from src.domain.entities.llm.tokens_usage import TokensUsage
from src.domain.entities.thinking.phase_outcome import PhaseOutcome
from src.domain.enums.model_provider_enum import ModelProviderEnum

_TOKENS = TokensUsage(
    tokens_input=10,
    tokens_output=20,
    llm_model=GenaiModel(model_name="vendor/modelo", model_provider=ModelProviderEnum.OPEN_ROUTER),
)


def test_carrega_os_campos_informados() -> None:
    resultado = PhaseOutcome(
        raw_output='{"chave": "valor"}',
        parsed={"chave": "valor"},
        tokens=_TOKENS,
        inference_time_ms=500,
        context_id="ctx-1",
    )

    assert resultado.raw_output == '{"chave": "valor"}'
    assert resultado.parsed == {"chave": "valor"}
    assert resultado.tokens is _TOKENS
    assert resultado.inference_time_ms == 500
    assert resultado.context_id == "ctx-1"


def test_e_imutavel() -> None:
    resultado = PhaseOutcome(
        raw_output='{"chave": "valor"}',
        parsed={"chave": "valor"},
        tokens=_TOKENS,
        inference_time_ms=500,
        context_id="ctx-1",
    )

    with pytest.raises(dataclasses.FrozenInstanceError):
        resultado.context_id = "ctx-2"
