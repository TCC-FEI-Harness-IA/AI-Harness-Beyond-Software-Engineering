from src.domain.entities.llm.llm_provider_request import LLMProviderRequest
from src.domain.enums.model_provider_enum import ModelProviderEnum
from src.infra.services.base_chat_completions_service import BaseChatCompletionsService

_API_KEY_VARIABLE = "OPENAI_API_KEY"


class OpenAIService(BaseChatCompletionsService):
    """Integração com a API de chat completions da OpenAI."""

    @property
    def provider(self) -> ModelProviderEnum:
        """Retorna o provedor suportado pelo serviço."""
        return ModelProviderEnum.OPENAI

    @property
    def provider_label(self) -> str:
        """Nome do provedor como aparece nas mensagens de erro."""
        return "OpenAI"

    def missing_settings(self) -> list[str]:
        """Lista as variáveis obrigatórias da OpenAI que estão sem valor."""
        if self.settings.openai_api_key:
            return []
        return [_API_KEY_VARIABLE]

    def completions_url(self, request: LLMProviderRequest) -> str:
        """Devolve o endpoint configurado — o mesmo para qualquer modelo."""
        return self.settings.openai_api_url

    def headers(self) -> dict[str, str]:
        """Monta os headers da requisição, com a autenticação por bearer token.

        `OpenAI-Organization` é opcional: só faz diferença em contas que pertencem a mais
        de uma organização, onde ela decide a qual atribuir o consumo.
        """
        headers = {
            "Authorization": f"Bearer {self.settings.openai_api_key}",
            "Content-Type": "application/json",
        }

        organization = self.settings.openai_organization
        if organization:
            headers["OpenAI-Organization"] = organization

        return headers
