from abc import ABC, abstractmethod
from datetime import datetime

from src.domain.entities.auth_session import AuthSession


class IAuthSessionRepository(ABC):
    """Persistência das sessões de autenticação, indexadas pelo resumo do token."""

    @abstractmethod
    async def insert(self, session: AuthSession) -> None:
        """Insere a sessão."""
        raise NotImplementedError

    @abstractmethod
    async def find_by_token_hash(self, token_hash: str) -> AuthSession | None:
        """Busca a sessão pelo resumo do token."""
        raise NotImplementedError

    @abstractmethod
    async def revoke(self, token_hash: str, revoked_at: datetime) -> bool:
        """Revoga a sessão; devolve `False` se ela não existia ou já estava revogada."""
        raise NotImplementedError
