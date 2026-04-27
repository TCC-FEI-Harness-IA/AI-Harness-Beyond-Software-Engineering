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
        input_message: Message,
        model_name: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> LLMMessage:
        """Envia uma mensagem para o provedor de LLM.

        Args:
            input_message: Mensagem de entrada a ser processada pelo LLM.
            model_name: Nome do modelo a ser usado na chamada. Se `None`, usa o padrão da implementação.
            max_tokens: Limite de tokens de saída. Se `None`, usa o padrão da implementação.
            temperature: Temperatura da geração. Se `None`, usa o padrão da implementação.

        Returns:
            LLMMessage: Resultado da interação com o LLM.
        """
        raise NotImplementedError

