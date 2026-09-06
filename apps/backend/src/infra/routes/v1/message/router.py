from typing import Any
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from src.infra.routes.v1.message.dtos.default_input_dto import DefaultInputDTO
from src.infra.routes.v1.message.dtos.default_output_dto import DefaultOutputDTO
from src.infra.routes.v1.message.dtos.reasoning_input_dto import ReasoningInputDTO
from src.infra.startups.default_message_startup import DefaultMessageStartup
from src.infra.startups.ralph_loop_startup import RalphLoopStartup

router = APIRouter(prefix="/message", tags=["message"])


@router.post("/reasoning", status_code=200)
async def reasoning(payload: ReasoningInputDTO) -> StreamingResponse:
    """Endpoint de streaming Server-Sent Events (SSE) para o Ralph Loop Harness."""
    try:
        startup = RalphLoopStartup()

        async def stream():
            async for chunk in startup.run_stream(payload=payload):
                yield f"data: {chunk}\n\n"

        return StreamingResponse(
            stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/reasoning/sync", status_code=200)
async def reasoning_sync(payload: ReasoningInputDTO) -> dict[str, Any]:
    """Endpoint consolidado para execução síncrona do Ralph Loop (ideal para benchmarks MMLU/GPQA)."""
    try:
        startup = RalphLoopStartup()
        return await startup.run_sync(payload=payload)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post(
    "/default",
    status_code=200,
    responses={500: {"description": "Internal Server Error"}},
)
async def default_message(payload: DefaultInputDTO) -> DefaultOutputDTO:
    """Endpoint de chamada direta sem raciocínio multi-fase (linha de base)."""
    try:
        startup = DefaultMessageStartup()
        return startup.run(payload=payload)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
