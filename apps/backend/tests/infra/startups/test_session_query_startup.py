import logging
from datetime import UTC, datetime
from pathlib import Path

import pytest

from src.application.usecases.get_session_usecase import GetSessionUseCase
from src.domain.entities.session.session import Session
from src.domain.enums.session_status_enum import SessionStatusEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.domain.errors.session_not_found_error import SessionNotFoundError
from src.infra.mappers.session_document_mapper import SessionDocumentMapper
from src.infra.repositories.json_file_session_repository import JsonFileSessionRepository
from src.infra.startups.session_query_startup import SessionQueryStartup
from tests.doubles.fake_settings import FakeSettings

_CRIADO_EM = datetime(2026, 8, 31, 12, 0, tzinfo=UTC)


def _nova_sessao(session_id: str) -> Session:
    return Session(
        id=session_id,
        user_question="pergunta do usuario",
        flow=ThinkingPhaseEnum.DIRECT_INFERENCE,
        model_name="vendor/modelo",
        max_tokens=1200,
        temperature=0.3,
        status=SessionStatusEnum.COMPLETED,
        created_at=_CRIADO_EM,
        updated_at=_CRIADO_EM,
    )


@pytest.fixture
def storage_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Aponta o armazenamento de sessões para dentro do `tmp_path` do teste."""
    caminho = tmp_path / "sessions"
    monkeypatch.setenv("RALPH_SESSIONS_STORAGE_PATH", str(caminho))
    return caminho


async def _gravar(storage_path: Path, session_id: str) -> None:
    repositorio = JsonFileSessionRepository(
        mapper=SessionDocumentMapper(),
        settings=FakeSettings(ralph_sessions_storage_path=str(storage_path)),
        logger=logging.getLogger("teste"),
    )
    await repositorio.save(session=_nova_sessao(session_id=session_id))


def test_constroi_todo_o_grafo_sem_deixar_atributo_nulo(storage_path: Path) -> None:
    startup = SessionQueryStartup()

    assert vars(startup)
    assert all(valor is not None for valor in vars(startup).values())


def test_injeta_o_repositorio_no_caso_de_uso(storage_path: Path) -> None:
    startup = SessionQueryStartup()

    assert isinstance(startup.get_session_use_case, GetSessionUseCase)
    assert startup.get_session_use_case.repository is startup.session_repository


async def test_devolve_o_documento_da_sessao_gravada(storage_path: Path) -> None:
    await _gravar(storage_path=storage_path, session_id="sess_ab12")

    documento = await SessionQueryStartup().get_session_document(session_id="sess_ab12")

    assert documento["_id"] == "sess_ab12"
    assert documento["id"] == "sess_ab12"
    assert documento["status"] == "completed"


async def test_documento_de_sessao_inexistente_e_recusado(storage_path: Path) -> None:
    with pytest.raises(SessionNotFoundError):
        await SessionQueryStartup().get_session_document(session_id="sess_zzz")


async def test_lista_os_identificadores_gravados(storage_path: Path) -> None:
    await _gravar(storage_path=storage_path, session_id="sess_b")
    await _gravar(storage_path=storage_path, session_id="sess_a")

    assert await SessionQueryStartup().list_session_ids() == ["sess_a", "sess_b"]
