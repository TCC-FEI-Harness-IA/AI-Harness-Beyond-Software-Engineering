import logging
from datetime import timedelta

import pytest

from src.application.usecases.get_benchmark_session_usecase import GetBenchmarkSessionUseCase
from src.application.usecases.list_benchmark_sessions_usecase import ListBenchmarkSessionsUseCase
from src.domain.errors.benchmark_session_not_found_error import BenchmarkSessionNotFoundError
from tests.doubles.benchmark_factories import bateria
from tests.doubles.in_memory_benchmark_session_repository import InMemoryBenchmarkSessionRepository

_LOGGER = logging.getLogger("teste.benchmark")


async def test_consulta_devolve_a_bateria_gravada() -> None:
    repositorio = InMemoryBenchmarkSessionRepository()
    await repositorio.save(bateria("Q1"))

    encontrada = await GetBenchmarkSessionUseCase(repository=repositorio, logger=_LOGGER).execute("bench_1")

    assert encontrada.id == "bench_1"


async def test_consulta_de_bateria_inexistente_e_recusada() -> None:
    caso = GetBenchmarkSessionUseCase(repository=InMemoryBenchmarkSessionRepository(), logger=_LOGGER)

    with pytest.raises(BenchmarkSessionNotFoundError):
        await caso.execute("bench_9")


async def test_listagem_devolve_as_baterias_da_mais_recente_para_a_mais_antiga() -> None:
    repositorio = InMemoryBenchmarkSessionRepository()
    antiga = bateria("Q1")
    recente = bateria("Q1")
    recente.id = "bench_2"
    recente.created_at = antiga.created_at + timedelta(hours=1)
    await repositorio.save(antiga)
    await repositorio.save(recente)

    baterias = await ListBenchmarkSessionsUseCase(repository=repositorio, logger=_LOGGER).execute()

    assert [item.id for item in baterias] == ["bench_2", "bench_1"]
