from fastapi import APIRouter, HTTPException, WebSocket

from src.infra.routes.v1.message.dtos.default_input_dto import DefaultInputDTO
from src.infra.routes.v1.message.dtos.default_output_dto import DefaultOutputDTO
from src.infra.startups.default_message_startup import DefaultMessageStartup

router = APIRouter(prefix="/message", tags=["message"])


@router.post(
    "/default",
    status_code=200,
    responses={500: {"description": "Internal Server Error"}},
)
async def default_message(payload: DefaultInputDTO) -> DefaultOutputDTO:
    """Executa o fluxo baseline: uma única chamada direta ao modelo."""
    try:
        startup = DefaultMessageStartup()
        return await startup.run(payload=payload)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.websocket("/reasoning")
async def reasoning(websocket: WebSocket) -> None:
    """Executa o fluxo harness (Ralph Loop adaptado), emitindo um evento por etapa."""
    raise NotImplementedError
