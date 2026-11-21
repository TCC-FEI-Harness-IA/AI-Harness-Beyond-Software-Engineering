from abc import ABC, abstractmethod

from src.domain.entities.llm.llm_message import LLMMessage
from src.domain.entities.llm.message import Message
from src.domain.enums.model_provider_enum import ModelProviderEnum


class ILLMCompletions(ABC):
    """Contrato de alto nível para caso de uso de completions no domínio.

    Diferente de `ILLMService`, esse contrato trabalha com entidades de domínio
    (`Message` e `LLMMessage`) e não com payload técnico de API.
    """

    @abstractmethod
    def validate_conversation(
        self,
        conversation: list[Message],
        model_name: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        provider: ModelProviderEnum | None = None,
    ) -> None:
        """Valida localmente uma chamada, sem enviá-la ao provedor.

        Quem chama usa esta validação para separar a recusa local do início efetivo da chamada: o
        que é recusado aqui nunca foi enviado, não consome orçamento e não é uma invocação ao modelo.
        Os parâmetros são os mesmos de `send_conversation`.

        Args:
            conversation: Mensagens da janela de contexto, em ordem cronológica.
            model_name: Nome do modelo a ser usado na chamada. Se `None`, usa o padrão da implementação.
            max_tokens: Limite de tokens de saída. Se `None`, usa o padrão da implementação.
            temperature: Temperatura da geração. Se `None`, usa o padrão da implementação.
            provider: Provedor que atende a chamada. Se `None`, usa o padrão da implementação.

        Raises:
            ValueError: Quando a conversa está vazia, algum parâmetro é inválido, o modelo é recusado
                ou o provedor não está configurado para atender a chamada.
        """
        raise NotImplementedError

    @abstractmethod
    async def send_message(
        self,
        input_message: Message,
        model_name: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        provider: ModelProviderEnum | None = None,
    ) -> LLMMessage:
        """Envia uma única mensagem para o provedor de LLM.

        Args:
            input_message: Mensagem de entrada a ser processada pelo LLM.
            model_name: Nome do modelo a ser usado na chamada. Se `None`, usa o padrão da implementação.
            max_tokens: Limite de tokens de saída. Se `None`, usa o padrão da implementação.
            temperature: Temperatura da geração. Se `None`, usa o padrão da implementação.
            provider: Provedor que atende a chamada. Se `None`, usa o padrão da implementação.

        Returns:
            LLMMessage: Resultado da interação com o LLM.

        Raises:
            ValueError: Quando algum parâmetro informado é inválido.
        """
        raise NotImplementedError

    @abstractmethod
    async def send_conversation(
        self,
        conversation: list[Message],
        model_name: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        provider: ModelProviderEnum | None = None,
    ) -> LLMMessage:
        """Envia uma conversa multi-turno para o provedor de LLM.

        Args:
            conversation: Mensagens da janela de contexto, em ordem cronológica.
            model_name: Nome do modelo a ser usado na chamada. Se `None`, usa o padrão da implementação.
            max_tokens: Limite de tokens de saída. Se `None`, usa o padrão da implementação.
            temperature: Temperatura da geração. Se `None`, usa o padrão da implementação.
            provider: Provedor que atende a chamada. Se `None`, usa o padrão da implementação.

        Returns:
            LLMMessage: Resultado da interação com o LLM.

        Raises:
            ValueError: Quando a conversa está vazia ou algum parâmetro é inválido.
        """
        raise NotImplementedError
