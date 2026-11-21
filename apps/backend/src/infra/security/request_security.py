import hmac
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request
from starlette.requests import HTTPConnection

from src.domain.entities.auth.authenticated_user import AuthenticatedUser
from src.domain.errors.credential_invalid_error import CredentialInvalidError
from src.domain.errors.execution_not_authorized_error import ExecutionNotAuthorizedError
from src.domain.errors.identity_service_unavailable_error import IdentityServiceUnavailableError
from src.domain.services.execution_authorization import ExecutionAuthorization
from src.infra.security.security_services import SecurityServices

LOGIN_REQUIRED = "Faça login para continuar."
CREDENTIAL_REQUIRED = "Configure a sua chave OpenRouter para executar chamadas LLM."


@dataclass(frozen=True)
class RequestExecution:
    """Identidade, autorização LLM e token de sessão de uma requisição que vai chamar o modelo."""

    identity: AuthenticatedUser
    authorization: ExecutionAuthorization


def security_services(connection: HTTPConnection) -> SecurityServices:
    """Serviços de segurança do processo."""
    return connection.app.state.security


def origin_allowed(connection: HTTPConnection, security: SecurityServices, required: bool) -> bool:
    """Confere o header `Origin` com as origens públicas.

    Args:
        connection: Requisição HTTP ou WebSocket.
        security: Serviços de segurança.
        required: Exige o header (WebSockets) em vez de só recusar origens desconhecidas.
    """
    origin = connection.headers.get("origin")
    if origin is None:
        return not required
    return origin.rstrip("/") in security.settings.public_origins


def secrets_match(expected: str, received: str | None) -> bool:
    """Comparação em tempo constante."""
    return received is not None and hmac.compare_digest(expected.encode(), received.encode())


async def resolve_identity(connection: HTTPConnection, security: SecurityServices) -> AuthenticatedUser | None:
    """Valida o cookie de sessão no serviço de autenticação; headers de identidade do cliente são ignorados.

    Raises:
        IdentityServiceUnavailableError: Quando a validação não pôde ser feita.
    """
    token = connection.cookies.get(security.settings.session_cookie_name, "")
    return await security.identity_provider.verify(session_token=token)


async def current_identity(request: Request) -> AuthenticatedUser:
    """Dependência das rotas privadas: exige sessão válida.

    Raises:
        HTTPException: 401 sem sessão válida; 503 quando a autenticação está indisponível.
    """
    security = security_services(request)
    try:
        identity = await resolve_identity(request, security)
    except IdentityServiceUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if identity is None:
        raise HTTPException(status_code=401, detail=LOGIN_REQUIRED)
    return identity


async def writer_identity(
    request: Request, identity: AuthenticatedUser = Depends(current_identity)
) -> AuthenticatedUser:
    """Dependência das rotas que alteram estado: além da sessão, exige origem permitida e o token anti-CSRF.

    Raises:
        HTTPException: 403 quando a origem ou o token anti-CSRF não confere.
    """
    security = security_services(request)
    if not origin_allowed(request, security, required=False):
        raise HTTPException(status_code=403, detail="Origem não permitida.")
    if not secrets_match(identity.csrf_token, request.headers.get("x-csrf-token")):
        raise HTTPException(status_code=403, detail="Token anti-CSRF ausente ou inválido.")
    return identity


def open_authorization(
    connection: HTTPConnection, security: SecurityServices, identity: AuthenticatedUser
) -> ExecutionAuthorization:
    """Decifra o cookie da credencial e monta a autorização da execução.

    Raises:
        CredentialInvalidError: Cookie ausente, adulterado, expirado ou de outra conta/sessão.
    """
    value = connection.cookies.get(security.settings.credential_cookie_name)
    if not value:
        raise CredentialInvalidError(CREDENTIAL_REQUIRED)
    credential = security.credential_codec.open(value=value, identity=identity)
    token = connection.cookies.get(security.settings.session_cookie_name, "")

    async def validate_session() -> None:
        try:
            current = await security.identity_provider.verify(session_token=token)
        except IdentityServiceUnavailableError as exc:
            raise ExecutionNotAuthorizedError("Não foi possível revalidar a sessão de autenticação.") from exc
        if current is None or current.user_id != identity.user_id or current.session_id != identity.session_id:
            raise ExecutionNotAuthorizedError("A sessão de autenticação foi encerrada. Faça login novamente.")

    return ExecutionAuthorization(
        identity=identity, credential=credential, clock=security.clock, session_validator=validate_session
    )


async def request_execution(
    request: Request, identity: AuthenticatedUser = Depends(writer_identity)
) -> RequestExecution:
    """Dependência das rotas HTTP que chamam o LLM: sessão, CSRF e credencial válidos.

    Raises:
        HTTPException: 428 quando a credencial falta ou não vale para esta sessão.
    """
    security = security_services(request)
    try:
        authorization = open_authorization(request, security, identity)
    except CredentialInvalidError as exc:
        raise HTTPException(status_code=428, detail=str(exc)) from exc
    return RequestExecution(identity=identity, authorization=authorization)
