import dataclasses
from datetime import UTC, datetime

import pytest

from src.domain.entities.session.session_message import SessionMessage
from src.domain.enums.message_source_enum import MessageSourceEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum

_TIMESTAMP = datetime.now(tz=UTC)


def _nova_mensagem() -> SessionMessage:
    return SessionMessage(
        id="msg-1",
        order=1,
        timestamp=_TIMESTAMP,
        phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION,
        source=MessageSourceEnum.LLM_AGENT,
        content="conteudo",
        task_id="t1",
        context_id="ctx-1",
        tokens_input=10,
        tokens_output=20,
        inference_time_ms=100,
        model_name="vendor/modelo",
    )


def test_carrega_todos_os_campos() -> None:
    mensagem = _nova_mensagem()

    assert mensagem.id == "msg-1"
    assert mensagem.order == 1
    assert mensagem.timestamp == _TIMESTAMP
    assert mensagem.phase is ThinkingPhaseEnum.B1_TASK_RESOLUTION
    assert mensagem.source is MessageSourceEnum.LLM_AGENT
    assert mensagem.content == "conteudo"
    assert mensagem.task_id == "t1"
    assert mensagem.context_id == "ctx-1"
    assert mensagem.tokens_input == 10
    assert mensagem.tokens_output == 20
    assert mensagem.inference_time_ms == 100
    assert mensagem.model_name == "vendor/modelo"


def test_e_imutavel() -> None:
    mensagem = _nova_mensagem()

    with pytest.raises(dataclasses.FrozenInstanceError):
        mensagem.content = "outro"


def test_total_tokens_soma_entrada_e_saida() -> None:
    mensagem = _nova_mensagem()

    assert mensagem.total_tokens == 30


def test_total_tokens_de_mensagem_sem_consumo_e_zero() -> None:
    mensagem = dataclasses.replace(_nova_mensagem(), tokens_input=0, tokens_output=0)

    assert mensagem.total_tokens == 0
