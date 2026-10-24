"""Fixtures compartilhadas pelos testes da camada de aplicação."""
import logging

import pytest

from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.infra.adapters.session_recorder_adapter import SessionRecorderAdapter
from tests.doubles.fake_clock import FakeClock
from tests.doubles.fake_id_generator import FakeIdGenerator
from tests.doubles.fake_settings import FakeSettings
from tests.doubles.in_memory_session_repository import InMemorySessionRepository


@pytest.fixture
async def recorder() -> SessionRecorderAdapter:
    """Gravador real, sobre repositório em memória, com a sessão já iniciada."""
    gravador = SessionRecorderAdapter(
        repository=InMemorySessionRepository(),
        clock=FakeClock(),
        id_generator=FakeIdGenerator(),
        settings=FakeSettings(),
        logger=logging.getLogger("teste.recorder"),
    )
    await gravador.start(
        user_question="pergunta",
        flow=ThinkingPhaseEnum.A1_GENERAL_CRITERIA,
        model_name="vendor/modelo",
        max_tokens=1200,
        temperature=0.3,
    )
    return gravador
