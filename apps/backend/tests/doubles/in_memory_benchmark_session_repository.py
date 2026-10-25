import copy

from src.domain.entities.benchmark.benchmark_session import BenchmarkSession
from src.domain.interfaces.benchmark_session_repository_interface import IBenchmarkSessionRepository


class InMemoryBenchmarkSessionRepository(IBenchmarkSessionRepository):
    """Dublê de `IBenchmarkSessionRepository` em memória, com falhas programáveis.

    Guarda uma cópia profunda a cada `save`, como faria uma persistência real.
    """

    def __init__(self, failing_save_calls: set[int] | None = None) -> None:
        """Prepara o armazenamento.

        Args:
            failing_save_calls: Números (a partir de 1) das tentativas de gravação que falham.
        """
        self.sessions: dict[str, BenchmarkSession] = {}
        self.saved: list[BenchmarkSession] = []
        self.failing_save_calls: set[int] = set(failing_save_calls or ())
        self.save_attempts = 0

    async def save(self, benchmark_session: BenchmarkSession) -> None:
        """Guarda uma cópia da bateria.

        Raises:
            OSError: Nas tentativas programadas para falhar.
        """
        self.save_attempts += 1
        if self.save_attempts in self.failing_save_calls:
            raise OSError(f"persistência indisponível (gravação {self.save_attempts})")
        snapshot = copy.deepcopy(benchmark_session)
        self.sessions[benchmark_session.id] = snapshot
        self.saved.append(snapshot)

    async def find_by_id(self, benchmark_session_id: str) -> BenchmarkSession | None:
        """Devolve a bateria guardada, ou `None`."""
        return self.sessions.get(benchmark_session_id)

    async def list_all(self) -> list[BenchmarkSession]:
        """Devolve as baterias, da mais recente para a mais antiga."""
        return sorted(self.sessions.values(), key=lambda item: item.created_at, reverse=True)
