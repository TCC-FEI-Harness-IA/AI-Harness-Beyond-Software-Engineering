from fastapi import APIRouter

from src.infra.routes.v1.message.router import router as message_router
from src.infra.routes.v1.session.router import router as session_router

router = APIRouter(prefix="/v1")

router.include_router(message_router)
router.include_router(session_router)


@router.get("/health", status_code=200)
async def health_check() -> dict[str, str]:
    """Verifica se a aplicação está no ar."""
    return {"status": "ok"}
