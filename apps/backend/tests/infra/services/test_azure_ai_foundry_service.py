"""O que é próprio do Azure AI Foundry. O comportamento comum às três implementações está
em `test_chat_completions_contract.py`.
"""
import json
from typing import Any

import httpx
import pytest

from src.domain.entities.llm.genai_model import GenaiModel
from src.domain.entities.llm.llm_provider_message import LLMProviderMessage
from src.domain.entities.llm.llm_provider_request import LLMProviderRequest
from src.domain.enums.model_provider_enum import ModelProviderEnum
from src.infra.services.azure_ai_foundry_service import AzureAIFoundryService
from tests.infra.services.provider_spec import build_service

_ENDPOINT = "https://recurso.services.ai.azure.com"


def _build_request(model_name: str = "gpt-4o-mini") -> LLMProviderRequest:
    return LLMProviderRequest(
        llm_model=GenaiModel(model_name=model_name, model_provider=ModelProviderEnum.AZURE_AI_FOUNDRY),
        messages=[LLMProviderMessage(role="user", content="pergunta")],
        max_tokens=100,
        temperature=0.3,
    )


def _build_service(**kwargs: Any) -> AzureAIFoundryService:
    service = build_service(AzureAIFoundryService, **kwargs)
    assert isinstance(service, AzureAIFoundryService)
    return service


# ── URL do deployment ────────────────────────────────────────────────────────

async def test_monta_a_url_com_endpoint_deployment_e_versao_da_api() -> None:
    capturadas: list[httpx.Request] = []
    service = _build_service(
        capturadas=capturadas,
        azure_ai_foundry_endpoint=_ENDPOINT,
        azure_ai_foundry_deployment="meu-deployment",
        azure_ai_foundry_api_version="2024-10-21",
    )

    await service.generate_response(request=_build_request())

    assert str(capturadas[0].url) == (
        f"{_ENDPOINT}/openai/deployments/meu-deployment/chat/completions?api-version=2024-10-21"
    )


async def test_sem_deployment_configurado_usa_o_nome_do_modelo() -> None:
    """No Foundry é comum nomear o deployment com o nome do modelo — aí a variável sobra."""
    capturadas: list[httpx.Request] = []
    service = _build_service(
        capturadas=capturadas,
        azure_ai_foundry_endpoint=_ENDPOINT,
        azure_ai_foundry_deployment="",
    )

    await service.generate_response(request=_build_request(model_name="gpt-4o-mini"))

    assert "/openai/deployments/gpt-4o-mini/chat/completions" in str(capturadas[0].url)


async def test_o_deployment_configurado_vence_o_nome_do_modelo() -> None:
    capturadas: list[httpx.Request] = []
    service = _build_service(
        capturadas=capturadas,
        azure_ai_foundry_endpoint=_ENDPOINT,
        azure_ai_foundry_deployment="deployment-de-producao",
    )

    await service.generate_response(request=_build_request(model_name="gpt-4o-mini"))

    assert "/openai/deployments/deployment-de-producao/chat/completions" in str(capturadas[0].url)


# ── Autenticação ─────────────────────────────────────────────────────────────

async def test_autentica_pelo_header_api_key() -> None:
    capturadas: list[httpx.Request] = []
    service = _build_service(capturadas=capturadas, azure_ai_foundry_api_key="chave-azure")

    await service.generate_response(request=_build_request())

    headers = capturadas[0].headers
    assert headers["api-key"] == "chave-azure"
    assert "Authorization" not in headers


# ── Configuração obrigatória ─────────────────────────────────────────────────

def test_endpoint_ausente_invalida_a_configuracao() -> None:
    service = _build_service(azure_ai_foundry_endpoint="")

    assert service.verify_provider_settings() is False


async def test_chamada_sem_endpoint_e_recusada_citando_a_variavel() -> None:
    service = _build_service(azure_ai_foundry_endpoint="")

    with pytest.raises(ValueError, match="AZURE_AI_FOUNDRY_ENDPOINT"):
        await service.generate_response(request=_build_request())


async def test_erro_lista_todas_as_variaveis_faltantes() -> None:
    service = _build_service(azure_ai_foundry_endpoint="", azure_ai_foundry_api_key="")

    with pytest.raises(ValueError) as excinfo:
        await service.generate_response(request=_build_request())

    assert "AZURE_AI_FOUNDRY_ENDPOINT" in str(excinfo.value)
    assert "AZURE_AI_FOUNDRY_API_KEY" in str(excinfo.value)


# ── Esforço de raciocínio ────────────────────────────────────────────────────

async def test_envia_o_esforco_de_raciocinio_como_parametro_nativo() -> None:
    capturadas: list[httpx.Request] = []
    service = _build_service(capturadas=capturadas, llm_reasoning_effort="medium")

    await service.generate_response(request=_build_request())

    assert json.loads(capturadas[0].content)["reasoning_effort"] == "medium"


async def test_omite_o_esforco_de_raciocinio_quando_nao_configurado() -> None:
    capturadas: list[httpx.Request] = []
    service = _build_service(capturadas=capturadas, llm_reasoning_effort="")

    await service.generate_response(request=_build_request())

    assert "reasoning_effort" not in json.loads(capturadas[0].content)


# ── Mensagens de erro ────────────────────────────────────────────────────────

async def test_erro_http_nomeia_o_azure_ai_foundry() -> None:
    service = _build_service(body={"error": "rate limited"}, status_code=429)

    with pytest.raises(RuntimeError, match="Azure AI Foundry API returned HTTP 429"):
        await service.generate_response(request=_build_request())
