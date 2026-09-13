from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import ValidationError
from starlette.websockets import WebSocketState

from src.domain.enums.session_status_enum import SessionStatusEnum
from src.infra.config.settings import Settings
from src.infra.routes.v1.message.dtos.default_input_dto import DefaultInputDTO
from src.infra.routes.v1.message.dtos.default_output_dto import DefaultOutputDTO
from src.infra.routes.v1.message.dtos.reasoning_input_dto import ReasoningInputDTO
from src.infra.startups.default_message_startup import DefaultMessageStartup
from src.infra.startups.ralph_thinking_startup import RalphThinkingStartup

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
    settings = Settings()
    logger = settings.logger(module_file=__file__)

    await websocket.accept()

    raw = await websocket.receive_text()
    if len(raw.encode("utf-8")) > settings.ralph_websocket_max_message_bytes:
        await websocket.close(code=1009)
        return

    try:
        payload = ReasoningInputDTO.model_validate_json(raw)
    except ValidationError as error:
        await websocket.send_json({"type": "error", "content": str(error)})
        await websocket.close(code=1003)
        return

    startup = RalphThinkingStartup()
    generator = startup.run(payload=payload)

    try:
        async for event in generator:
            await websocket.send_json(event.model_dump())
        await websocket.close(code=1000)
    except WebSocketDisconnect:
        await generator.aclose()
        await startup.session_recorder.finish(status=SessionStatusEnum.FAILED, final_answer=None)
        logger.info("Cliente desconectou durante a execução do fluxo harness")
    except Exception as error:
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.send_json({"type": "error", "content": str(error)})
        await websocket.close(code=1011)
        logger.exception("Erro ao executar o fluxo harness")
