from datetime import UTC, datetime
from uuid import UUID, uuid4

from src.domain.classes.llm.messages.message import Message
from src.domain.classes.llm.tokens_usage.tokens import TokensUsage


class LLMMessage:
    """Representa o resultado de uma interação com o LLM.

    Attributes:
        id: Identificador único da interação de LLM.
        creation_timestamp: Data e hora de criação da interação em UTC.
        input_message: Mensagem de entrada utilizada na interação.
        output_message: Mensagem de saída retornada pelo LLM.
        tokens: Dados de consumo de tokens da interação.
    """

    def __init__(
        self,
        id: UUID | None = None,
        creation_timestamp: datetime | None = None,
        input_message: Message | None = None,
        output_message: Message | None = None,
        tokens: TokensUsage | None = None,
    ) -> None:
        """Inicializa uma interação de LLM.

        Args:
            id: Identificador único da interação.
            creation_timestamp: Data e hora de criação da interação.
            input_message: Mensagem de entrada utilizada na interação.
            output_message: Mensagem de saída retornada pelo LLM.
            tokens: Dados de consumo de tokens da interação.
        """
        self.id = id
        self.creation_timestamp = creation_timestamp
        self.input_message = input_message
        self.output_message = output_message
        self.tokens = tokens

    def new(
        self,
        input_message: Message,
        output_message: Message,
        tokens: TokensUsage,
    ) -> None:
        """Inicializa a interação de LLM inferindo `id` e `creation_timestamp`.

        Raises:
            ValueError: Quando a instância já possui dados.

        Args:
            input_message: Mensagem de entrada utilizada na interação.
            output_message: Mensagem de saída retornada pelo LLM.
            tokens: Dados de consumo de tokens da interação.
        """
        if any(
            value is not None
            for value in (
                self.id,
                self.creation_timestamp,
                self.input_message,
                self.output_message,
                self.tokens,
            )
        ):
            raise ValueError("Cannot call `new` on an LLMMessage that already has data.")

        self.id = uuid4()
        self.creation_timestamp = datetime.now(tz=UTC)
        self.input_message = input_message
        self.output_message = output_message
        self.tokens = tokens

