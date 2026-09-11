from datetime import UTC, datetime

from src.domain.entities.llm.genai_model import GenaiModel
from src.domain.entities.llm.llm_message import LLMMessage
from src.domain.entities.llm.message import Message
from src.domain.entities.llm.tokens_usage import TokensUsage
from src.domain.enums.message_source_enum import MessageSourceEnum
from src.domain.enums.model_provider_enum import ModelProviderEnum
from src.domain.interfaces.llm_completions_interface import ILLMCompletions

_DEFAULT_TOKENS_INPUT = 10
_DEFAULT_TOKENS_OUTPUT = 5
_DEFAULT_MODEL_NAME = "vendor/modelo-padrao"


class ScriptedLLMCompletions(ILLMCompletions):
    """Dublê de `ILLMCompletions` que devolve uma fila de saídas programadas.

    Guarda uma cópia de cada conversa recebida: é inspecionando essas conversas
    que os testes provam as invariantes de contexto do fluxo.
    """

    def __init__(
        self,
        responses: list[str] | None = None,
        tokens_input: int = _DEFAULT_TOKENS_INPUT,
        tokens_output: int = _DEFAULT_TOKENS_OUTPUT,
        error: Exception | None = None,
    ) -> None:
        """Configura o dublê.

        Args:
            responses: Fila de saídas brutas devolvidas, uma por chamada.
            tokens_input: Tokens de entrada contabilizados em cada chamada.
            tokens_output: Tokens de saída contabilizados em cada chamada.
            error: Exceção levantada em vez de responder, quando informada.
        """
        self.responses = list(responses) if responses else []
        self.tokens_input = tokens_input
        self.tokens_output = tokens_output
        self.error = error
        self.conversations: list[list[Message]] = []
        self.calls: list[dict[str, object]] = []

    @property
    def call_count(self) -> int:
        """Quantidade de chamadas ao modelo já realizadas."""
        return len(self.conversations)

    def texts_of(self, call_index: int) -> list[str]:
        """Devolve os textos da conversa capturada na chamada informada.

        Args:
            call_index: Índice da chamada, começando em zero.

        Returns:
            list[str]: Textos das mensagens enviadas naquela chamada, em ordem.
        """
        return [message.text for message in self.conversations[call_index]]

    async def send_message(
        self,
        input_message: Message,
        model_name: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> LLMMessage:
        """Delega o envio de uma única mensagem para o envio de conversa."""
        return await self.send_conversation(
            conversation=[input_message],
            model_name=model_name,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    async def send_conversation(
        self,
        conversation: list[Message],
        model_name: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> LLMMessage:
        """Copia a conversa recebida e devolve a próxima saída programada.

        Raises:
            AssertionError: Quando a fila de saídas programadas se esgota.
        """
        self.conversations.append(list(conversation))
        self.calls.append({"model_name": model_name, "max_tokens": max_tokens, "temperature": temperature})

        if self.error is not None:
            raise self.error

        if not self.responses:
            raise AssertionError(f"Chamada ao modelo nº {self.call_count} sem saída programada.")

        return self.__to_llm_message(conversation=conversation, output_text=self.responses.pop(0))

    def __to_llm_message(self, conversation: list[Message], output_text: str) -> LLMMessage:
        """Monta o resultado de domínio equivalente à saída programada."""
        return LLMMessage.new(
            input_message=conversation[-1],
            output_message=Message(
                creation_timestamp=datetime(2026, 8, 31, 12, 0, tzinfo=UTC),
                text=output_text,
                source=MessageSourceEnum.LLM_AGENT,
            ),
            tokens=TokensUsage(
                tokens_input=self.tokens_input,
                tokens_output=self.tokens_output,
                llm_model=GenaiModel(
                    model_name=_DEFAULT_MODEL_NAME,
                    model_provider=ModelProviderEnum.OPEN_ROUTER,
                ),
            ),
        )
