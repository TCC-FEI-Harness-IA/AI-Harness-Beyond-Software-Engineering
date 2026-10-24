import copy

from src.domain.entities.session.session import Session
from src.domain.enums.session_status_enum import SessionStatusEnum
from src.domain.interfaces.session_repository_interface import ISessionRepository


class InMemorySessionRepository(ISessionRepository):
    """Dublê de `ISessionRepository` apoiado em dicionário, contando as escritas.

    Guarda uma cópia profunda da sessão a cada `save`, como faria uma persistência
    real, para que mutações posteriores do agregado não alterem o que foi gravado.
    """

    def __init__(
        self,
        failing_saves: dict[SessionStatusEnum, int] | None = None,
        failing_save_calls: set[int] | None = None,
    ) -> None:
        """Prepara o armazenamento em memória e os contadores de chamada.

        Args:
            failing_saves: Quantas gravações consecutivas falham, por status da sessão gravada.
                Simula uma indisponibilidade transitória da persistência apenas naquela etapa.
            failing_save_calls: Números (a partir de 1) das tentativas de gravação que falham,
                contados sobre todas as tentativas, inclusive as que falham.
        """
        self.sessions: dict[str, Session] = {}
        self.save_calls: list[str] = []
        self.failing_saves: dict[SessionStatusEnum, int] = dict(failing_saves or {})
        self.failing_save_calls: set[int] = set(failing_save_calls or ())
        self.save_attempts = 0

    async def save(self, session: Session) -> None:
        """Guarda uma cópia da sessão e registra a chamada.

        Raises:
            OSError: Enquanto restarem falhas programadas para o status da sessão.
        """
        self.save_attempts += 1
        if self.save_attempts in self.failing_save_calls:
            raise OSError(f"persistência indisponível (gravação {self.save_attempts})")
        if self.failing_saves.get(session.status, 0) > 0:
            self.failing_saves[session.status] -= 1
            raise OSError(f"persistência indisponível (gravação {self.save_attempts})")
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
