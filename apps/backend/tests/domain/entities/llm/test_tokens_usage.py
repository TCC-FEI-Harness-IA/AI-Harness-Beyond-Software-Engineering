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


_MODELO = GenaiModel(model_name="vendor/modelo", model_provider=ModelProviderEnum.OPEN_ROUTER)


def test_os_dois_contadores_sao_conhecidos_por_padrao() -> None:
    tokens = _build_tokens()

    assert tokens.input_known is True
    assert tokens.output_known is True
    assert tokens.known_input == 7
    assert tokens.known_output == 13


def test_contador_desconhecido_vale_zero_para_somar_e_none_para_registrar() -> None:
    tokens = TokensUsage(tokens_input=10, tokens_output=0, llm_model=_MODELO, input_known=True, output_known=False)

    assert tokens.tokens_output == 0
    assert tokens.known_input == 10
    assert tokens.known_output is None


def test_zero_conhecido_nao_se_confunde_com_desconhecido() -> None:
    tokens = TokensUsage(tokens_input=0, tokens_output=0, llm_model=_MODELO)

    assert tokens.known_input == 0
    assert tokens.known_output == 0


def test_from_reported_converte_none_em_contador_desconhecido() -> None:
    tokens = TokensUsage.from_reported(tokens_input=None, tokens_output=9, llm_model=_MODELO)

    assert (tokens.tokens_input, tokens.tokens_output) == (0, 9)
    assert tokens.input_known is False
    assert tokens.output_known is True
    assert tokens.known_input is None
    assert tokens.known_output == 9
