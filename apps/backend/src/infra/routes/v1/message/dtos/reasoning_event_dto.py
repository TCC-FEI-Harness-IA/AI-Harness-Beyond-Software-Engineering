from pydantic import BaseModel

from src.infra.routes.v1.message.dtos.context_window_dto import ContextWindowDTO


class ReasoningEventDTO(BaseModel):
    """Frame de evento emitido pelo WebSocket do fluxo harness."""

    type: str
    subtype: str
    phase: str
    task: str
    session_id: str
    content: str
    total_tokens: int
    context_window: ContextWindowDTO
    inference_time_ms: int
