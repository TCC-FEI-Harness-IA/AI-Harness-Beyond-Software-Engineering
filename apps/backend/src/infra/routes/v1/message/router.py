from fastapi import APIRouter
from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from src.application.usecases.chain_of_thought_usecase import SendReasoningMessageUsecase
from src.infra.routes.v1.message.dtos.default_input_dto import DefaultInputDTO
from src.infra.routes.v1.message.dtos.default_output_dto import DefaultOutputDTO
from src.infra.routes.v1.message.dtos.reasoning_input_dto import ReasoningInputDTO
from src.infra.startups.default_message_startup import DefaultMessageStartup

router = APIRouter(prefix="/message", tags=["message"])


@router.post("/reasoning", status_code=200)
async def reasoning(payload: ReasoningInputDTO) -> StreamingResponse:
    usecase = SendReasoningMessageUsecase()

    async def stream():
        async for chunk in usecase.execute(payload.message.user_input):
            yield f"data: {chunk}\n\n"

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.post(
    "/default",
    status_code=200,
    responses={500: {"description": "Internal Server Error"}},
)
async def default_message(payload: DefaultInputDTO) -> DefaultOutputDTO:
    try:
        startup = DefaultMessageStartup()
        return startup.run(payload=payload)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
