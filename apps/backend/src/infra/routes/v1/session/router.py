from fastapi import APIRouter

router = APIRouter(prefix="/sessions", tags=["session"])


@router.get(
    "",
    status_code=200,
    responses={500: {"description": "Internal Server Error"}},
)
async def list_sessions() -> list[str]:
    """Lista os identificadores de todas as sessões persistidas."""
    raise NotImplementedError


@router.get(
    "/{session_id}",
    status_code=200,
    responses={404: {"description": "Not Found"}, 500: {"description": "Internal Server Error"}},
)
async def get_session(session_id: str) -> dict[str, str]:
    """Consulta uma sessão persistida pelo identificador."""
    raise NotImplementedError
