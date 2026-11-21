from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response

from src.domain.entities.auth_session import AuthSession
from src.domain.entities.user import User
from src.domain.errors.email_already_registered_error import EmailAlreadyRegisteredError
from src.domain.errors.invalid_credentials_error import InvalidCredentialsError
from src.domain.errors.invalid_registration_error import InvalidRegistrationError
from src.domain.errors.session_invalid_error import SessionInvalidError
from src.domain.errors.too_many_attempts_error import TooManyAttemptsError
from src.infra.routes.dtos.auth_dtos import CredentialsInputDTO
from src.infra.routes.http_security import (
    NO_STORE,
    clear_auth_cookies,
    client_key,
    ensure_allowed_origin,
    set_session_cookie,
    tokens_match,
)
from src.infra.startups.auth_container import AuthContainer

router = APIRouter(prefix="/auth", tags=["auth"])


def _container(request: Request) -> AuthContainer:
    return request.app.state.container


def _session_view(user: User, session: AuthSession) -> dict[str, Any]:
    """Visão da sessão para o próprio navegador: sem token e sem hash de senha."""
    return {
        "user": {"id": user.id, "email": user.email, "role": user.role.value},
        "session": {"expires_at": session.expires_at.isoformat()},
        "csrf_token": session.csrf_token,
    }


@router.post("/register", status_code=201)
async def register(payload: CredentialsInputDTO, request: Request, response: Response) -> dict[str, Any]:
    """Cadastra uma conta comum. Não abre sessão: o cliente faz login em seguida."""
    container = _container(request)
    ensure_allowed_origin(request, container.settings)
    response.headers.update(NO_STORE)
    try:
        user = await container.register_user.execute(email=payload.email, password=payload.password)
    except InvalidRegistrationError as exc:
        raise HTTPException(status_code=400, detail=str(exc), headers=NO_STORE) from exc
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(status_code=409, detail=str(exc), headers=NO_STORE) from exc
    return {"user": {"id": user.id, "email": user.email, "role": user.role.value}}


@router.post("/login")
async def login(payload: CredentialsInputDTO, request: Request, response: Response) -> dict[str, Any]:
    """Autentica e grava o cookie de sessão."""
    container = _container(request)
    settings = container.settings
    ensure_allowed_origin(request, settings)
    try:
        result = await container.login.execute(
            email=payload.email, password=payload.password, client_key=client_key(request, settings)
        )
    except TooManyAttemptsError as exc:
        raise HTTPException(
            status_code=429, detail=str(exc), headers={**NO_STORE, "Retry-After": str(exc.retry_after_seconds)}
        ) from exc
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=401, detail=str(exc), headers=NO_STORE) from exc
    response.headers.update(NO_STORE)
    set_session_cookie(
        response, settings, token=result.token, expires_at=result.session.expires_at, now=container.clock.now()
    )
    return _session_view(result.user, result.session)


@router.get("/me")
async def me(request: Request, response: Response) -> dict[str, Any]:
    """Conta e sessão atuais, com o token anti-CSRF a enviar em `X-CSRF-Token`."""
    container = _container(request)
    token = request.cookies.get(container.settings.session_cookie_name, "")
    try:
        current = await container.resolve_session.execute(token=token)
    except SessionInvalidError as exc:
        raise HTTPException(status_code=401, detail=str(exc), headers=NO_STORE) from exc
    response.headers.update(NO_STORE)
    return _session_view(current.user, current.session)


@router.post("/logout", status_code=204)
async def logout(request: Request) -> Response:
    """Revoga a sessão e remove os cookies de sessão e de credencial.

    Com uma sessão válida, exige o token anti-CSRF; sem sessão válida, apenas limpa os cookies.
    """
    container = _container(request)
    settings = container.settings
    ensure_allowed_origin(request, settings)
    token = request.cookies.get(settings.session_cookie_name, "")
    try:
        current = await container.resolve_session.execute(token=token)
    except SessionInvalidError:
        current = None
    if current is not None:
        if not tokens_match(current.session.csrf_token, request.headers.get("x-csrf-token")):
            raise HTTPException(status_code=403, detail="Token anti-CSRF ausente ou inválido.", headers=NO_STORE)
        await container.logout.execute(token=token)
    response = Response(status_code=204, headers=NO_STORE)
    clear_auth_cookies(response, settings)
    return response
