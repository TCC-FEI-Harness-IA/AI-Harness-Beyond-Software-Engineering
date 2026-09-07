import dataclasses

import pytest

from src.domain.entities.llm.llm_provider_message import LLMProviderMessage


def test_carrega_papel_e_conteudo() -> None:
    message = LLMProviderMessage(role="user", content="pergunta")

    assert message.role == "user"
    assert message.content == "pergunta"


def test_e_imutavel() -> None:
    message = LLMProviderMessage(role="user", content="pergunta")

    with pytest.raises(dataclasses.FrozenInstanceError):
        message.role = "assistant"
