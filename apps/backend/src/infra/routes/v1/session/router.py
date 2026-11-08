from typing import Any

from fastapi import APIRouter, HTTPException

from src.domain.errors.session_not_found_error import SessionNotFoundError
from src.infra.startups.session_query_startup import SessionQueryStartup

router = APIRouter(prefix="/sessions", tags=["session"])


@router.get(
    "",
    status_code=200,
    responses={500: {"description": "Internal Server Error"}},
)
async def list_sessions() -> dict[str, list[str]]:
    """Lista os identificadores de todas as sessões persistidas."""
    try:
        startup = SessionQueryStartup()
        return {"session_ids": await startup.list_session_ids()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get(
    "/{session_id}",
    status_code=200,
    responses={
        400: {"description": "Bad Request"},
        404: {"description": "Not Found"},
        500: {"description": "Internal Server Error"},
    },
)
async def get_session(session_id: str) -> dict[str, Any]:
    """Consulta uma sessão persistida pelo identificador."""
    try:
        startup = SessionQueryStartup()
        return await startup.get_session_document(session_id=session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
