from typing import Any

from src.domain.entities.llm.llm_provider_request import LLMProviderRequest
from src.domain.enums.model_provider_enum import ModelProviderEnum
from src.infra.services.base_chat_completions_service import BaseChatCompletionsService

_API_KEY_VARIABLE = "OPENROUTER_API_KEY"
_MINIMAL_EFFORT = "minimal"


class OpenRouterService(BaseChatCompletionsService):
    """Integração com a API de chat completions da OpenRouter."""

    @property
    def provider(self) -> ModelProviderEnum:
        """Retorna o provedor suportado pelo serviço."""
        return ModelProviderEnum.OPEN_ROUTER

    @property
    def provider_label(self) -> str:
        """Nome do provedor como aparece nas mensagens de erro."""
        return "OpenRouter"

    def missing_settings(self) -> list[str]:
        """Lista as variáveis obrigatórias da OpenRouter que estão sem valor."""
        if self.settings.openrouter_api_key:
            return []
        return [_API_KEY_VARIABLE]

    def completions_url(self, request: LLMProviderRequest) -> str:
        """Devolve o endpoint configurado — o mesmo para qualquer modelo."""
        return self.settings.openrouter_api_url

    def headers(self) -> dict[str, str]:
        """Monta os headers da requisição, com a autenticação e a identificação do app.

        `HTTP-Referer` e `X-Title` são opcionais: a OpenRouter os usa apenas para atribuir
        o consumo a uma aplicação nos seus rankings.
        """
        headers = {
            "Authorization": f"Bearer {self.settings.openrouter_api_key}",
            "Content-Type": "application/json",
        }

        http_referer = self.settings.openrouter_http_referer
        if http_referer:
            headers["HTTP-Referer"] = http_referer

        title = self.settings.openrouter_x_title
        if title:
            headers["X-Title"] = title

        return headers

    def payload_extras(self, request: LLMProviderRequest) -> dict[str, Any]:
        """Traduz o esforço de raciocínio para o bloco `reasoning` próprio da OpenRouter.

        A OpenRouter não usa o `reasoning_effort` das demais APIs compatíveis com a OpenAI:
        ela expõe um bloco `reasoning` que também permite desligar o raciocínio por completo.
        """
        reasoning_effort = self.settings.llm_reasoning_effort
        if not reasoning_effort:
            return {}

        if reasoning_effort == _MINIMAL_EFFORT:
            # "minimal" só é um `effort` nativo da OpenAI; em outros provedores (como o
            # DeepSeek) a OpenRouter ignora o valor e o modelo raciocina sem limite,
            # consumindo todo o `max_tokens` antes de escrever a resposta. Desligar o
            # raciocínio via `enabled: false` é o jeito que funciona em qualquer provedor.
            return {"reasoning": {"enabled": False}}

        return {"reasoning": {"effort": reasoning_effort}}
