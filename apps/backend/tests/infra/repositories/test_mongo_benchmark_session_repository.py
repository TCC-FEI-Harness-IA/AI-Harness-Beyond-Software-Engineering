import logging
from datetime import timedelta

from mongomock_motor import AsyncMongoMockClient

from src.infra.mappers.benchmark_session_document_mapper import BenchmarkSessionDocumentMapper
from src.infra.repositories.mongo_benchmark_session_repository import MongoBenchmarkSessionRepository
from tests.doubles.benchmark_factories import bateria


def _repositorio() -> MongoBenchmarkSessionRepository:
    return MongoBenchmarkSessionRepository(
        collection=AsyncMongoMockClient()["banco_de_teste"]["baterias"],
        mapper=BenchmarkSessionDocumentMapper(),
        logger=logging.getLogger("teste"),
    )


async def test_save_substitui_e_find_by_id_devolve_a_bateria() -> None:
    repositorio = _repositorio()
    sessao = bateria("Q1")
    await repositorio.save(benchmark_session=sessao)
    sessao.max_parallel = 4
    await repositorio.save(benchmark_session=sessao)

    encontrada = await repositorio.find_by_id(benchmark_session_id="bench_1")

    assert encontrada == sessao
    assert await repositorio.collection.count_documents({}) == 1


async def test_bateria_inexistente_devolve_none() -> None:
    assert await _repositorio().find_by_id(benchmark_session_id="bench_9") is None


async def test_listagem_ordena_da_mais_recente_para_a_mais_antiga() -> None:
    repositorio = _repositorio()
    antiga = bateria("Q1")
    recente = bateria("Q1")
    recente.id = "bench_2"
    recente.created_at = antiga.created_at + timedelta(days=1)
    await repositorio.save(benchmark_session=antiga)
    await repositorio.save(benchmark_session=recente)

    assert [item.id for item in await repositorio.list_all()] == ["bench_2", "bench_1"]
