from abc import ABC, abstractmethod

from src.domain.entities.auth.authenticated_user import AuthenticatedUser


class IIdentityProvider(ABC):
    """Valida o token de sessão de um cookie junto ao serviço de autenticação."""

    @abstractmethod
    async def verify(self, session_token: str) -> AuthenticatedUser | None:
        """Devolve a identidade da sessão, ou `None` quando ela não vale.

        Raises:
            IdentityServiceUnavailableError: Quando o serviço não pôde responder (falha fechada).
        """
        raise NotImplementedError
