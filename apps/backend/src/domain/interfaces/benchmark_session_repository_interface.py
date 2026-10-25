from abc import ABC, abstractmethod

from src.domain.entities.benchmark.benchmark_session import BenchmarkSession


class IBenchmarkSessionRepository(ABC):
    """Contrato de persistência das baterias de benchmark."""

    @abstractmethod
    async def save(self, benchmark_session: BenchmarkSession) -> None:
        """Persiste (insere ou substitui) a bateria inteira.

        Args:
            benchmark_session: Bateria a ser persistida.
        """
        raise NotImplementedError

    @abstractmethod
    async def find_by_id(self, benchmark_session_id: str) -> BenchmarkSession | None:
        """Busca uma bateria pelo identificador.

        Args:
            benchmark_session_id: Identificador da bateria procurada.

        Returns:
            BenchmarkSession | None: Bateria encontrada, ou `None` quando não existe.
        """
        raise NotImplementedError

    @abstractmethod
    async def list_all(self) -> list[BenchmarkSession]:
        """Lista todas as baterias persistidas.

        Returns:
            list[BenchmarkSession]: Baterias, da mais recente para a mais antiga.
        """
        raise NotImplementedError
