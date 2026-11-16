import hmac
from datetime import datetime

from fastapi import HTTPException, Request, Response

from src.infra.config.settings import Settings

_CREDENTIAL_COOKIE_PATH = "/v1"
NO_STORE = {"Cache-Control": "no-store"}


def ensure_allowed_origin(request: Request, settings: Settings) -> None:
    """Recusa requisições de navegador vindas de outra origem (defesa contra CSRF de login).

    Clientes que não são navegador não enviam `Origin` e não são vetores de CSRF.

    Raises:
        HTTPException: 403 quando `Origin` existe e não pertence às origens públicas.
    """
    origin = request.headers.get("origin")
    if origin is not None and origin.rstrip("/") not in settings.public_origins:
        raise HTTPException(status_code=403, detail="Origem não permitida.", headers=NO_STORE)


def tokens_match(expected: str, received: str | None) -> bool:
    """Comparação em tempo constante de segredos."""
    return received is not None and hmac.compare_digest(expected.encode(), received.encode())


def client_key(request: Request, settings: Settings) -> str:
    """Chave do cliente para o limite de tentativas: `X-Real-IP` do proxy confiável, ou o par TCP."""
    forwarded = request.headers.get("x-real-ip") if settings.trust_proxy_headers else None
    host = forwarded or (request.client.host if request.client else "desconhecido")
    return f"ip:{host}"


def set_session_cookie(response: Response, settings: Settings, token: str, expires_at: datetime, now: datetime) -> None:
    """Grava o cookie de sessão: HttpOnly, SameSite=Lax, `Secure` em produção, válido até o fim absoluto."""
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=max(0, int((expires_at - now).total_seconds())),
        expires=expires_at,
        path="/",
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax",
    )


def clear_auth_cookies(response: Response, settings: Settings) -> None:
    """Remove o cookie de sessão e o da credencial LLM (que vive sob `/v1`)."""
    response.delete_cookie(
        key=settings.session_cookie_name, path="/", secure=settings.cookie_secure, httponly=True, samesite="lax"
    )
    response.delete_cookie(
        key=settings.credential_cookie_name,
        path=_CREDENTIAL_COOKIE_PATH,
        secure=settings.cookie_secure,
        httponly=True,
        samesite="strict",
    )
