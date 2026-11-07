import logging
from datetime import timedelta

import pytest
from mongomock_motor import AsyncMongoMockClient

from src.domain.errors.benchmark_session_not_found_error import BenchmarkSessionNotFoundError
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


async def test_alias_persistido_nao_sobrescreve_resultados_e_sobrevive_a_reexecucao() -> None:
    repository = _repositorio()
    session = bateria()
    await repository.save(session)
    edit = await repository.find_by_id(session.id)
    assert edit is not None
    # A execução avança depois da leitura usada pela edição do alias.
    session.wall_time_ms = 250
    await repository.save(session)
    edit.alias = "Rodada de comparação"
    edit.updated_at += timedelta(minutes=1)
    await repository.update_alias(edit)
    document = await repository.collection.find_one({"_id": session.id})
    assert document is not None
    assert document["alias"] == edit.alias
    assert document["updated_at"] == edit.updated_at.isoformat()
    assert document["wall_time_ms"] == 250
    # Uma execução com snapshot anterior à edição deve preservar o alias.
    await repository.save(session)
    assert (await repository.list_all())[0].alias == edit.alias
    edit.alias = None
    await repository.update_alias(edit)
    await repository.save(session)
    assert (await repository.list_all())[0].alias is None


async def test_editar_alias_nao_cria_bateria_inexistente() -> None:
    repository = _repositorio()
    with pytest.raises(BenchmarkSessionNotFoundError):
        await repository.update_alias(bateria())
    assert await repository.collection.count_documents({}) == 0


async def test_listagem_ordena_da_mais_recente_para_a_mais_antiga() -> None:
    repositorio = _repositorio()
    antiga = bateria("Q1")
    recente = bateria("Q1")
    recente.id = "bench_2"
    recente.created_at = antiga.created_at + timedelta(days=1)
    await repositorio.save(benchmark_session=antiga)
    await repositorio.save(benchmark_session=recente)

    assert [item.id for item in await repositorio.list_all()] == ["bench_2", "bench_1"]
