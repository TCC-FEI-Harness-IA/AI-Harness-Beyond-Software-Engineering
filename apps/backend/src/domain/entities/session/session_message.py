from dataclasses import dataclass
from datetime import datetime

from src.domain.enums.message_source_enum import MessageSourceEnum
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

    @property
    def total_tokens(self) -> int:
        """Total de tokens consumidos pela mensagem.

        Returns:
            int: Soma de `tokens_input` e `tokens_output`.
        """
        return self.tokens_input + self.tokens_output
