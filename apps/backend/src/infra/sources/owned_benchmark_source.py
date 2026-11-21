import logging

from src.domain.entities.publication.source_battery import SourceBattery
from src.domain.entities.session.session import Session
from src.domain.interfaces.benchmark_session_repository_interface import IBenchmarkSessionRepository
from src.domain.interfaces.benchmark_source_interface import IBenchmarkSource
from src.domain.interfaces.session_repository_interface import ISessionRepository


class OwnedBenchmarkSource(IBenchmarkSource):
    """Histórico pessoal de uma conta específica, pelos repositórios escopados a ela (somente leitura)."""

    def __init__(
        self,
        benchmark_repository: IBenchmarkSessionRepository,
        session_repository: ISessionRepository,
        description: str,
        logger: logging.Logger,
    ) -> None:
        """Inicializa a origem."""
        self.benchmark_repository = benchmark_repository
        self.session_repository = session_repository
        self.description = description
        self.logger = logger

    def describe(self) -> str:
        """Conta e armazenamento lidos."""
        return self.description

    async def list_batteries(self) -> list[SourceBattery]:
        """Baterias da conta."""
        return [
            SourceBattery(battery_id=battery.id, battery=battery)
            for battery in await self.benchmark_repository.list_all()
        ]

    async def find_session(self, session_id: str) -> Session | None:
        """Sessão da conta."""
        return await self.session_repository.find_by_id(session_id=session_id)
