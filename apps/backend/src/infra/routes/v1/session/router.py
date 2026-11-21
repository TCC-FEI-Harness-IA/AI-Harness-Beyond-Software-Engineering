from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from src.domain.entities.auth.authenticated_user import AuthenticatedUser
from src.domain.errors.session_not_found_error import SessionNotFoundError
from src.infra.security.request_security import current_identity
from src.infra.startups.session_query_startup import SessionQueryStartup

router = APIRouter(prefix="/sessions", tags=["session"])


@router.get(
    "",
    status_code=200,
    responses={401: {"description": "Unauthorized"}, 500: {"description": "Internal Server Error"}},
)
async def list_sessions(identity: AuthenticatedUser = Depends(current_identity)) -> dict[str, list[str]]:
    """Lista os identificadores das sessões da conta autenticada."""
    try:
        startup = SessionQueryStartup(owner_id=identity.user_id)
        return {"session_ids": await startup.list_session_ids()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get(
    "/{session_id}",
    status_code=200,
    responses={
        400: {"description": "Bad Request"},
        401: {"description": "Unauthorized"},
        404: {"description": "Not Found"},
        500: {"description": "Internal Server Error"},
    },
)
async def get_session(session_id: str, identity: AuthenticatedUser = Depends(current_identity)) -> dict[str, Any]:
    """Consulta uma sessão da conta autenticada; a de outra conta é indistinguível de inexistente (404)."""
    try:
        startup = SessionQueryStartup(owner_id=identity.user_id)
        return await startup.get_session_document(session_id=session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
