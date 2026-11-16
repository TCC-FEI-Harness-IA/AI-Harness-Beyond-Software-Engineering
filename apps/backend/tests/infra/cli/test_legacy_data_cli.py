"""Atribuição explícita do histórico legado (sem dono) a uma conta: cópia, nunca movimentação."""
import asyncio
import json
from pathlib import Path

import pytest
from mongomock_motor import AsyncMongoMockClient

from src.infra.adapters import mongo_client_adapter
from src.infra.cli import legacy_data_cli as cli
from src.infra.config.settings import Settings
from src.infra.mappers.benchmark_session_document_mapper import BenchmarkSessionDocumentMapper
from src.infra.mappers.session_document_mapper import SessionDocumentMapper
from src.infra.repositories.benchmark_session_repository_factory import BenchmarkSessionRepositoryFactory
from src.infra.repositories.session_repository_factory import SessionRepositoryFactory
from tests.doubles.publication_doubles import bateria_concluida


@pytest.fixture
def legado(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("RALPH_SESSION_STORAGE_BACKEND", "json_file")
    monkeypatch.setenv("RALPH_SESSIONS_STORAGE_PATH", str(tmp_path / "sessions"))
    monkeypatch.setenv("RALPH_BENCHMARK_SESSIONS_STORAGE_PATH", str(tmp_path / "benchmark-sessions"))
    (tmp_path / "sessions").mkdir()
    (tmp_path / "benchmark-sessions").mkdir()
    bateria, sessoes = bateria_concluida("bench_legada")
    (tmp_path / "benchmark-sessions" / "bench_legada.json").write_text(
        json.dumps(BenchmarkSessionDocumentMapper().to_document(bateria))
    )
    for sessao in sessoes:
        documento = SessionDocumentMapper().to_document(sessao)
        (tmp_path / "sessions" / f"{sessao.id}.json").write_text(json.dumps(documento))
    return tmp_path


def _rodar(*argv: str) -> int:
    return asyncio.run(cli.run(list(argv)))


def _arquivos(base: Path) -> dict[Path, bytes]:
    return {path: path.read_bytes() for path in base.glob("*/*.json")}


def test_sem_apply_so_informa(legado: Path, capsys) -> None:
    assert _rodar("assign", "--owner", "usr_autor") == 0

    saida = capsys.readouterr().out
    assert "1 baterias" in saida and "4 sessões" in saida and "nada foi gravado" in saida
    assert not (legado / "sessions" / "owners").exists()


def test_copia_para_a_conta_preservando_a_origem_e_e_idempotente(legado: Path, capsys) -> None:
    antes = _arquivos(legado)

    assert _rodar("assign", "--owner", "usr_autor", "--apply") == 0
    assert _rodar("assign", "--owner", "usr_autor", "--apply") == 0

    assert _arquivos(legado) == antes
    settings = Settings()
    baterias = asyncio.run(
        BenchmarkSessionRepositoryFactory(settings, BenchmarkSessionDocumentMapper()).create("usr_autor").list_all()
    )
    sessoes = asyncio.run(SessionRepositoryFactory(settings, SessionDocumentMapper()).create("usr_autor").list_ids())
    assert [item.id for item in baterias] == ["bench_legada"]
    assert len(sessoes) == 4
    assert "0 copiadas" in capsys.readouterr().out.splitlines()[-1]
    outra = SessionRepositoryFactory(settings, SessionDocumentMapper()).create("usr_outra")
    assert asyncio.run(outra.list_ids()) == []


def test_mongodb(monkeypatch: pytest.MonkeyPatch) -> None:
    cliente = AsyncMongoMockClient()
    monkeypatch.setattr(mongo_client_adapter, "AsyncIOMotorClient", lambda *_, **__: cliente)
    monkeypatch.setenv("RALPH_SESSION_STORAGE_BACKEND", "mongodb")
    bateria, sessoes = bateria_concluida("bench_mongo")
    asyncio.run(cliente["tcc"]["benchmark_sessions"].insert_one(BenchmarkSessionDocumentMapper().to_document(bateria)))
    for sessao in sessoes:
        asyncio.run(cliente["tcc"]["sessions"].insert_one(SessionDocumentMapper().to_document(sessao)))

    assert _rodar("assign", "--owner", "usr_autor", "--apply") == 0
    assert _rodar("assign", "--owner", "usr_autor", "--apply") == 0

    settings = Settings()
    repositorio = BenchmarkSessionRepositoryFactory(settings, BenchmarkSessionDocumentMapper()).create("usr_autor")
    assert [item.id for item in asyncio.run(repositorio.list_all())] == ["bench_mongo"]
    assert asyncio.run(cliente["tcc"]["sessions"].count_documents({"owner_id": {"$exists": False}})) == 4
    assert asyncio.run(cliente["tcc"]["sessions"].count_documents({"owner_id": "usr_autor"})) == 4


def test_dono_invalido_e_recusado(legado: Path, capsys) -> None:
    assert _rodar("assign", "--owner", "../x", "--apply") == 2
    assert "inválido" in capsys.readouterr().err


def test_main(legado: Path) -> None:
    assert cli.main(["assign", "--owner", "usr_autor"]) == 0
