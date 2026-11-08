import logging

from src.domain.entities.benchmark.benchmark_session import BenchmarkSession
from src.domain.interfaces.benchmark_session_repository_interface import IBenchmarkSessionRepository


class ListBenchmarkSessionsUseCase:
    """Listagem das baterias de benchmark persistidas."""

    def __init__(self, repository: IBenchmarkSessionRepository, logger: logging.Logger) -> None:
        """Inicializa o caso de uso.

        Args:
            repository: Repositório de persistência das baterias.
            logger: Logger do módulo.
        """
        self.repository: IBenchmarkSessionRepository = repository
        self.logger = logger

    async def execute(self) -> list[BenchmarkSession]:
        """Lista as baterias persistidas.

        Returns:
            list[BenchmarkSession]: Baterias, da mais recente para a mais antiga.
        """
        self.logger.info("Listando as baterias de benchmark")
        return await self.repository.list_all()
