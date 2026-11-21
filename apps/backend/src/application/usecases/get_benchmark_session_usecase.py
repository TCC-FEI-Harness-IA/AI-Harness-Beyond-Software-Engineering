import logging

from src.domain.entities.benchmark.benchmark_session import BenchmarkSession
from src.domain.errors.benchmark_session_not_found_error import BenchmarkSessionNotFoundError
from src.domain.interfaces.benchmark_session_repository_interface import IBenchmarkSessionRepository


class GetBenchmarkSessionUseCase:
    """Consulta de uma bateria de benchmark persistida pelo identificador."""

    def __init__(self, repository: IBenchmarkSessionRepository, logger: logging.Logger) -> None:
        """Inicializa o caso de uso.

        Args:
            repository: Repositório de persistência das baterias.
            logger: Logger do módulo.
        """
        self.repository: IBenchmarkSessionRepository = repository
        self.logger = logger

    async def execute(self, benchmark_session_id: str) -> BenchmarkSession:
        """Busca a bateria pelo identificador informado.

        Args:
            benchmark_session_id: Identificador da bateria procurada.

        Returns:
            BenchmarkSession: Bateria encontrada.

        Raises:
            BenchmarkSessionNotFoundError: Quando a bateria não existe.
        """
        self.logger.info("Consultando a bateria '%s'", benchmark_session_id)
        benchmark_session = await self.repository.find_by_id(benchmark_session_id=benchmark_session_id)
        if benchmark_session is None:
            raise BenchmarkSessionNotFoundError(benchmark_session_id=benchmark_session_id)
        return benchmark_session
