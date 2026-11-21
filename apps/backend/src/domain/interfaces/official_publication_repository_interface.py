from abc import ABC, abstractmethod
from datetime import datetime

from src.domain.entities.publication.official_publication import OfficialPublication
from src.domain.entities.session.session import Session


class IOfficialPublicationRepository(ABC):
    """Armazenamento das publicações oficiais, separado dos dados pessoais."""

    @abstractmethod
    async def create(self, publication: OfficialPublication, sessions: list[Session]) -> None:
        """Grava a publicação e as cópias das sessões filhas (sessões primeiro, publicação por último)."""
        raise NotImplementedError

    @abstractmethod
    async def find(self, publication_id: str) -> OfficialPublication | None:
        """Busca uma publicação."""
        raise NotImplementedError

    @abstractmethod
    async def list_all(self) -> list[OfficialPublication]:
        """Todas as publicações, da mais recente para a mais antiga."""
        raise NotImplementedError

    @abstractmethod
    async def find_session(self, publication_id: str, session_id: str) -> Session | None:
        """Cópia de uma sessão filha guardada com a publicação."""
        raise NotImplementedError

    @abstractmethod
    async def list_sessions(self, publication_id: str) -> list[Session]:
        """Todas as cópias de sessões da publicação."""
        raise NotImplementedError

    @abstractmethod
    async def mark_superseded(self, publication_id: str, superseded_by: str, at: datetime) -> None:
        """Marca a publicação como substituída, sem apagar nada."""
        raise NotImplementedError
