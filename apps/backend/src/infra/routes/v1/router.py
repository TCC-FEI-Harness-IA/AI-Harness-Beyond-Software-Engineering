from fastapi import APIRouter
from src.infra.routes.v1.message.router import router as message_router

router = APIRouter(prefix="/v1")

router.include_router(message_router)

@router.get("/health", status_code=200)
async def health_check():
    return {"status": "ok"}

