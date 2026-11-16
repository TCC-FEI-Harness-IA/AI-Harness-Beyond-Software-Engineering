from abc import ABC, abstractmethod

from src.domain.entities.user import User


class IUserRepository(ABC):
    """Persistência das contas. A unicidade do e-mail é garantida pelo armazenamento."""

    @abstractmethod
    async def insert(self, user: User) -> None:
        """Insere a conta.

        Raises:
            EmailAlreadyRegisteredError: Quando o e-mail já existe.
        """
        raise NotImplementedError

    @abstractmethod
    async def find_by_email(self, email: str) -> User | None:
        """Busca pelo e-mail já normalizado."""
        raise NotImplementedError

    @abstractmethod
    async def find_by_id(self, user_id: str) -> User | None:
        """Busca pelo identificador."""
        raise NotImplementedError

    @abstractmethod
    async def update(self, user: User) -> None:
        """Substitui hash de senha e perfil de uma conta existente."""
        raise NotImplementedError
