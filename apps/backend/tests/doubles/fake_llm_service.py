from src.domain.entities.llm.llm_provider_request import LLMProviderRequest
from src.domain.entities.llm.llm_provider_response import LLMProviderResponse
from src.domain.enums.model_provider_enum import ModelProviderEnum
from src.domain.interfaces.llm_service_interface import ILLMService


class FakeLLMService(ILLMService):
    """Dublê de `ILLMService` com resposta programável e captura das requisições."""

    def __init__(self, response: LLMProviderResponse | None = None, error: Exception | None = None) -> None:
        """Configura o dublê.

        Args:
            response: Resposta devolvida em cada chamada. Quando `None`, usa uma resposta padrão.
            error: Exceção levantada em vez de responder, quando informada.
        """
        self.response = response or LLMProviderResponse(
            output_text="resposta do modelo",
            input_tokens=11,
            output_tokens=22,
            finish_reason="stop",
        )
        self.error = error
        self.requests: list[LLMProviderRequest] = []

    @property
    def provider(self) -> ModelProviderEnum:
        """Retorna o provedor atendido pelo dublê."""
        return ModelProviderEnum.OPEN_ROUTER

    def verify_provider_settings(self) -> bool:
        """O dublê está sempre apto a responder."""
        return True

    async def generate_response(self, request: LLMProviderRequest) -> LLMProviderResponse:
        """Captura a requisição e devolve a resposta programada."""
        self.requests.append(request)

        if self.error is not None:
            raise self.error

        return self.response
