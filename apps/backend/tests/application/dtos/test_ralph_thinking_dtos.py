import dataclasses

import pytest

from src.application.dtos.ralph_thinking_input_dto import RalphThinkingInputDTO
from src.application.dtos.ralph_thinking_output_dto import RalphThinkingOutputDTO
from src.domain.enums.session_status_enum import SessionStatusEnum


def test_dto_de_entrada_carrega_os_parametros_da_sessao() -> None:
    dto = RalphThinkingInputDTO(
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
    dto = RalphThinkingInputDTO(
        user_input="pergunta",
        model_name="vendor/modelo",
        max_tokens=100,
        temperature=0.3,
    )

    with pytest.raises(dataclasses.FrozenInstanceError):
        dto.user_input = "outra"


def test_dto_de_saida_carrega_resposta_e_metricas() -> None:
    dto = RalphThinkingOutputDTO(
        session_id="sess_1",
        final_answer="resposta final",
        status=SessionStatusEnum.COMPLETED,
        total_tokens=642,
        total_inference_time_ms=812,
    )

    assert dto.session_id == "sess_1"
    assert dto.final_answer == "resposta final"
    assert dto.status is SessionStatusEnum.COMPLETED
    assert dto.total_tokens == 642
    assert dto.total_inference_time_ms == 812


def test_dto_de_saida_e_imutavel() -> None:
    dto = RalphThinkingOutputDTO(
        session_id="sess_1",
        final_answer="resposta final",
        status=SessionStatusEnum.COMPLETED,
        total_tokens=642,
        total_inference_time_ms=812,
    )

    with pytest.raises(dataclasses.FrozenInstanceError):
        dto.final_answer = "outra"
