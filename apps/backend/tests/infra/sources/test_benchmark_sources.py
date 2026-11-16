import json
import logging
from pathlib import Path

import pytest
from mongomock_motor import AsyncMongoMockClient

from src.domain.enums.benchmark_dataset_enum import BenchmarkDatasetEnum
from src.infra.mappers.benchmark_session_document_mapper import BenchmarkSessionDocumentMapper
from src.infra.mappers.session_document_mapper import SessionDocumentMapper
from src.infra.sources.legacy_json_benchmark_source import LegacyJsonBenchmarkSource
from src.infra.sources.legacy_mongo_benchmark_source import LegacyMongoBenchmarkSource
from src.infra.sources.owned_benchmark_source import OwnedBenchmarkSource
from tests.doubles.in_memory_benchmark_session_repository import InMemoryBenchmarkSessionRepository
from tests.doubles.in_memory_session_repository import InMemorySessionRepository
from tests.doubles.publication_doubles import bateria_concluida

_BENCH = BenchmarkSessionDocumentMapper()
_SESS = SessionDocumentMapper()


def _gravar_legado(base: Path) -> tuple[str, list[str]]:
    bateria, sessoes = bateria_concluida("bench_legada", BenchmarkDatasetEnum.MMLU)
    (base / "benchmark-sessions").mkdir(parents=True)
    (base / "sessions").mkdir(parents=True)
    (base / "benchmark-sessions" / "bench_legada.json").write_text(json.dumps(_BENCH.to_document(bateria)))
    (base / "benchmark-sessions" / "bench_quebrada.json").write_text("{nao-json")
    (base / "benchmark-sessions" / "owners" / "usr_x").mkdir(parents=True)
    (base / "benchmark-sessions" / "owners" / "usr_x" / "bench_de_outro.json").write_text("{}")
    for sessao in sessoes:
        (base / "sessions" / f"{sessao.id}.json").write_text(json.dumps(_SESS.to_document(sessao)))
    return bateria.id, [sessao.id for sessao in sessoes]


async def test_origem_legada_json_le_so_a_raiz_sem_escrever(tmp_path: Path) -> None:
    battery_id, session_ids = _gravar_legado(tmp_path)
    antes = {path: path.read_bytes() for path in tmp_path.rglob("*.json")}
    origem = LegacyJsonBenchmarkSource(
        benchmarks_dir=tmp_path / "benchmark-sessions", sessions_dir=tmp_path / "sessions",
        benchmark_mapper=_BENCH, session_mapper=_SESS,
    )

    baterias = await origem.list_batteries()

    assert [(item.battery_id, item.battery is not None) for item in baterias] == [
        ("bench_legada", True), ("bench_quebrada", False),
    ]
    assert "JSON" in baterias[1].error
    assert (await origem.find_session(session_ids[0])).id == session_ids[0]
    assert await origem.find_session("sess_inexistente") is None
    with pytest.raises(ValueError):
        await origem.find_session("../fora")
    assert "legado" in origem.describe() and str(tmp_path) in origem.describe()
    assert {path: path.read_bytes() for path in tmp_path.rglob("*.json")} == antes
    assert battery_id == "bench_legada"


async def test_origem_legada_json_sessao_ilegivel(tmp_path: Path) -> None:
    (tmp_path / "sessions").mkdir()
    (tmp_path / "sessions" / "sess_x.json").write_text("{quebrado")
    origem = LegacyJsonBenchmarkSource(
        benchmarks_dir=tmp_path / "nao-existe", sessions_dir=tmp_path / "sessions",
        benchmark_mapper=_BENCH, session_mapper=_SESS,
    )

    assert await origem.list_batteries() == []
    with pytest.raises(ValueError):
        await origem.find_session("sess_x")


async def test_origem_legada_mongo_ignora_documentos_com_dono() -> None:
    client = AsyncMongoMockClient()
    bateria, sessoes = bateria_concluida("bench_legada", BenchmarkDatasetEnum.GPQA)
    await client["db"]["benchmark_sessions"].insert_one(_BENCH.to_document(bateria))
    com_dono = {**_BENCH.to_document(bateria), "_id": "usr_x/bench_legada", "owner_id": "usr_x"}
    await client["db"]["benchmark_sessions"].insert_one(com_dono)
    await client["db"]["benchmark_sessions"].insert_one({"_id": "bench_ruim"})
    await client["db"]["sessions"].insert_one(_SESS.to_document(sessoes[0]))
    await client["db"]["sessions"].insert_one({"_id": "sess_ruim"})
    origem = LegacyMongoBenchmarkSource(
        benchmarks=client["db"]["benchmark_sessions"], sessions=client["db"]["sessions"],
        benchmark_mapper=_BENCH, session_mapper=_SESS,
    )

    baterias = await origem.list_batteries()

    assert [(item.battery_id, item.battery is not None) for item in baterias] == [
        ("bench_legada", True), ("bench_ruim", False),
    ]
    assert (await origem.find_session(sessoes[0].id)).id == sessoes[0].id
    assert await origem.find_session("sess_inexistente") is None
    with pytest.raises(ValueError):
        await origem.find_session("sess_ruim")
    assert "MongoDB" in origem.describe()


async def test_origem_de_uma_conta_usa_os_repositorios_escopados() -> None:
    baterias, sessoes_repo = InMemoryBenchmarkSessionRepository(), InMemorySessionRepository()
    bateria, sessoes = bateria_concluida("bench_da_conta", BenchmarkDatasetEnum.VESTIBULAR)
    await baterias.save(bateria)
    for sessao in sessoes:
        await sessoes_repo.save(sessao)
    origem = OwnedBenchmarkSource(
        benchmark_repository=baterias, session_repository=sessoes_repo, description="conta usr_admin",
        logger=logging.getLogger("teste"),
    )

    assert [item.battery_id for item in await origem.list_batteries()] == ["bench_da_conta"]
    assert (await origem.find_session(sessoes[0].id)).id == sessoes[0].id
    assert origem.describe() == "conta usr_admin"
