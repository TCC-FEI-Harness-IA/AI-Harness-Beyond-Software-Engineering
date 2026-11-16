"""Linha de comando administrativa da carga e substituição dos resultados oficiais."""
import asyncio
import json
from pathlib import Path

import pytest

from src.domain.enums.benchmark_dataset_enum import BenchmarkDatasetEnum
from src.domain.enums.benchmark_session_status_enum import BenchmarkSessionStatusEnum
from src.infra.cli import official_publications_cli as cli
from src.infra.config.settings import Settings
from src.infra.mappers.benchmark_session_document_mapper import BenchmarkSessionDocumentMapper
from src.infra.mappers.session_document_mapper import SessionDocumentMapper
from src.infra.repositories.benchmark_session_repository_factory import BenchmarkSessionRepositoryFactory
from src.infra.repositories.session_repository_factory import SessionRepositoryFactory
from tests.doubles.publication_doubles import bateria_concluida

V, M, G = BenchmarkDatasetEnum.VESTIBULAR, BenchmarkDatasetEnum.MMLU, BenchmarkDatasetEnum.GPQA


@pytest.fixture
def dados(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("RALPH_SESSION_STORAGE_BACKEND", "json_file")
    monkeypatch.setenv("RALPH_SESSIONS_STORAGE_PATH", str(tmp_path / "sessions"))
    monkeypatch.setenv("RALPH_BENCHMARK_SESSIONS_STORAGE_PATH", str(tmp_path / "benchmark-sessions"))
    monkeypatch.setenv("RALPH_OFFICIAL_STORAGE_PATH", str(tmp_path / "official"))
    (tmp_path / "sessions").mkdir()
    (tmp_path / "benchmark-sessions").mkdir()
    for battery_id, dataset, horas in [("bench_v", V, 1), ("bench_m", M, 2), ("bench_v_velha", V, 0)]:
        _gravar_legado(tmp_path, *bateria_concluida(battery_id, dataset, horas=horas))
    interrompida, sessoes = bateria_concluida("bench_g_interrompida", G, horas=3)
    interrompida.status = BenchmarkSessionStatusEnum.INTERRUPTED
    _gravar_legado(tmp_path, interrompida, sessoes)
    return tmp_path


def _gravar_legado(base: Path, bateria, sessoes) -> None:
    (base / "benchmark-sessions" / f"{bateria.id}.json").write_text(
        json.dumps(BenchmarkSessionDocumentMapper().to_document(bateria)), encoding="utf-8"
    )
    for sessao in sessoes:
        (base / "sessions" / f"{sessao.id}.json").write_text(
            json.dumps(SessionDocumentMapper().to_document(sessao)), encoding="utf-8"
        )


def _fotografia(base: Path) -> dict[Path, bytes]:
    return {path: path.read_bytes() for path in (base / "sessions").rglob("*.json")} | {
        path: path.read_bytes() for path in (base / "benchmark-sessions").rglob("*.json")
    }


def _rodar(*argv: str) -> int:
    return asyncio.run(cli.run(list(argv)))


def test_descoberta_informa_o_armazenamento_efetivo(dados: Path, capsys) -> None:
    assert _rodar("discover") == 0

    saida = capsys.readouterr().out
    assert "json_file" in saida
    assert str(dados / "benchmark-sessions") in saida
    assert "4 baterias" in saida


def test_inspecao_mostra_selecao_e_descartes_sem_escrever(dados: Path, capsys) -> None:
    (dados / "benchmark-sessions" / "bench_corrompida.json").write_text("{nao-json", encoding="utf-8")
    antes = _fotografia(dados)

    assert _rodar("inspect", "--source", "legacy") == 0

    saida = capsys.readouterr().out
    assert "vestibular: bench_v" in saida
    assert "mmlu: bench_m" in saida
    assert "gpqa: AUSENTE" in saida
    assert "bench_g_interrompida" in saida and "interrupted" in saida
    assert "protocolo generative_5shot" in saida and "seed 42" in saida
    assert "4 questões" not in saida and "2 questões" in saida
    assert "ilegível bench_corrompida" in saida
    assert _fotografia(dados) == antes
    assert not (dados / "official").exists()


def test_carga_sem_apply_nao_escreve(dados: Path, capsys) -> None:
    assert _rodar("publish-initial", "--source", "legacy", "--published-by", "admin") == 0

    assert "inspeção: nada foi gravado" in capsys.readouterr().out
    assert not (dados / "official").exists()


def test_carga_aplicada_e_idempotente_e_preserva_a_origem(dados: Path, capsys) -> None:
    antes = _fotografia(dados)
    backups = dados / "backups"

    assert _rodar("publish-initial", "--source", "legacy", "--published-by", "admin",
                  "--backup-dir", str(backups), "--apply") == 0
    primeira = capsys.readouterr().out
    assert _rodar("publish-initial", "--source", "legacy", "--published-by", "admin",
                  "--backup-dir", str(backups), "--apply") == 0
    segunda = capsys.readouterr().out

    assert primeira.count("publish") >= 2 and "pub_" in primeira
    assert "already_published" in segunda
    assert len(list((dados / "official" / "publications").iterdir())) == 2
    assert len(list(backups.iterdir())) == 1
    assert _fotografia(dados) == antes

    assert _rodar("list") == 0
    listagem = capsys.readouterr().out
    assert "vestibular" in listagem and "bench_v" in listagem and "active" in listagem


def test_substituicao_explicita(dados: Path, capsys) -> None:
    _rodar("publish-initial", "--source", "legacy", "--published-by", "admin", "--backup-dir",
           str(dados / "backups"), "--apply")
    capsys.readouterr()

    sem_apply = _rodar("replace", "--source", "legacy", "--benchmark-session-id", "bench_v_velha",
                       "--published-by", "admin")
    assert "inspeção" in capsys.readouterr().out
    codigo = _rodar("replace", "--source", "legacy", "--benchmark-session-id", "bench_v_velha",
                    "--published-by", "admin", "--backup-dir", str(dados / "backups"), "--apply")
    saida = capsys.readouterr().out

    assert sem_apply == 0 and codigo == 0
    assert "replace" in saida
    _rodar("list")
    listagem = capsys.readouterr().out
    assert "superseded" in listagem and "bench_v_velha" in listagem


def test_substituicao_por_bateria_nao_integra_e_recusada(dados: Path, capsys) -> None:
    codigo = _rodar("replace", "--source", "legacy", "--benchmark-session-id", "bench_g_interrompida",
                    "--published-by", "admin", "--apply")

    assert codigo == 2
    assert "interrupted" in capsys.readouterr().err


def test_origem_de_uma_conta_explicita(dados: Path, capsys) -> None:
    settings = Settings()
    bateria, sessoes = bateria_concluida("bench_da_conta", G)
    baterias = BenchmarkSessionRepositoryFactory(settings, BenchmarkSessionDocumentMapper()).create("usr_admin")
    asyncio.run(baterias.save(bateria))
    repositorio = SessionRepositoryFactory(settings, SessionDocumentMapper()).create("usr_admin")
    for sessao in sessoes:
        asyncio.run(repositorio.save(sessao))

    assert _rodar("inspect", "--source", "owner:usr_admin") == 0

    saida = capsys.readouterr().out
    assert "gpqa: bench_da_conta" in saida
    assert "vestibular: AUSENTE" in saida
    assert "usr_admin" in saida


def test_origem_desconhecida(dados: Path, capsys) -> None:
    assert _rodar("inspect", "--source", "todos") == 2
    assert "Origem pessoal desconhecida" in capsys.readouterr().err


def test_backend_mongodb_usa_as_colecoes_legadas(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from mongomock_motor import AsyncMongoMockClient

    from src.infra.adapters import mongo_client_adapter

    cliente = AsyncMongoMockClient()
    monkeypatch.setattr(mongo_client_adapter, "AsyncIOMotorClient", lambda *_, **__: cliente)
    monkeypatch.setenv("RALPH_SESSION_STORAGE_BACKEND", "mongodb")
    bateria, sessoes = bateria_concluida("bench_mongo", M)
    asyncio.run(cliente["tcc"]["benchmark_sessions"].insert_one(BenchmarkSessionDocumentMapper().to_document(bateria)))
    for sessao in sessoes:
        asyncio.run(cliente["tcc"]["sessions"].insert_one(SessionDocumentMapper().to_document(sessao)))

    assert _rodar("discover") == 0
    assert _rodar("publish-initial", "--source", "legacy", "--published-by", "admin",
                  "--backup-dir", str(tmp_path / "bk"), "--apply") == 0

    assert asyncio.run(cliente["tcc"]["official_publications"].count_documents({})) == 1
    assert len(list((tmp_path / "bk").iterdir())) == 1


def test_main_executa_o_comando(dados: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert cli.main(["discover"]) == 0
