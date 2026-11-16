from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from src.domain.entities.auth.authenticated_user import AuthenticatedUser
from src.domain.errors.credential_invalid_error import CredentialInvalidError
from src.domain.errors.credential_rejected_error import CredentialRejectedError
from src.domain.errors.llm_key_validation_unavailable_error import LLMKeyValidationUnavailableError
from src.infra.security.request_security import current_identity, security_services, writer_identity
from src.infra.security.security_services import SecurityServices

router = APIRouter(prefix="/credentials", tags=["credentials"])

_COOKIE_PATH = "/v1"
_MAX_KEY_CHARS = 512
_MISSING = "missing"
_VALID = "valid"
_INVALID = "invalid"


def _status(status: str, expires_at: datetime | None = None) -> dict[str, Any]:
    """Estado da credencial para a interface: nunca o conteúdo."""
    return {
        "status": status,
        "available": status == _VALID,
        "expires_at": expires_at.isoformat() if expires_at is not None else None,
    }


def _delete_cookie(response: Response, security: SecurityServices) -> None:
    response.delete_cookie(
        key=security.settings.credential_cookie_name,
        path=_COOKIE_PATH,
        secure=security.settings.cookie_secure,
        httponly=True,
        samesite="strict",
    )


async def _read_api_key(request: Request) -> str:
    """Lê `api_key` do corpo sem devolver o valor em erros de validação."""
    try:
        body = await request.json()
    except ValueError:
        body = None
    api_key = body.get("api_key") if isinstance(body, dict) else None
    if not isinstance(api_key, str) or not api_key.strip() or len(api_key) > _MAX_KEY_CHARS:
        raise HTTPException(status_code=422, detail="Envie a chave OpenRouter no campo api_key.")
    return api_key.strip()


@router.get("/openrouter")
async def describe_credential(
    request: Request, response: Response, identity: AuthenticatedUser = Depends(current_identity)
) -> dict[str, Any]:
    """Informa se há credencial utilizável nesta sessão; um cookie que não vale mais é removido."""
    security = security_services(request)
    value = request.cookies.get(security.settings.credential_cookie_name)
    if not value:
        return _status(_MISSING)
    try:
        credential = security.credential_codec.open(value=value, identity=identity)
    except CredentialInvalidError:
        _delete_cookie(response, security)
        return _status(_INVALID)
    return _status(_VALID, credential.expires_at)


@router.put("/openrouter")
async def store_credential(
    request: Request, response: Response, identity: AuthenticatedUser = Depends(writer_identity)
) -> dict[str, Any]:
    """Valida a chave com a OpenRouter e a devolve cifrada num cookie HttpOnly; nada é persistido."""
    security = security_services(request)
    api_key = await _read_api_key(request)
    try:
        await security.key_validator.validate(api_key=api_key)
    except CredentialRejectedError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except LLMKeyValidationUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    sealed = security.credential_codec.seal(api_key=api_key, identity=identity)
    response.set_cookie(
        key=security.settings.credential_cookie_name,
        value=sealed.value,
        max_age=max(0, int((sealed.expires_at - security.clock.now()).total_seconds())),
        expires=sealed.expires_at,
        path=_COOKIE_PATH,
        secure=security.settings.cookie_secure,
        httponly=True,
        samesite="strict",
    )
    return _status(_VALID, sealed.expires_at)


@router.delete("/openrouter", status_code=204)
async def delete_credential(request: Request, _: AuthenticatedUser = Depends(writer_identity)) -> Response:
    """Remove a credencial desta sessão."""
    response = Response(status_code=204)
    _delete_cookie(response, security_services(request))
    return response
