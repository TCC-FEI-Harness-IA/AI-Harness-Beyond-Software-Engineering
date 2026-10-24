import logging
from collections.abc import Sequence
from datetime import UTC, datetime

from src.domain.entities.llm.llm_message import LLMMessage
from src.domain.entities.llm.llm_provider_message import LLMProviderMessage
from src.domain.entities.llm.llm_provider_request import LLMProviderRequest
from src.domain.entities.llm.message import Message
from src.domain.entities.llm.tokens_usage import TokensUsage
from src.domain.enums.message_source_enum import MessageSourceEnum
from src.domain.enums.model_provider_enum import ModelProviderEnum
from src.domain.interfaces.llm_completions_interface import ILLMCompletions
from src.domain.interfaces.llm_service_interface import ILLMService
from src.domain.interfaces.model_catalog_interface import IModelCatalog
from src.domain.interfaces.settings_interface import ISettings

_PROVIDER_ROLE_BY_SOURCE = {
    MessageSourceEnum.USER: "user",
    MessageSourceEnum.LLM_AGENT: "assistant",
    MessageSourceEnum.SYSTEM: "system",
}


class LLMCompletionsAdapter(ILLMCompletions):
    """Adapter para obtenção de completions via os `ILLMService` registrados.

    Recebe um serviço por provedor suportado e escolhe, a cada chamada, aquele que
    atende o provedor pedido — o da requisição, ou o configurado como padrão. Assim a
    troca de provedor é uma decisão de quem chama, e não da composição da aplicação.
    """

    def __init__(
        self,
        llm_services: Sequence[ILLMService],
        model_catalog: IModelCatalog,
        logger: logging.Logger,
        settings: ISettings,
    ) -> None:
        """Inicializa o adapter.

        Args:
            llm_services: Serviços de integração, um por provedor suportado.
            model_catalog: Catálogo que valida modelo e provedor.
            logger: Logger do módulo.
            settings: Configurações da aplicação, fonte dos valores padrão.

        Raises:
            ValueError: Quando a lista de serviços está vazia, tem dois serviços para o
                mesmo provedor, ou não cobre o provedor configurado como padrão. Também
                quando algum outro valor padrão configurado é inválido.
        """
        self.model_catalog: IModelCatalog = model_catalog
        self.logger = logger
        self.settings: ISettings = settings
        self.__services_by_provider = self.__index_services(llm_services=llm_services)
        self.__provider = self.__validate_provider(provider=self.settings.llm_provider)
        self.__model_name = self.__validate_model_name(model_name=self.settings.llm_model)
        self.__max_tokens = self.__validate_max_tokens(max_tokens=self.settings.llm_max_tokens)
        self.__temperature = self.__validate_temperature(temperature=self.settings.llm_temperature)

    def validate_conversation(
        self,
        conversation: list[Message],
        model_name: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        provider: ModelProviderEnum | None = None,
    ) -> None:
        """Valida a chamada exatamente como o envio a validaria, sem enviá-la.

        Args:
            conversation: Mensagens da janela de contexto, em ordem cronológica.
            model_name: Nome do modelo para a chamada atual.
            max_tokens: Limite máximo de tokens para a chamada atual.
            temperature: Temperatura para a chamada atual.
            provider: Provedor que atende a chamada atual.

        Raises:
            ValueError: Quando a conversa está vazia, algum parâmetro é inválido, o modelo é recusado
                ou o provedor não está configurado para atender a chamada.
        """
        self.__prepare(
            conversation=conversation,
            model_name=model_name,
            max_tokens=max_tokens,
            temperature=temperature,
            provider=provider,
        )

    async def send_message(
        self,
        input_message: Message,
        model_name: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        provider: ModelProviderEnum | None = None,
    ) -> LLMMessage:
        """Envia uma única mensagem, delegando para o envio de conversa.

        Args:
            input_message: Mensagem de entrada no formato de domínio.
            model_name: Nome do modelo para a chamada atual.
            max_tokens: Limite máximo de tokens para a chamada atual.
            temperature: Temperatura para a chamada atual.
            provider: Provedor que atende a chamada atual.

        Returns:
            LLMMessage: Resultado da interação com o provedor.
        """
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
        """Envia a janela de contexto inteira e devolve a completion do provedor.

        Quando `model_name`, `max_tokens`, `temperature` ou `provider` são informados,
        eles sobrescrevem os valores padrão do adapter apenas nesta chamada.

        Args:
            conversation: Mensagens da janela de contexto, em ordem cronológica.
            model_name: Nome do modelo para a chamada atual.
            max_tokens: Limite máximo de tokens para a chamada atual.
            temperature: Temperatura para a chamada atual.
            provider: Provedor que atende a chamada atual.

        Returns:
            LLMMessage: Resultado da interação com o provedor.

        Raises:
            ValueError: Quando a conversa está vazia ou algum parâmetro é inválido.
        """
        self.logger.info("Iniciando envio de conversa via LLMCompletionsAdapter")

        llm_service, request = self.__prepare(
            conversation=conversation,
            model_name=model_name,
            max_tokens=max_tokens,
            temperature=temperature,
            provider=provider,
        )
        llm_model = request.llm_model
        provider_response = await llm_service.generate_response(request=request)

        output_domain_message = Message(
            creation_timestamp=datetime.now(tz=UTC),
            text=provider_response.output_text,
            source=MessageSourceEnum.LLM_AGENT,
        )

        self.logger.info("Conversa processada com sucesso via LLMCompletionsAdapter")
        return LLMMessage.new(
            input_message=conversation[-1],
            output_message=output_domain_message,
            tokens=TokensUsage.from_reported(
                tokens_input=provider_response.input_tokens,
                tokens_output=provider_response.output_tokens,
                llm_model=llm_model,
            ),
            finish_reason=provider_response.finish_reason,
            provider_response_id=provider_response.response_id,
        )

    def __prepare(
        self,
        conversation: list[Message],
        model_name: str | None,
        max_tokens: int | None,
        temperature: float | None,
        provider: ModelProviderEnum | None,
    ) -> tuple[ILLMService, LLMProviderRequest]:
        """Valida a chamada por inteiro e monta a requisição que o serviço do provedor receberá.

        É o único caminho de validação: o envio e a validação prévia passam pelas mesmas regras.

        Args:
            conversation: Mensagens da janela de contexto, em ordem cronológica.
            model_name: Nome do modelo para a chamada atual.
            max_tokens: Limite máximo de tokens para a chamada atual.
            temperature: Temperatura para a chamada atual.
            provider: Provedor que atende a chamada atual.

        Returns:
            tuple[ILLMService, LLMProviderRequest]: Serviço do provedor e requisição já validada.

        Raises:
            ValueError: Quando qualquer regra local recusa a chamada.
        """
        if not conversation:
            raise ValueError("conversation must contain at least one message.")

        model_provider = self.__resolve_provider(provider=provider)
        llm_model = self.model_catalog.resolve(
            model_name=self.__resolve_model_name(model_name=model_name),
            model_provider=model_provider,
        )
        request = LLMProviderRequest(
            llm_model=llm_model,
            messages=[self.__to_provider_message(message=message) for message in conversation],
            max_tokens=self.__resolve_max_tokens(max_tokens=max_tokens),
            temperature=self.__resolve_temperature(temperature=temperature),
        )
        llm_service = self.__services_by_provider[model_provider]
        llm_service.validate_request(request=request)
        return llm_service, request

    def __index_services(self, llm_services: Sequence[ILLMService]) -> dict[ModelProviderEnum, ILLMService]:
        """Indexa os serviços pelo provedor que cada um atende.

        Args:
            llm_services: Serviços de integração informados na construção.

        Returns:
            dict[ModelProviderEnum, ILLMService]: Serviço responsável por cada provedor.

        Raises:
            ValueError: Quando a lista está vazia ou dois serviços atendem o mesmo provedor.
        """
        if not llm_services:
            raise ValueError("llm_services deve conter ao menos um serviço.")

        services_by_provider: dict[ModelProviderEnum, ILLMService] = {}
        for llm_service in llm_services:
            if llm_service.provider in services_by_provider:
                raise ValueError(f"Há mais de um serviço para o provedor '{llm_service.provider.value}'.")
            services_by_provider[llm_service.provider] = llm_service

        return services_by_provider

    def __to_provider_message(self, message: Message) -> LLMProviderMessage:
        """Converte uma mensagem de domínio no formato esperado pelo provedor."""
        return LLMProviderMessage(role=_PROVIDER_ROLE_BY_SOURCE[message.source], content=message.text)

    def __resolve_provider(self, provider: ModelProviderEnum | None) -> ModelProviderEnum:
        """Devolve o provedor da chamada, ou o padrão do adapter."""
        if provider is None:
            return self.__provider
        return self.__validate_provider(provider=provider)

    def __resolve_model_name(self, model_name: str | None) -> str:
        """Devolve o nome de modelo da chamada, ou o padrão do adapter."""
        if model_name is None:
            return self.__model_name
        return self.__validate_model_name(model_name=model_name)

    def __resolve_max_tokens(self, max_tokens: int | None) -> int:
        """Devolve o limite de tokens da chamada, ou o padrão do adapter."""
        if max_tokens is None:
            return self.__max_tokens
        return self.__validate_max_tokens(max_tokens=max_tokens)

    def __resolve_temperature(self, temperature: float | None) -> float:
        """Devolve a temperatura da chamada, ou o padrão do adapter."""
        if temperature is None:
            return self.__temperature
        return self.__validate_temperature(temperature=temperature)

    def __validate_provider(self, provider: ModelProviderEnum) -> ModelProviderEnum:
        """Valida que há um serviço registrado para o provedor.

        Raises:
            ValueError: Quando nenhum serviço atende o provedor.
        """
        if provider not in self.__services_by_provider:
            registrados = sorted(item.value for item in self.__services_by_provider)
            raise ValueError(
                f"Não há serviço registrado para o provedor '{provider.value}'. Registrados: {registrados}."
            )
        return provider

    def __validate_model_name(self, model_name: str) -> str:
        """Valida e normaliza um nome de modelo.

        Raises:
            ValueError: Quando o nome é vazio ou só contém espaços.
        """
        validated_model_name = model_name.strip()
        if not validated_model_name:
            raise ValueError("model_name deve ser um valor não vazio.")
        return validated_model_name

    def __validate_max_tokens(self, max_tokens: int) -> int:
        """Valida um limite de tokens de saída.

        Raises:
            ValueError: Quando o limite não é maior que zero.
        """
        if max_tokens <= 0:
            raise ValueError("max_tokens deve ser maior que zero.")
        return max_tokens

    def __validate_temperature(self, temperature: float) -> float:
        """Valida uma temperatura, preservando exatamente o valor solicitado.

        Raises:
            ValueError: Quando a temperatura está fora do intervalo `[0, 1]` ou não é finita.
        """
        if not 0 <= temperature <= 1:
            raise ValueError("temperature deve estar entre 0 e 1")
        return temperature
