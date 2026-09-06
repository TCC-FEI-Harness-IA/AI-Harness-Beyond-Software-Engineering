from collections.abc import Mapping
from datetime import UTC, datetime
import logging

from src.domain.classes.llm.llm_service_provider.llm_provider_message import LLMProviderMessage
from src.domain.classes.llm.llm_service_provider.llm_provider_request import LLMProviderRequest
from src.domain.classes.llm.messages.llm_message import LLMMessage
from src.domain.classes.llm.messages.message import Message
from src.domain.classes.llm.models.genai_model import GenaiModel
from src.domain.classes.llm.tokens_usage.tokens import TokensUsage
from src.domain.enums.message_source_enum import MessageSourceEnum
from src.domain.enums.model_provider_enum import ModelProviderEnum
from src.domain.interfaces.llm_complitions_interface import ILLMCompletions
from src.domain.interfaces.llm_service_interface import ILLMService
from src.domain.interfaces.settings_interface import ISettings


class LLMComplitionsAdapter(ILLMCompletions):
    """Adapter para obtenção de completions via múltiplos `ILLMService` (Azure Foundry, OpenRouter, Mock)."""

    def __init__(
        self,
        llm_service: ILLMService,
        logger: logging.Logger,
        settings: ISettings,
        additional_services: Mapping[ModelProviderEnum, ILLMService] | None = None,
    ) -> None:
        self.logger = logger
        self.settings: ISettings = settings
        self.__services: dict[ModelProviderEnum, ILLMService] = {
            llm_service.provider: llm_service
        }
        if additional_services:
            self.__services.update(additional_services)

        self.primary_service = llm_service

    def register_service(self, service: ILLMService) -> None:
        """Registra dinamicamente um novo serviço de LLM por provedor."""
        self.__services[service.provider] = service

    def __resolve_provider(self, provider_str: str | None) -> ModelProviderEnum:
        if provider_str:
            normalized = provider_str.strip().lower()
            for p in ModelProviderEnum:
                if p.value == normalized:
                    return p

        try:
            default_env = (self.settings.get_var_env("DEFAULT_MODEL_PROVIDER") or "").strip().lower()
            for p in ModelProviderEnum:
                if p.value == default_env:
                    return p
        except ValueError:
            pass

        return self.primary_service.provider

    def __resolve_service(self, provider: ModelProviderEnum) -> ILLMService:
        if provider in self.__services:
            return self.__services[provider]

        # Se o provedor requisitado não tiver serviço registrado, tenta o primário
        self.logger.warning(
            "Provedor '%s' não encontrado nos serviços registrados. Usando primário: '%s'",
            provider.value,
            self.primary_service.provider.value,
        )
        return self.primary_service

    def __resolve_default_model(self, provider: ModelProviderEnum) -> str:
        if provider == ModelProviderEnum.AZURE_FOUNDRY:
            try:
                return (self.settings.get_var_env("AZURE_FOUNDRY_MODEL") or "meta-llama-3.1-8b-instruct").strip()
            except ValueError:
                return "meta-llama-3.1-8b-instruct"
        elif provider == ModelProviderEnum.OPEN_ROUTER:
            try:
                return (self.settings.get_var_env("OPENROUTER_MODEL") or "openai/gpt-4o-mini").strip()
            except ValueError:
                return "openai/gpt-4o-mini"
        elif provider == ModelProviderEnum.MOCK:
            return "mock-llama-3.1-8b"

        return "default-model"

    def __map_message_to_provider(self, msg: Message) -> LLMProviderMessage:
        if msg.source == MessageSourceEnum.LLM_AGENT:
            role = "assistant"
        elif msg.source == MessageSourceEnum.SYSTEM:
            role = "system"
        else:
            role = "user"
        return LLMProviderMessage(role=role, content=msg.text)

    def send_message(
        self,
        input_message: Message | list[Message],
        model_name: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        provider: str | None = None,
        endpoint: str | None = None,
    ) -> LLMMessage:
        resolved_provider = self.__resolve_provider(provider)
        service = self.__resolve_service(resolved_provider)

        resolved_model_name = (
            model_name.strip()
            if model_name and model_name.strip()
            else self.__resolve_default_model(resolved_provider)
        )

        resolved_max_tokens = max_tokens if max_tokens is not None and max_tokens > 0 else 1024
        resolved_temperature = (
            round(float(temperature), 1)
            if temperature is not None and 0 <= float(temperature) <= 1
            else 0.7
        )

        # Monta mensagens para o provedor
        if isinstance(input_message, list):
            if not input_message:
                raise ValueError("A lista de mensagens não pode ser vazia.")
            provider_messages = [self.__map_message_to_provider(m) for m in input_message]
            last_input = input_message[-1]
        else:
            provider_messages = [self.__map_message_to_provider(input_message)]
            last_input = input_message

        llm_model = GenaiModel(settings=self.settings)
        llm_model.new(
            model_name=resolved_model_name,
            model_provider=resolved_provider,
        )

        metadata: dict[str, object] = {}
        if endpoint:
            metadata["endpoint"] = endpoint

        request = LLMProviderRequest(
            llm_model=llm_model,
            messages=provider_messages,
            max_tokens=resolved_max_tokens,
            temperature=resolved_temperature,
            metadata=metadata,
        )

        provider_response = service.generate_response(request=request)

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
            input_message=last_input,
            output_message=output_domain_message,
            tokens=tokens_usage,
        )

        return llm_message
