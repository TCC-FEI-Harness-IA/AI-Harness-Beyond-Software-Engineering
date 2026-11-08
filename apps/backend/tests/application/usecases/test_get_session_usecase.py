import logging
from datetime import UTC, datetime

import pytest

from src.application.usecases.get_session_usecase import GetSessionUseCase
from src.domain.entities.session.session import Session
from src.domain.enums.session_status_enum import SessionStatusEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.domain.errors.session_not_found_error import SessionNotFoundError
from tests.doubles.in_memory_session_repository import InMemorySessionRepository

_CRIADO_EM = datetime(2026, 8, 31, 12, 0, tzinfo=UTC)


def _nova_sessao() -> Session:
    return Session(
        id="sess_ab12",
        user_question="pergunta do usuario",
        flow=ThinkingPhaseEnum.DIRECT_INFERENCE,
        model_name="vendor/modelo",
        max_tokens=1200,
        temperature=0.3,
        status=SessionStatusEnum.COMPLETED,
        created_at=_CRIADO_EM,
        updated_at=_CRIADO_EM,
    )


def _build_usecase(repository: InMemorySessionRepository) -> GetSessionUseCase:
    return GetSessionUseCase(repository=repository, logger=logging.getLogger("teste"))


async def test_devolve_a_sessao_encontrada() -> None:
    repositorio = InMemorySessionRepository()
    sessao = _nova_sessao()
    await repositorio.save(session=sessao)

    assert await _build_usecase(repository=repositorio).execute(session_id="sess_ab12") == sessao


async def test_sessao_inexistente_levanta_erro_de_dominio() -> None:
    with pytest.raises(SessionNotFoundError) as erro:
        await _build_usecase(repository=InMemorySessionRepository()).execute(session_id="sess_zzz")

    assert erro.value.session_id == "sess_zzz"


async def test_falha_do_repositorio_e_propagada_e_registrada(caplog: pytest.LogCaptureFixture) -> None:
    class _RepositorioQuebrado(InMemorySessionRepository):
        async def find_by_id(self, session_id: str) -> Session | None:
            raise RuntimeError("disco fora do ar")

    with caplog.at_level(logging.ERROR):
        with pytest.raises(RuntimeError, match="disco fora do ar"):
            await _build_usecase(repository=_RepositorioQuebrado()).execute(session_id="sess_ab12")

    assert "Erro ao executar GetSessionUseCase" in caplog.text
