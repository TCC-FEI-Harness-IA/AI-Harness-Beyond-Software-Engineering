import asyncio
from collections.abc import Coroutine
from dataclasses import dataclass, field
from typing import Any

from fastapi import WebSocket

from src.domain.entities.auth.authenticated_user import AuthenticatedUser
from src.domain.errors.credential_invalid_error import CredentialInvalidError
from src.domain.errors.execution_limit_exceeded_error import ExecutionLimitExceededError
from src.domain.errors.execution_not_authorized_error import ExecutionNotAuthorizedError
from src.domain.errors.identity_service_unavailable_error import IdentityServiceUnavailableError
from src.domain.interfaces.execution_limiter_interface import IExecutionSlot
from src.domain.services.execution_authorization import ExecutionAuthorization
from src.infra.security.request_security import (
    LOGIN_REQUIRED,
    open_authorization,
    origin_allowed,
    resolve_identity,
    security_services,
)
from src.infra.security.security_services import SecurityServices

# Códigos de fechamento (faixa 4000–4999, de uso da aplicação) lidos pelo frontend.
WS_CLOSE_POLICY_VIOLATION = 1008
WS_CLOSE_UNAUTHENTICATED = 4401
WS_CLOSE_CREDENTIAL_REQUIRED = 4428
WS_CLOSE_RATE_LIMITED = 4429
WS_CLOSE_AUTH_UNAVAILABLE = 4503

_ERROR_FRAME_TYPE = "error"
_SESSION_ENDED = "A sessão de autenticação foi encerrada. Faça login novamente."
_REVALIDATION_UNAVAILABLE = "Não foi possível revalidar a sessão de autenticação; a execução foi interrompida."


@dataclass
class WebSocketExecution:
    """Execução LLM autorizada por WebSocket: identidade, credencial, vaga e revalidação periódica.

    Todo trabalho LLM da conexão roda por `run`, que revalida a sessão a cada
    `revalidation_interval_seconds`. Ao detectar expiração, logout ou indisponibilidade da
    validação, a autorização é revogada (nenhuma chamada nova sai) e o trabalho é cancelado,
    seguindo o mesmo caminho de encerramento da desconexão do cliente.
    """

    websocket: WebSocket
    security: SecurityServices
    identity: AuthenticatedUser
    authorization: ExecutionAuthorization
    session_token: str = field(repr=False)
    slot: IExecutionSlot
    revoked_reason: str | None = None

    @property
    def owner_id(self) -> str:
        """Conta dona da execução."""
        return self.identity.user_id

    async def run(self, work: Coroutine[Any, Any, None]) -> bool:
        """Executa o trabalho sob vigilância da sessão.

        Args:
            work: Corrotina que consome o fluxo e envia os frames.

        Returns:
            bool: `True` quando o trabalho terminou; `False` quando foi interrompido por revogação.

        Raises:
            Exception: O que o próprio trabalho levantar (ex.: `WebSocketDisconnect`).
        """
        task = asyncio.ensure_future(work)
        watcher = asyncio.ensure_future(self.__watch())
        try:
            await asyncio.wait({task, watcher}, return_when=asyncio.FIRST_COMPLETED)
        finally:
            watcher.cancel()
        if task.done():
            try:
                task.result()
            except ExecutionNotAuthorizedError as exc:
                self.revoked_reason = str(exc)
                self.authorization.revoke(str(exc))
                return False
            return self.authorization.is_active
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        return False

    async def close_revoked(self) -> None:
        """Informa a interrupção ao cliente e fecha com 4401."""
        await reject(self.websocket, WS_CLOSE_UNAUTHENTICATED, self.revoked_reason or _SESSION_ENDED)

    def release(self) -> None:
        """Libera a vaga do limitador."""
        self.slot.release()

    async def __watch(self) -> None:
        """Revalida a sessão até ela deixar de valer; então revoga a autorização e termina."""
        interval = self.security.settings.revalidation_interval_seconds
        while True:
            await asyncio.sleep(interval)
            reason = await self.__check()
            if reason is not None:
                self.revoked_reason = reason
                self.authorization.revoke(reason)
                return

    async def __check(self) -> str | None:
        if not self.authorization.is_active:
            return _SESSION_ENDED
        try:
            identity = await self.security.identity_provider.verify(session_token=self.session_token)
        except IdentityServiceUnavailableError:
            return _REVALIDATION_UNAVAILABLE
        if identity is None or identity.session_id != self.identity.session_id:
            return _SESSION_ENDED
        return None


async def reject(websocket: WebSocket, code: int, message: str) -> None:
    """Envia um frame de erro e fecha a conexão com o código informado."""
    await websocket.send_json({"type": _ERROR_FRAME_TYPE, "content": message})
    await websocket.close(code=code)


async def open_websocket_execution(websocket: WebSocket) -> WebSocketExecution | None:
    """Autoriza uma conexão WebSocket antes de qualquer trabalho LLM.

    Ordem: origem (antes do aceite: um handshake de outra origem recebe 403), sessão, credencial
    e limites. Tokens e credenciais nunca vêm na URL: só nos cookies.

    Returns:
        WebSocketExecution | None: Execução autorizada, ou `None` quando a conexão foi recusada e fechada.
    """
    security = security_services(websocket)
    if not origin_allowed(websocket, security, required=True):
        await websocket.close(code=WS_CLOSE_POLICY_VIOLATION)
        return None
    await websocket.accept()
    token = websocket.cookies.get(security.settings.session_cookie_name, "")
    try:
        identity = await resolve_identity(websocket, security)
    except IdentityServiceUnavailableError as exc:
        await reject(websocket, WS_CLOSE_AUTH_UNAVAILABLE, str(exc))
        return None
    if identity is None:
        await reject(websocket, WS_CLOSE_UNAUTHENTICATED, LOGIN_REQUIRED)
        return None
    try:
        authorization = open_authorization(websocket, security, identity)
    except CredentialInvalidError as exc:
        await reject(websocket, WS_CLOSE_CREDENTIAL_REQUIRED, str(exc))
        return None
    try:
        slot = security.execution_limiter.acquire(identity.user_id)
    except ExecutionLimitExceededError as exc:
        await reject(websocket, WS_CLOSE_RATE_LIMITED, str(exc))
        return None
    return WebSocketExecution(
        websocket=websocket,
        security=security,
        identity=identity,
        authorization=authorization,
        session_token=token,
        slot=slot,
    )
