from dataclasses import dataclass, field

from src.domain.entities.llm.message import Message
from src.domain.entities.llm.tokens_usage import TokensUsage
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum


@dataclass
class ContextWindow:
    """Janela de contexto isolada de uma etapa do fluxo de thinking.

    Materializa o conceito de *Fresh Context* do paper: cada nova tarefa recebe
    uma janela nova, com identidade própria.

    Attributes:
        context_id: Identidade da janela. Muda a cada reinicialização de contexto.
        phase: Fase do fluxo que originou a janela.
        task_id: Tarefa associada, quando houver.
        messages: Conversa acumulada na janela, em ordem.
        tokens_input: Tokens de entrada acumulados na janela.
        tokens_output: Tokens de saída acumulados na janela.

    Os contadores somam o consumo de cada chamada feita sobre a janela. Como cada chamada reenvia
    o histórico, a soma conta de novo o que já estava lá: ela mede consumo acumulado, e não o
    comprimento atual da janela, e não deve ser lida como medida de mitigação de *context rot*.
    """

    context_id: str
    phase: ThinkingPhaseEnum
    task_id: str | None = None
    messages: list[Message] = field(default_factory=list)
    tokens_input: int = 0
    tokens_output: int = 0

    @property
    def context_size(self) -> int:
        """Total de tokens consumidos pelas chamadas feitas sobre a janela (consumo acumulado).

        Returns:
            int: Soma de `tokens_input` e `tokens_output`.
        """
        return self.tokens_input + self.tokens_output

    def append(self, message: Message) -> None:
        """Anexa uma mensagem ao final da janela.

        Args:
            message: Mensagem a ser anexada.
        """
        self.messages.append(message)

    def register_usage(self, tokens: TokensUsage) -> None:
        """Acumula o consumo de tokens de uma chamada na janela.

        Args:
            tokens: Consumo de tokens da chamada.
        """
        self.tokens_input += tokens.tokens_input
        self.tokens_output += tokens.tokens_output

    def is_empty(self) -> bool:
        """Informa se a janela ainda não recebeu nenhuma mensagem.

        Returns:
            bool: `True` quando `messages` está vazia.
        """
        return not self.messages
