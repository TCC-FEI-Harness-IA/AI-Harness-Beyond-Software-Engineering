from abc import ABC, abstractmethod

from src.domain.entities.publication.source_battery import SourceBattery
from src.domain.entities.session.session import Session


class IBenchmarkSource(ABC):
    """Origem pessoal explícita das baterias candidatas a resultado oficial (somente leitura)."""

    @abstractmethod
    def describe(self) -> str:
        """Descreve a origem (armazenamento, caminhos ou coleções) para o relatório."""
        raise NotImplementedError

    @abstractmethod
    async def list_batteries(self) -> list[SourceBattery]:
        """Todas as baterias da origem, inclusive as ilegíveis."""
        raise NotImplementedError

    @abstractmethod
    async def find_session(self, session_id: str) -> Session | None:
        """Sessão filha da origem.

        Raises:
            ValueError: Quando o documento existe mas é inválido.
        """
        raise NotImplementedError
