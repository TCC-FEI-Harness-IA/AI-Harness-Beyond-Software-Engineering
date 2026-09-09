import copy

from src.domain.entities.session.session import Session
from src.domain.interfaces.session_repository_interface import ISessionRepository


class InMemorySessionRepository(ISessionRepository):
    """Dublê de `ISessionRepository` apoiado em dicionário, contando as escritas.

    Guarda uma cópia profunda da sessão a cada `save`, como faria uma persistência
    real, para que mutações posteriores do agregado não alterem o que foi gravado.
    """

    def __init__(self) -> None:
        """Prepara o armazenamento em memória e os contadores de chamada."""
        self.sessions: dict[str, Session] = {}
        self.save_calls: list[str] = []

    async def save(self, session: Session) -> None:
        """Guarda uma cópia da sessão e registra a chamada."""
        self.sessions[session.id] = copy.deepcopy(session)
        self.save_calls.append(session.id)

    async def find_by_id(self, session_id: str) -> Session | None:
        """Devolve a sessão guardada, ou `None` quando não existe."""
        return self.sessions.get(session_id)

    async def list_ids(self) -> list[str]:
        """Devolve os identificadores guardados em ordem alfabética."""
        return sorted(self.sessions)

    async def delete(self, session_id: str) -> bool:
        """Remove a sessão guardada, informando se ela existia."""
        return self.sessions.pop(session_id, None) is not None
