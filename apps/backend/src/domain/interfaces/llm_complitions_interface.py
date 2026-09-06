from abc import ABC, abstractmethod

from src.domain.classes.llm.messages.llm_message import LLMMessage
from src.domain.classes.llm.messages.message import Message


class ILLMCompletions(ABC):
    """Contrato de alto nível para caso de uso de completions no domínio.

    Diferente de `ILLMService`, esse contrato trabalha com entidades de domínio
    (`Message` e `LLMMessage`) e não com payload técnico de API.
    """

    @abstractmethod
    def send_message(
        self,
        input_message: Message | list[Message],
        model_name: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        provider: str | None = None,
        endpoint: str | None = None,
    ) -> LLMMessage:
        """Envia uma mensagem ou histórico de mensagens para o provedor de LLM.

        Args:
            input_message: Mensagem única ou lista sequencial de mensagens de domínio.
            model_name: Nome do modelo a ser usado na chamada. Se `None`, usa o padrão.
            max_tokens: Limite de tokens de saída. Se `None`, usa o padrão.
            temperature: Temperatura da geração. Se `None`, usa o padrão.
            provider: Provedor desejado (ex: "azure_foundry", "open_router", "mock").
            endpoint: Endpoint customizado opcional.

        Returns:
            LLMMessage: Resultado da interação com o LLM.
        """
        raise NotImplementedError

