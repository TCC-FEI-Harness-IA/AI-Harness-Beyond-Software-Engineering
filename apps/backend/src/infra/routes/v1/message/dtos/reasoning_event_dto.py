from pydantic import BaseModel

from src.infra.routes.v1.message.dtos.context_window_dto import ContextWindowDTO


class ReasoningEventDTO(BaseModel):
    """Frame de evento emitido pelo WebSocket do fluxo harness.

    `flow_version` acompanha todo frame para que o consumidor saiba, antes de interpretar o evento,
    o que significam as fases ambíguas: na versão 2, `A3` é a validação da decomposição e `A4` a
    extração dos aprendizados do enunciado.
    """

    type: str
    subtype: str
    phase: str
    task: str
    session_id: str
    content: str
    total_tokens: int
    context_window: ContextWindowDTO
    inference_time_ms: int
    flow_version: int
