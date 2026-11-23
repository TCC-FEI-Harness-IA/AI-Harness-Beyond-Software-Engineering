"""Descrição de cada implementação concreta de `BaseChatCompletionsService`.

Os três provedores expõem a mesma API de chat completions, então a maior parte do
comportamento é verificada uma única vez, parametrizada por estas especificações
(`test_chat_completions_contract.py`). O que é próprio de cada provedor — URL,
autenticação e vocabulário de parâmetros — tem o seu próprio arquivo de teste.
"""
import logging
from dataclasses import dataclass
from typing import Any

import httpx

from src.domain.enums.model_provider_enum import ModelProviderEnum
from src.infra.services.azure_ai_foundry_service import AzureAIFoundryService
from src.infra.services.base_chat_completions_service import BaseChatCompletionsService
from src.infra.services.openai_service import OpenAIService
from src.infra.services.openrouter_service import OpenRouterService
from tests.doubles.fake_settings import FakeSettings

RESPOSTA_COMPLETA: dict[str, Any] = {
    "choices": [{"message": {"content": "resposta do modelo"}, "finish_reason": "stop"}],
    "usage": {"prompt_tokens": 11, "completion_tokens": 22},
}


@dataclass(frozen=True)
class ProviderSpec:
    """Dados de um provedor necessários para exercer o contrato comum.

    Attributes:
        service_class: Implementação concreta sob teste.
        provider: Provedor atendido pela implementação.
        api_key_setting: Propriedade de `ISettings` que guarda a credencial.
        api_key_variable: Variável de ambiente correspondente, citada nos erros.
    """

    service_class: type[BaseChatCompletionsService]
    provider: ModelProviderEnum
    api_key_setting: str
    api_key_variable: str

    def __str__(self) -> str:
        """Identifica o caso parametrizado pelo provedor, e não pelo endereço do objeto."""
        return self.provider.value


PROVIDER_SPECS = (
    ProviderSpec(
        service_class=OpenRouterService,
        provider=ModelProviderEnum.OPEN_ROUTER,
        api_key_setting="openrouter_api_key",
        api_key_variable="OPENROUTER_API_KEY",
    ),
    ProviderSpec(
        service_class=OpenAIService,
        provider=ModelProviderEnum.OPENAI,
        api_key_setting="openai_api_key",
        api_key_variable="OPENAI_API_KEY",
    ),
    ProviderSpec(
        service_class=AzureAIFoundryService,
        provider=ModelProviderEnum.AZURE_AI_FOUNDRY,
        api_key_setting="azure_ai_foundry_api_key",
        api_key_variable="AZURE_AI_FOUNDRY_API_KEY",
    ),
)


def build_service(
    service_class: type[BaseChatCompletionsService],
    body: Any = None,
    status_code: int = 200,
    capturadas: list[httpx.Request] | None = None,
    erro: Exception | None = None,
    **settings_overrides: Any,
) -> BaseChatCompletionsService:
    """Monta um serviço com a camada de rede substituída por um transporte de teste.

    Args:
        service_class: Implementação concreta a instanciar.
        body: Corpo JSON devolvido pelo provedor simulado.
        status_code: Status HTTP devolvido pelo provedor simulado.
        capturadas: Lista que recebe cada requisição enviada, quando informada.
        erro: Exceção levantada pelo transporte em vez de responder.
        **settings_overrides: Sobrescritas aplicadas ao `FakeSettings`.

    Returns:
        BaseChatCompletionsService: Serviço pronto para uso em teste.
    """

    def handler(request: httpx.Request) -> httpx.Response:
        if capturadas is not None:
            capturadas.append(request)
        if erro is not None:
            raise erro
        return httpx.Response(status_code=status_code, json=body if body is not None else RESPOSTA_COMPLETA)

    return service_class(
        logger=logging.getLogger("teste"),
        settings=FakeSettings(**settings_overrides),
        transport=httpx.MockTransport(handler),
    )
