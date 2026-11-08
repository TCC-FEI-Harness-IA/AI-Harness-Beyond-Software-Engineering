import logging
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.domain.entities.session.session import Session
from src.domain.enums.session_status_enum import SessionStatusEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.infra.mappers.session_document_mapper import SessionDocumentMapper
from src.infra.repositories.json_file_session_repository import JsonFileSessionRepository
from src.infra.routes.v1.session import router as session_router_module
from src.main import create_app
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


@pytest.fixture
def client(storage_path: Path) -> TestClient:
    """Cliente HTTP com o armazenamento de sessões isolado no `tmp_path`."""
    return TestClient(create_app())


async def _gravar(storage_path: Path, session_id: str) -> Session:
    sessao = _nova_sessao(session_id=session_id)
    repositorio = JsonFileSessionRepository(
        mapper=SessionDocumentMapper(),
        settings=FakeSettings(ralph_sessions_storage_path=str(storage_path)),
        logger=logging.getLogger("teste"),
    )
    await repositorio.save(session=sessao)
    return sessao


async def test_consulta_devolve_o_documento_da_sessao(client: TestClient, storage_path: Path) -> None:
    sessao = await _gravar(storage_path=storage_path, session_id="sess_ab12")

    resposta = client.get("/v1/sessions/sess_ab12")

    assert resposta.status_code == 200
    assert resposta.json() == SessionDocumentMapper().to_document(session=sessao)


def test_consulta_de_sessao_inexistente_devolve_404(client: TestClient) -> None:
    resposta = client.get("/v1/sessions/sess_zzz")

    assert resposta.status_code == 404
    assert "sess_zzz" in resposta.json()["detail"]


def test_identificador_invalido_devolve_400(client: TestClient) -> None:
    resposta = client.get("/v1/sessions/sess%20invalido")

    assert resposta.status_code == 400
    assert "inválido" in resposta.json()["detail"]


def test_falha_inesperada_na_consulta_vira_500(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    class _StartupQuebrado:
        def __init__(self) -> None:
            raise RuntimeError("disco fora do ar")

    monkeypatch.setattr(session_router_module, "SessionQueryStartup", _StartupQuebrado)

    resposta = client.get("/v1/sessions/sess_ab12")

    assert resposta.status_code == 500
    assert resposta.json()["detail"] == "disco fora do ar"


async def test_listagem_devolve_os_identificadores(client: TestClient, storage_path: Path) -> None:
    await _gravar(storage_path=storage_path, session_id="sess_b")
    await _gravar(storage_path=storage_path, session_id="sess_a")

    resposta = client.get("/v1/sessions")

    assert resposta.status_code == 200
    assert resposta.json() == {"session_ids": ["sess_a", "sess_b"]}


def test_listagem_sem_sessoes_devolve_lista_vazia(client: TestClient) -> None:
    resposta = client.get("/v1/sessions")

    assert resposta.status_code == 200
    assert resposta.json() == {"session_ids": []}


def test_falha_inesperada_na_listagem_vira_500(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    class _StartupQuebrado:
        def __init__(self) -> None:
            raise RuntimeError("disco fora do ar")

    monkeypatch.setattr(session_router_module, "SessionQueryStartup", _StartupQuebrado)

    resposta = client.get("/v1/sessions")

    assert resposta.status_code == 500
    assert resposta.json()["detail"] == "disco fora do ar"
