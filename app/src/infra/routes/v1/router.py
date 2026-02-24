from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from src.infra.startups.chat_startup import ChatStartup

router = APIRouter(prefix="/v1")


@router.get("/health", status_code=200)
async def health_check():
    return {"status": "ok"}


@router.get("/chat", status_code=200)
async def chat():
    chat_startup = ChatStartup()
    return StreamingResponse(
        chat_startup.run(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )

