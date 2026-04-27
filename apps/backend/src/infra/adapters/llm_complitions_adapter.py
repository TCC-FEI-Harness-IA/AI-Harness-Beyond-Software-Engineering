from datetime import UTC, datetime
import logging

from src.domain.classes.llm.messages.llm_message import LLMMessage
from src.domain.classes.llm.messages.message import Message
from src.domain.classes.llm.llm_service_provider.llm_provider_message import LLMProviderMessage
from src.domain.classes.llm.llm_service_provider.llm_provider_request import LLMProviderRequest
from src.domain.classes.llm.models.genai_model import GenaiModel
from src.domain.classes.llm.tokens_usage.tokens import TokensUsage
from src.domain.enums.message_source_enum import MessageSourceEnum
from src.domain.enums.model_provider_enum import ModelProviderEnum
from src.domain.interfaces.llm_complitions_interface import ILLMCompletions
from src.domain.interfaces.llm_service_interface import ILLMService
from src.domain.interfaces.settings_interface import ISettings


class LLMComplitionsAdapter(ILLMCompletions):
    """Adapter para obtenção de completions via um `ILLMService`."""

    def __init__(self, llm_service: ILLMService, logger: logging.Logger, settings: ISettings) -> None:
        """Inicializa o adapter.

        Args:
            llm_service: Serviço de integração com provedor LLM injetado externamente.
        """
        self.llm_service: ILLMService = llm_service
        self.logger = logger
        self.settings: ISettings = settings
        self.__model_name = self.__load_default_model_name()
        self.__max_tokens = self.__load_default_max_tokens()
        self.__temperature = self.__load_default_temperature()

    def __validate_model_name(self, model_name: str) -> str:
        validated_model_name = model_name.strip()
        if not validated_model_name:
            raise ValueError("model_name deve ser um valor não vazio.")
        return validated_model_name

    def __validate_max_tokens(self, max_tokens: int | str) -> int:
        validated_max_tokens = int(max_tokens)
        if validated_max_tokens <= 0:
            raise ValueError("max_tokens deve ser maior que zero.")
        return validated_max_tokens

    def __validate_temperature(self, temperature: float | str) -> float:
        validated_temperature = float(temperature)
        if not 0 <= validated_temperature <= 1:
            raise ValueError("temperature deve estar entre 0 e 1")
        return round(validated_temperature, 1)

    def __load_default_model_name(self) -> str:
        return self.__validate_model_name(self.settings.get_var_env("OPENROUTER_MODEL"))

    def __load_default_max_tokens(self) -> int:
        return self.__validate_max_tokens(self.settings.get_var_env("OPENROUTER_MAX_TOKENS"))

    def __load_default_temperature(self) -> float:
        return self.__validate_temperature(self.settings.get_var_env("OPENROUTER_TEMPERATURE"))

    def send_message(
        self,
        input_message: Message,
        model_name: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> LLMMessage:
        """Envia uma mensagem de domínio e retorna a completion do provedor.

        Se `model_name`, `max_tokens` ou `temperature` forem informados, eles
        sobrescrevem os valores padrão do adapter nesta chamada. Caso contrário,
        os valores padrão carregados de variáveis de ambiente serão utilizados.

        Args:
            input_message: Mensagem de entrada no formato de domínio.
            model_name: Nome do modelo para a chamada atual.
            max_tokens: Limite máximo de tokens para a chamada atual.
            temperature: Temperatura para a chamada atual.

        Returns:
            LLMMessage: Resultado da interação com o provedor.
        """
        self.logger.info("Iniciando envio de mensagem via LLMComplitionsAdapter")

        resolved_model_name = (
            self.__validate_model_name(model_name) if model_name is not None else self.__model_name
        )

        resolved_max_tokens = (
            self.__validate_max_tokens(max_tokens) if max_tokens is not None else self.__max_tokens
        )

        resolved_temperature = (
            self.__validate_temperature(temperature) if temperature is not None else self.__temperature
        )

        llm_model = GenaiModel(settings=self.settings)
        llm_model.new(
            model_name=resolved_model_name,
            model_provider=ModelProviderEnum.OPEN_ROUTER,
        )

        provider_response = self.llm_service.generate_response(
            request=LLMProviderRequest(
                llm_model=llm_model,
                messages=[LLMProviderMessage(role="user", content=input_message.text)],
                max_tokens=resolved_max_tokens,
                temperature=resolved_temperature,
            )
        )

        tokens_usage = TokensUsage(
            tokens_input=provider_response.input_tokens,
            tokens_output=provider_response.output_tokens,
            llm_model=llm_model,
        )

        output_domain_message = Message(
            creation_timestamp=datetime.now(tz=UTC),
            text=provider_response.output_text,
            source=MessageSourceEnum.LLM_AGENT,
        )

        llm_message = LLMMessage()
        llm_message.new(
            input_message=input_message,
            output_message=output_domain_message,
            tokens=tokens_usage,
        )

        self.logger.info("Mensagem processada com sucesso via LLMComplitionsAdapter")
        return llm_message
