from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from src.domain.entities.llm.message import Message
from src.domain.entities.llm.tokens_usage import TokensUsage


@dataclass
class LLMMessage:
    """Representa o resultado de uma interação com o LLM.

    Attributes:
        id: Identificador único da interação de LLM.
        creation_timestamp: Data e hora de criação da interação em UTC.
        input_message: Mensagem de entrada utilizada na interação.
        output_message: Mensagem de saída retornada pelo LLM.
        tokens: Dados de consumo de tokens da interação.
        finish_reason: Motivo de término informado pelo provedor, quando há.
        provider_response_id: Identificador da resposta no provedor, quando há.
    """

    id: UUID | None = None
    creation_timestamp: datetime | None = None
    input_message: Message | None = None
    output_message: Message | None = None
    tokens: TokensUsage | None = None
    finish_reason: str | None = None
    provider_response_id: str | None = None

    @classmethod
    def new(
        cls,
        input_message: Message,
        output_message: Message,
        tokens: TokensUsage,
        finish_reason: str | None = None,
        provider_response_id: str | None = None,
    ) -> "LLMMessage":
        """Cria uma interação de LLM inferindo `id` e `creation_timestamp`.

        Args:
            input_message: Mensagem de entrada utilizada na interação.
            output_message: Mensagem de saída retornada pelo LLM.
            tokens: Dados de consumo de tokens da interação.
            finish_reason: Motivo de término informado pelo provedor, quando há.
            provider_response_id: Identificador da resposta no provedor, quando há.

        Returns:
            LLMMessage: Interação recém-criada.
        """
        return cls(
            id=uuid4(),
            creation_timestamp=datetime.now(tz=UTC),
            input_message=input_message,
            output_message=output_message,
            tokens=tokens,
            finish_reason=finish_reason,
            provider_response_id=provider_response_id,
        )
