import logging
from datetime import timedelta

import pytest

from src.application.usecases.update_benchmark_alias_usecase import UpdateBenchmarkAliasUseCase
from src.domain.enums.benchmark_session_status_enum import BenchmarkSessionStatusEnum
from src.domain.errors.benchmark_session_not_finished_error import BenchmarkSessionNotFinishedError
from src.domain.errors.benchmark_session_not_found_error import BenchmarkSessionNotFoundError
from tests.doubles.benchmark_factories import CRIADO_EM, bateria
from tests.doubles.fake_clock import FakeClock
from tests.doubles.in_memory_benchmark_session_repository import InMemoryBenchmarkSessionRepository


def _use_case(repository: InMemoryBenchmarkSessionRepository) -> UpdateBenchmarkAliasUseCase:
    return UpdateBenchmarkAliasUseCase(
        repository=repository,
        clock=FakeClock(now_values=[CRIADO_EM + timedelta(days=1)]),
        logger=logging.getLogger("teste"),
    )


@pytest.mark.parametrize("status", [
    BenchmarkSessionStatusEnum.COMPLETED, BenchmarkSessionStatusEnum.FAILED, BenchmarkSessionStatusEnum.INTERRUPTED,
])
async def test_define_edita_e_remove_alias_sem_alterar_resultados(status: BenchmarkSessionStatusEnum) -> None:
    repository = InMemoryBenchmarkSessionRepository()
    session = bateria("Q1", status=status)
    await repository.save(session)
    use_case = _use_case(repository)

    for alias, expected in [("  Comparação GPT  ", "Comparação GPT"), ("Nova rodada", "Nova rodada"),
                            ("   ", None), ("x" * 120, "x" * 120), (None, None)]:
        updated = await use_case.execute("bench_1", alias)
        stored = await repository.find_by_id("bench_1")
        assert stored == updated
        assert stored is not None
        assert stored.alias == expected
        assert stored.updated_at == CRIADO_EM + timedelta(days=1)
        assert stored.questions == session.questions
        assert stored.status == session.status
        assert stored.finished_at == session.finished_at
        assert stored.wall_time_ms == session.wall_time_ms


async def test_nao_altera_bateria_em_execucao_ou_inexistente() -> None:
    repository = InMemoryBenchmarkSessionRepository()
    await repository.save(bateria())
    use_case = _use_case(repository)

    with pytest.raises(BenchmarkSessionNotFinishedError):
        await use_case.execute("bench_1", "alias")
    with pytest.raises(BenchmarkSessionNotFoundError):
        await use_case.execute("bench_9", "alias")
    assert repository.save_attempts == 1


async def test_recusa_alias_longo_sem_persistir() -> None:
    repository = InMemoryBenchmarkSessionRepository()
    await repository.save(bateria(status=BenchmarkSessionStatusEnum.COMPLETED))

    with pytest.raises(ValueError, match="120 caracteres"):
        await _use_case(repository).execute("bench_1", "x" * 121)
    assert repository.save_attempts == 1
