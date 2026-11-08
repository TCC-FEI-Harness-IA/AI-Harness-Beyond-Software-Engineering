from src.domain.entities.llm.llm_provider_request import LLMProviderRequest
from src.domain.enums.model_provider_enum import ModelProviderEnum
from src.infra.services.base_chat_completions_service import BaseChatCompletionsService

_ENDPOINT_VARIABLE = "AZURE_AI_FOUNDRY_ENDPOINT"
_API_KEY_VARIABLE = "AZURE_AI_FOUNDRY_API_KEY"


class AzureAIFoundryService(BaseChatCompletionsService):
    """Integração com a API de chat completions do Azure AI Foundry.

    Duas diferenças em relação aos demais provedores: o modelo não vive apenas no corpo
    da requisição — ele é o *deployment* que compõe a URL — e a autenticação usa o header
    `api-key`, e não um bearer token.
    """

    @property
    def provider(self) -> ModelProviderEnum:
        """Retorna o provedor suportado pelo serviço."""
        return ModelProviderEnum.AZURE_AI_FOUNDRY

    @property
    def provider_label(self) -> str:
        """Nome do provedor como aparece nas mensagens de erro."""
        return "Azure AI Foundry"

    def missing_settings(self) -> list[str]:
        """Lista as variáveis obrigatórias do Azure AI Foundry que estão sem valor.

        Diferente dos outros provedores, o endereço não tem default: cada recurso do
        Foundry tem o seu, então sem o endpoint não há chamada possível.
        """
        missing: list[str] = []

        if not self.settings.azure_ai_foundry_endpoint:
            missing.append(_ENDPOINT_VARIABLE)

        if not self.settings.azure_ai_foundry_api_key:
            missing.append(_API_KEY_VARIABLE)

        return missing

    def completions_url(self, request: LLMProviderRequest) -> str:
        """Monta a URL do deployment que atende o modelo pedido.

        Args:
            request: Payload técnico de envio da completion, fonte do nome do modelo
                usado como deployment quando não há um configurado.

        Returns:
            str: URL completa de chat completions do deployment.
        """
        deployment = self.settings.azure_ai_foundry_deployment or request.llm_model.model_name
        endpoint = self.settings.azure_ai_foundry_endpoint
        api_version = self.settings.azure_ai_foundry_api_version

        return f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"

    def headers(self) -> dict[str, str]:
        """Monta os headers da requisição, com a autenticação por chave de recurso."""
        return {
            "api-key": self.settings.azure_ai_foundry_api_key,
            "Content-Type": "application/json",
        }
