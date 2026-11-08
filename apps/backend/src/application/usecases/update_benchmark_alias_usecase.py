import logging

from src.domain.entities.benchmark.benchmark_session import BenchmarkSession
from src.domain.enums.benchmark_session_status_enum import BenchmarkSessionStatusEnum
from src.domain.errors.benchmark_session_not_finished_error import BenchmarkSessionNotFinishedError
from src.domain.errors.benchmark_session_not_found_error import BenchmarkSessionNotFoundError
from src.domain.interfaces.benchmark_session_repository_interface import IBenchmarkSessionRepository
from src.domain.interfaces.clock_interface import IClock


class UpdateBenchmarkAliasUseCase:
    """Define ou remove o alias de uma bateria já encerrada."""

    def __init__(self, repository: IBenchmarkSessionRepository, clock: IClock, logger: logging.Logger) -> None:
        self.repository = repository
        self.clock = clock
        self.logger = logger

    async def execute(self, benchmark_session_id: str, alias: str | None) -> BenchmarkSession:
        session = await self.repository.find_by_id(benchmark_session_id=benchmark_session_id)
        if session is None:
            raise BenchmarkSessionNotFoundError(benchmark_session_id=benchmark_session_id)
        if session.status is BenchmarkSessionStatusEnum.RUNNING:
            raise BenchmarkSessionNotFinishedError(benchmark_session_id=benchmark_session_id)
        session.set_alias(alias=alias, at=self.clock.now())
        await self.repository.update_alias(benchmark_session=session)
        self.logger.info("Alias da bateria '%s' atualizado", benchmark_session_id)
        return session
