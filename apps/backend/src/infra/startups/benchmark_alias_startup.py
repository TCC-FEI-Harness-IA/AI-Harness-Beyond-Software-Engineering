from typing import Any

from src.application.usecases.update_benchmark_alias_usecase import UpdateBenchmarkAliasUseCase
from src.infra.adapters.clock_adapter import ClockAdapter
from src.infra.config.settings import Settings
from src.infra.mappers.benchmark_session_document_mapper import BenchmarkSessionDocumentMapper
from src.infra.repositories.benchmark_session_repository_factory import BenchmarkSessionRepositoryFactory


class BenchmarkAliasStartup:
    """Composition root da edição de aliases das baterias de benchmark."""

    def __init__(self) -> None:
        settings = Settings()
        self.document_mapper = BenchmarkSessionDocumentMapper()
        self.update_use_case = UpdateBenchmarkAliasUseCase(
            repository=BenchmarkSessionRepositoryFactory(settings=settings, mapper=self.document_mapper).create(),
            clock=ClockAdapter(),
            logger=settings.logger(module_file=__file__),
        )

    async def update_alias(self, benchmark_session_id: str, alias: str | None) -> dict[str, Any]:
        session = await self.update_use_case.execute(benchmark_session_id=benchmark_session_id, alias=alias)
        return self.document_mapper.to_document(benchmark_session=session)
