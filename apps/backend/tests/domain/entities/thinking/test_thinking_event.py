import dataclasses

import pytest

from src.domain.entities.thinking.thinking_event import ThinkingEvent
from src.domain.enums.thinking_event_subtype_enum import ThinkingEventSubtypeEnum
from src.domain.enums.thinking_event_type_enum import ThinkingEventTypeEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum


def _novo_evento() -> ThinkingEvent:
    return ThinkingEvent(
        type=ThinkingEventTypeEnum.THINKING,
        subtype=ThinkingEventSubtypeEnum.EXECUTE,
        phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION,
        task="t1",
        content="markdown renderizavel",
        session_id="sess_1",
        total_tokens=642,
        context_id="ctx-1",
        context_size=182,
        inference_time_ms=812,
    )


def test_carrega_todos_os_campos_do_contrato() -> None:
    evento = _novo_evento()

    assert evento.type is ThinkingEventTypeEnum.THINKING
    assert evento.subtype is ThinkingEventSubtypeEnum.EXECUTE
    assert evento.phase is ThinkingPhaseEnum.B1_TASK_RESOLUTION
    assert evento.task == "t1"
    assert evento.content == "markdown renderizavel"
    assert evento.session_id == "sess_1"
    assert evento.total_tokens == 642
    assert evento.context_id == "ctx-1"
    assert evento.context_size == 182
    assert evento.inference_time_ms == 812


def test_e_imutavel() -> None:
    evento = _novo_evento()

    with pytest.raises(dataclasses.FrozenInstanceError):
        evento.content = "outro conteudo"
