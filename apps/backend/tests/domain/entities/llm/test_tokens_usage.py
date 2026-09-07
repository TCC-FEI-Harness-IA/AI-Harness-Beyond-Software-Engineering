import dataclasses

import pytest

from src.domain.entities.llm.genai_model import GenaiModel
from src.domain.entities.llm.tokens_usage import TokensUsage
from src.domain.enums.model_provider_enum import ModelProviderEnum


def _build_tokens() -> TokensUsage:
    return TokensUsage(
        tokens_input=7,
        tokens_output=13,
        llm_model=GenaiModel(model_name="vendor/modelo", model_provider=ModelProviderEnum.OPEN_ROUTER),
    )


def test_carrega_consumo_e_modelo() -> None:
    tokens = _build_tokens()

    assert tokens.tokens_input == 7
    assert tokens.tokens_output == 13
    assert tokens.llm_model.model_name == "vendor/modelo"


def test_e_imutavel() -> None:
    tokens = _build_tokens()

    with pytest.raises(dataclasses.FrozenInstanceError):
        tokens.tokens_input = 99
