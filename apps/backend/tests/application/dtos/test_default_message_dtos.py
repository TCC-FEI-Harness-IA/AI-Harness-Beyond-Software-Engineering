import dataclasses

import pytest

from src.application.dtos.default_message_input_dto import DefaultMessageInputDTO
from src.application.dtos.default_message_output_dto import DefaultMessageOutputDTO


def test_dto_de_entrada_carrega_os_parametros_da_chamada() -> None:
    dto = DefaultMessageInputDTO(
        user_input="pergunta",
        model_name="vendor/modelo",
        max_tokens=100,
        temperature=0.3,
    )

    assert dto.user_input == "pergunta"
    assert dto.model_name == "vendor/modelo"
    assert dto.max_tokens == 100
    assert dto.temperature == 0.3


def test_dto_de_entrada_e_imutavel() -> None:
    dto = DefaultMessageInputDTO(
        user_input="pergunta",
        model_name="vendor/modelo",
        max_tokens=100,
        temperature=0.3,
    )

    with pytest.raises(dataclasses.FrozenInstanceError):
        dto.user_input = "outra"


def test_dto_de_saida_carrega_resposta_e_metricas() -> None:
    dto = DefaultMessageOutputDTO(
        message="pergunta",
        response="resposta",
        tokens_input=11,
        tokens_output=22,
        inference_time_ms=0,
    )

    assert dto.message == "pergunta"
    assert dto.response == "resposta"
    assert dto.tokens_input == 11
    assert dto.tokens_output == 22
    assert dto.inference_time_ms == 0


def test_dto_de_saida_e_imutavel() -> None:
    dto = DefaultMessageOutputDTO(
        message="pergunta",
        response="resposta",
        tokens_input=0,
        tokens_output=0,
        inference_time_ms=0,
    )

    with pytest.raises(dataclasses.FrozenInstanceError):
        dto.response = "outra"
