from dataclasses import dataclass
from datetime import datetime

from src.domain.entities.llm.message import Message
from src.domain.enums.message_source_enum import MessageSourceEnum
from src.domain.enums.thinking_event_subtype_enum import ThinkingEventSubtypeEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum


@dataclass(frozen=True)
class SessionMessage:
    """Representa uma mensagem persistida no histórico de uma sessão.

    Attributes:
        id: Identificador único da mensagem.
        order: Posição sequencial da mensagem na sessão.
        timestamp: Data e hora de registro da mensagem em UTC.
        phase: Fase de thinking que originou a mensagem.
        source: Origem da mensagem.
        content: Conteúdo textual da mensagem.
        task_id: Tarefa associada, quando houver.
        context_id: Janela de contexto associada, quando houver.
        tokens_input: Tokens de entrada consumidos pela mensagem.
        tokens_output: Tokens de saída consumidos pela mensagem.
        inference_time_ms: Tempo da chamada ao modelo, em milissegundos.
        model_name: Nome do modelo usado, quando aplicável.
        prompt_input: Conversa enviada ao modelo na chamada que produziu `content`, em ordem;
            vazia quando a mensagem não resulta de uma chamada ao modelo.
        invocation_id: Invocação a que a mensagem se refere, como a que produziu uma saída recusada e
            auditada; `None` quando não há vínculo ou em mensagens anteriores a este campo.
        subtype: Subtipo do evento emitido junto com a mensagem, para que o histórico reproduza o fluxo ao
            vivo sem adivinhar pelo conteúdo (por exemplo, distinguir um plano candidato da confirmação na
            fila); `None` em registros sem evento, como a auditoria de saídas recusadas, e nas sessões
            gravadas antes deste campo.
    """

    id: str
    order: int
    timestamp: datetime
    phase: ThinkingPhaseEnum
    source: MessageSourceEnum
    content: str
    task_id: str | None
    context_id: str | None
    tokens_input: int
    tokens_output: int
    inference_time_ms: int
    model_name: str | None
    prompt_input: tuple[Message, ...] = ()
    invocation_id: str | None = None
    subtype: ThinkingEventSubtypeEnum | None = None

    @property
    def total_tokens(self) -> int:
        """Total de tokens consumidos pela mensagem.

        Returns:
            int: Soma de `tokens_input` e `tokens_output`.
        """
        return self.tokens_input + self.tokens_output
