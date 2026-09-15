from src.domain.entities.llm.llm_message import LLMMessage
from src.domain.entities.llm.message import Message
from src.domain.enums.model_provider_enum import ModelProviderEnum
from src.domain.interfaces.llm_completions_interface import ILLMCompletions


class FakeLLMCompletions(ILLMCompletions):
    """Dublê de `ILLMCompletions` com retorno programável e contagem de chamadas."""

    def __init__(self, result: LLMMessage | None = None, error: Exception | None = None) -> None:
        """Configura o dublê.

        Args:
            result: Resultado devolvido em cada chamada.
            error: Exceção levantada em vez de responder, quando informada.
        """
        self.result = result
        self.error = error
        self.conversations: list[list[Message]] = []
        self.calls: list[dict[str, object]] = []

    async def send_message(
        self,
        input_message: Message,
        model_name: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        provider: ModelProviderEnum | None = None,
    ) -> LLMMessage:
        """Registra o envio de uma única mensagem e devolve o resultado programado."""
        return await self.send_conversation(
            conversation=[input_message],
            model_name=model_name,
            max_tokens=max_tokens,
            temperature=temperature,
            provider=provider,
        )

    async def send_conversation(
        self,
        conversation: list[Message],
        model_name: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        provider: ModelProviderEnum | None = None,
    ) -> LLMMessage:
        """Registra a conversa e devolve o resultado programado."""
        self.conversations.append(conversation)
        self.calls.append(
            {
                "model_name": model_name,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "provider": provider,
            }
        )

        if self.error is not None:
            raise self.error

        return self.result  # type: ignore[return-value]
