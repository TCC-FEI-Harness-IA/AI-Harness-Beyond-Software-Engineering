from abc import ABC, abstractmethod

from src.domain.classes.llm.llm_service_provider.llm_provider_request import LLMProviderRequest
from src.domain.classes.llm.llm_service_provider.llm_provider_response import LLMProviderResponse
from src.domain.enums.model_provider_enum import ModelProviderEnum


class ILLMService(ABC):
    """Contrato de baixo nível para integração direta com APIs de LLM providers.

    Diferente de `ILLMCompletions`, este contrato não trabalha com entidades de
    domínio (`Message`/`LLMMessage`) e sim com payloads técnicos de API.
    """

    @property
    @abstractmethod
    def provider(self) -> ModelProviderEnum:
        """Retorna o provedor atendido pela implementação."""
        raise NotImplementedError

    @abstractmethod
    def verify_provider_settings(self) -> bool:
        """Verifica se as configurações mínimas do provedor estão disponíveis.

        Returns:
            bool: `True` quando o serviço está apto para chamadas.
        """
        raise NotImplementedError

    @abstractmethod
    def generate_response(self, request: LLMProviderRequest) -> LLMProviderResponse:
        """Executa uma chamada de chat completion no provedor.

        Args:
            request: Payload técnico da chamada de completion.

        Returns:
            LLMProviderResponse: Resultado padronizado da API.
        """
        raise NotImplementedError
