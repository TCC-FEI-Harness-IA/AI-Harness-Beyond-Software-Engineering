from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response

from src.domain.errors.session_invalid_error import SessionInvalidError
from src.infra.routes.dtos.auth_dtos import VerifyInputDTO
from src.infra.routes.http_security import NO_STORE, tokens_match
from src.infra.startups.auth_container import AuthContainer

router = APIRouter(prefix="/internal", tags=["internal"], include_in_schema=False)


@router.post("/sessions/verify")
async def verify_session(payload: VerifyInputDTO, request: Request, response: Response) -> dict[str, Any]:
    """Valida, para o backend, o token de sessão que chegou num cookie.

    Só atende quem apresenta o segredo de serviço (`Authorization: Bearer <AUTH_INTERNAL_TOKEN>`); o
    proxy público não encaminha `/internal`. Devolve o mínimo para autorização: sem e-mail.
    """
    container: AuthContainer = request.app.state.container
    authorization = request.headers.get("authorization", "")
    presented = authorization[len("Bearer "):] if authorization.startswith("Bearer ") else None
    if not tokens_match(container.settings.internal_token, presented):
        raise HTTPException(status_code=401, detail="Serviço não autorizado.", headers=NO_STORE)
    try:
        current = await container.resolve_session.execute(token=payload.token)
    except SessionInvalidError as exc:
        raise HTTPException(status_code=401, detail=str(exc), headers=NO_STORE) from exc
    response.headers.update(NO_STORE)
    return {
        "user_id": current.user.id,
        "role": current.user.role.value,
        "session_id": current.session.id,
        "expires_at": current.session.expires_at.isoformat(),
        "csrf_token": current.session.csrf_token,
    }
