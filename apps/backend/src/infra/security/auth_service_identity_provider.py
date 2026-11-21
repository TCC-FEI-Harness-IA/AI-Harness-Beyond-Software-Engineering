import logging
from datetime import datetime

import httpx

from src.domain.entities.auth.authenticated_user import AuthenticatedUser
from src.domain.errors.identity_service_unavailable_error import IdentityServiceUnavailableError
from src.domain.interfaces.identity_provider_interface import IIdentityProvider

_VERIFY_PATH = "/internal/sessions/verify"
_UNAUTHORIZED = 401


class AuthServiceIdentityProvider(IIdentityProvider):
    """Valida sessões no serviço de autenticação pela rota interna, com o segredo de serviço.

    Qualquer resposta diferente de "válida" ou "inválida" (erro, rede, corpo inesperado) vira
    `IdentityServiceUnavailableError`: a ausência de validação nunca libera uma operação privada.
    """

    def __init__(
        self,
        base_url: str,
        internal_token: str,
        logger: logging.Logger,
        timeout_seconds: float = 5,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        """Inicializa o adapter.

        Args:
            base_url: Endereço interno do serviço (ex.: `http://auth:8001`).
            internal_token: Segredo compartilhado com o serviço de autenticação.
            logger: Logger do módulo.
            timeout_seconds: Tempo máximo da verificação.
            transport: Transporte HTTP alternativo, para testes.
        """
        self.url = f"{base_url.rstrip('/')}{_VERIFY_PATH}"
        self.__internal_token = internal_token
        self.logger = logger
        self.timeout_seconds = timeout_seconds
        self.transport = transport

    async def verify(self, session_token: str) -> AuthenticatedUser | None:
        """Consulta o serviço de autenticação.

        Args:
            session_token: Valor do cookie de sessão.

        Returns:
            AuthenticatedUser | None: Identidade, ou `None` quando a sessão não vale.

        Raises:
            IdentityServiceUnavailableError: Quando o serviço não respondeu de forma válida.
        """
        if not session_token:
            return None
        try:
            async with httpx.AsyncClient(transport=self.transport, timeout=self.timeout_seconds) as client:
                response = await client.post(
                    self.url,
                    json={"token": session_token},
                    headers={"Authorization": f"Bearer {self.__internal_token}"},
                )
        except httpx.HTTPError as exc:
            self.logger.warning("Serviço de autenticação inacessível: %s", type(exc).__name__)
            raise IdentityServiceUnavailableError() from exc
        if response.status_code == _UNAUTHORIZED:
            return None
        if response.status_code != 200:
            self.logger.warning("Serviço de autenticação respondeu HTTP %s", response.status_code)
            raise IdentityServiceUnavailableError()
        try:
            body = response.json()
            return AuthenticatedUser(
                user_id=str(body["user_id"]),
                role=str(body["role"]),
                session_id=str(body["session_id"]),
                session_expires_at=datetime.fromisoformat(body["expires_at"]),
                csrf_token=str(body["csrf_token"]),
            )
        except (ValueError, KeyError, TypeError) as exc:
            raise IdentityServiceUnavailableError() from exc
