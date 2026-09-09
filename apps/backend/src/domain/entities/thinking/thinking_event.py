from dataclasses import dataclass

from src.domain.enums.thinking_event_subtype_enum import ThinkingEventSubtypeEnum
from src.domain.enums.thinking_event_type_enum import ThinkingEventTypeEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum


@dataclass(frozen=True)
class ThinkingEvent:
    """Representa um evento emitido pelo WebSocket de thinking.

    Attributes:
        type: Tipo do evento.
        subtype: Subtipo do evento, mapeando a etapa exata do fluxo.
        phase: Fase de thinking que originou o evento.
        task: Identificador da tarefa, ou `setup`/`synthesis` para etapas globais.
        content: Conteúdo em markdown pronto para renderização.
        session_id: Identificador da sessão.
        total_tokens: Total de tokens acumulados na sessão até o evento.
        context_id: Identidade da janela de contexto no momento do evento.
        context_size: Tokens acumulados na janela de contexto atual.
        inference_time_ms: Tempo da chamada ao modelo, em milissegundos.
    """

    type: ThinkingEventTypeEnum
    subtype: ThinkingEventSubtypeEnum
    phase: ThinkingPhaseEnum
    task: str
    content: str
    session_id: str
    total_tokens: int
    context_id: str
    context_size: int
    inference_time_ms: int
