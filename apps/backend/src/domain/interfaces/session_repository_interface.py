from abc import ABC, abstractmethod

from src.domain.entities.session.session import Session


class ISessionRepository(ABC):
    """Contrato de persistência de sessões."""

    @abstractmethod
    async def save(self, session: Session) -> None:
        """Persiste (insere ou substitui) a sessão inteira.

        Args:
            session: Sessão a ser persistida.
        """
        raise NotImplementedError

    @abstractmethod
    async def find_by_id(self, session_id: str) -> Session | None:
        """Busca uma sessão pelo identificador.

        Args:
            session_id: Identificador da sessão procurada.

        Returns:
            Session | None: Sessão encontrada, ou `None` quando não existe.
        """
        raise NotImplementedError

    @abstractmethod
    async def list_ids(self) -> list[str]:
        """Lista os identificadores de todas as sessões persistidas.

        Returns:
            list[str]: Identificadores de sessão.
        """
        raise NotImplementedError

    @abstractmethod
    async def delete(self, session_id: str) -> bool:
        """Remove uma sessão persistida.

        Args:
            session_id: Identificador da sessão a remover.

        Returns:
            bool: `True` quando a sessão existia e foi removida.
        """
        raise NotImplementedError
