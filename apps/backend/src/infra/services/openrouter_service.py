import logging
from typing import Any

import httpx

from src.domain.entities.llm.llm_provider_request import LLMProviderRequest
from src.domain.enums.model_provider_enum import ModelProviderEnum
from src.domain.interfaces.settings_interface import ISettings
from src.domain.services.execution_authorization import ExecutionAuthorization
from src.infra.services.base_chat_completions_service import BaseChatCompletionsService

USER_CREDENTIAL_LABEL = "user OpenRouter API key"
_MINIMAL_EFFORT = "minimal"


class OpenRouterService(BaseChatCompletionsService):
    """Integração com a API de chat completions da OpenRouter, com a chave do usuário.

    A chave vem exclusivamente da autorização da execução (cookie cifrado decifrado na requisição),
    nunca da configuração do servidor. Cada requisição ou execução tem a sua instância, então
    execuções simultâneas nunca compartilham credencial. Antes de cada chamada a autorização é
    conferida: depois do fim da sessão ou de uma revogação, nenhuma chamada sai.
    """

    def __init__(
        self,
        logger: logging.Logger,
        settings: ISettings,
        authorization: ExecutionAuthorization | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        """Inicializa o serviço.

        Args:
            logger: Logger do módulo.
            settings: Configurações da aplicação (endpoint, timeout, raciocínio).
            authorization: Autorização da execução, com a credencial do usuário.
            transport: Transporte HTTP alternativo, para testes.
        """
        super().__init__(logger=logger, settings=settings, transport=transport)
        self.authorization = authorization

    @property
    def provider(self) -> ModelProviderEnum:
        """Retorna o provedor suportado pelo serviço."""
        return ModelProviderEnum.OPEN_ROUTER

    @property
    def provider_label(self) -> str:
        """Nome do provedor como aparece nas mensagens de erro."""
        return "OpenRouter"

    def missing_settings(self) -> list[str]:
        """Sem autorização não há credencial: a chave do servidor nunca é usada como alternativa."""
        return [] if self.authorization is not None else [USER_CREDENTIAL_LABEL]

    def validate_request(self, request: LLMProviderRequest) -> None:
        """Valida localmente a requisição e a vigência da autorização.

        Raises:
            ValueError: Configuração ou requisição inválidas.
            ExecutionNotAuthorizedError: Sessão expirada ou revogada (subclasse de `ValueError`).
        """
        super().validate_request(request=request)
        assert self.authorization is not None
        self.authorization.ensure_active()

    def completions_url(self, request: LLMProviderRequest) -> str:
        """Devolve o endpoint configurado — o mesmo para qualquer modelo."""
        return self.settings.openrouter_api_url

    async def authorize_request(self) -> None:
        """Revalida a sessão no auth antes de cada chamada, sem esperar pelo observador WebSocket."""
        assert self.authorization is not None
        await self.authorization.revalidate()

    def headers(self) -> dict[str, str]:
        """Monta os headers com a chave do usuário e a identificação opcional do app."""
        assert self.authorization is not None
        headers = {
            "Authorization": f"Bearer {self.authorization.credential.api_key}",
            "Content-Type": "application/json",
        }

        http_referer = self.settings.openrouter_http_referer
        if http_referer:
            headers["HTTP-Referer"] = http_referer

        title = self.settings.openrouter_x_title
        if title:
            headers["X-Title"] = title

        return headers

    def redact(self, text: str) -> str:
        """Remove a chave do usuário de textos que viram mensagem de erro."""
        return self.authorization.credential.redact(text) if self.authorization is not None else text

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
