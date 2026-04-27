from datetime import UTC, datetime
from typing import List
from uuid import UUID, uuid4

from src.domain.classes.llm.messages.llm_message import LLMMessage
from src.domain.classes.llm.messages.message import Message
from src.domain.classes.llm.tokens_usage.tokens import TokensUsage


class Chat:
    """Representa uma conversa com contexto e agregados de uso.

    Attributes:
        id: Identificador único do chat.
        creation_timestamp: Data e hora de criação do chat em UTC.
        update_timestamp: Data e hora da última atualização do chat em UTC.
        input_message: Mensagem de entrada inicial do chat.
        internal_llm_messages: Mensagens internas de LLM acumuladas no chat.
        final_output_message: Mensagem final de saída do chat, quando disponível.
        total_tokens_usage: Consumo total de tokens acumulado no chat.
        total_messages: Total de mensagens contabilizadas no chat.
    """

    def __init__(
        self,
        id: UUID | None = None,
        creation_timestamp: datetime | None = None,
        update_timestamp: datetime | None = None,
        input_message: Message | None = None,
        internal_llm_messages: List[LLMMessage] | None = None,
        final_output_message: LLMMessage | None = None,
        total_tokens_usage: TokensUsage | None = None,
        total_messages: int | None = None,
    ) -> None:
        """Inicializa uma instância de chat.

        Args:
            id: Identificador único do chat.
            creation_timestamp: Data e hora de criação do chat.
            update_timestamp: Data e hora da última atualização do chat.
            input_message: Mensagem de entrada inicial do chat.
            internal_llm_messages: Mensagens internas de LLM acumuladas no chat.
            final_output_message: Mensagem final de saída do chat.
            total_tokens_usage: Consumo total de tokens acumulado no chat.
            total_messages: Total de mensagens contabilizadas no chat.
        """
        self.id = id
        self.creation_timestamp = creation_timestamp
        self.update_timestamp = update_timestamp
        self.input_message = input_message
        self.internal_llm_messages = internal_llm_messages
        self.final_output_message = final_output_message
        self.total_tokens_usage = total_tokens_usage
        self.total_messages = total_messages

    def new(self, input_message: Message) -> None:
        """Inicializa o chat inferindo metadados iniciais.

        Raises:
            ValueError: Quando a instância já possui dados.

        Args:
            input_message: Mensagem de entrada inicial do chat.
        """
        if any(
            value is not None
            for value in (
                self.id,
                self.creation_timestamp,
                self.update_timestamp,
                self.input_message,
                self.internal_llm_messages,
                self.final_output_message,
                self.total_tokens_usage,
                self.total_messages,
            )
        ):
            raise ValueError("Cannot call `new` on a Chat that already has data.")

        now = datetime.now(tz=UTC)
        self.id = uuid4()
        self.creation_timestamp = now
        self.update_timestamp = now
        self.input_message = input_message
        self.internal_llm_messages = []
        self.final_output_message = None
        self.total_tokens_usage = None
        self.total_messages = 1

    def add_intenal_llm_message(self, llm_message: LLMMessage) -> None:
        """Adiciona uma mensagem interna de LLM e atualiza contadores.

        Args:
            llm_message: Mensagem de LLM a ser adicionada.
        """
        if self.internal_llm_messages is None or self.total_messages is None:
            raise ValueError("Chat must be initialized with `new` before adding messages.")

        self.internal_llm_messages.append(llm_message)
        self.__increase_messages_count()
        self.__increase_tokens_count(llm_message)
        self.update_timestamp = datetime.now(tz=UTC)

    def add_final_output_message(self, llm_message: LLMMessage) -> None:
        """Adiciona a mensagem final do chat e atualiza contadores.

        Args:
            llm_message: Mensagem final a ser adicionada.
        """
        if self.total_messages is None:
            raise ValueError("Chat must be initialized with `new` before adding messages.")

        self.final_output_message = llm_message
        self.__increase_messages_count()
        self.__increase_tokens_count(llm_message)
        self.update_timestamp = datetime.now(tz=UTC)

    def __increase_messages_count(self) -> None:
        """Incrementa em uma unidade o total de mensagens do chat."""
        if self.total_messages is None:
            raise ValueError("Chat must be initialized with `new` before counting messages.")

        self.total_messages += 1

    def __increase_tokens_count(self, llm_message: LLMMessage) -> None:
        """Acumula os tokens de entrada e saída no total do chat.

        Args:
            llm_message: Mensagem de LLM com consumo de tokens a ser somado.
        """
        if llm_message.tokens is None:
            raise ValueError("LLMMessage must contain `tokens` to update token usage.")

        tokens = llm_message.tokens

        if self.total_tokens_usage is None:
            self.total_tokens_usage = TokensUsage(
                tokens_input=0,
                tokens_output=0,
                llm_model=tokens.llm_model,
            )

        self.total_tokens_usage.tokens_input += tokens.tokens_input
        self.total_tokens_usage.tokens_output += tokens.tokens_output

