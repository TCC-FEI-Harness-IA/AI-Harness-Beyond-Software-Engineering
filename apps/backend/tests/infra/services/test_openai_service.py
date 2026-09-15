"""O que é próprio da OpenAI. O comportamento comum às três implementações está em
`test_chat_completions_contract.py`.
"""
import json
from typing import Any

import httpx
import pytest

from src.domain.entities.llm.genai_model import GenaiModel
from src.domain.entities.llm.llm_provider_message import LLMProviderMessage
from src.domain.entities.llm.llm_provider_request import LLMProviderRequest
from src.domain.enums.model_provider_enum import ModelProviderEnum
from src.infra.services.openai_service import OpenAIService
from tests.infra.services.provider_spec import build_service


def _build_request() -> LLMProviderRequest:
    return LLMProviderRequest(
        llm_model=GenaiModel(model_name="gpt-4o-mini", model_provider=ModelProviderEnum.OPENAI),
        messages=[LLMProviderMessage(role="user", content="pergunta")],
        max_tokens=100,
        temperature=0.3,
    )


def _build_service(**kwargs: Any) -> OpenAIService:
    service = build_service(OpenAIService, **kwargs)
    assert isinstance(service, OpenAIService)
    return service


# ── Endpoint e headers ───────────────────────────────────────────────────────

async def test_chama_o_endpoint_configurado() -> None:
    capturadas: list[httpx.Request] = []
    service = _build_service(capturadas=capturadas, openai_api_url="https://openai.test/v1/chat/completions")

    await service.generate_response(request=_build_request())

    assert str(capturadas[0].url) == "https://openai.test/v1/chat/completions"


async def test_envia_a_chave_no_header_authorization() -> None:
    capturadas: list[httpx.Request] = []
    service = _build_service(capturadas=capturadas, openai_api_key="sk-chave-secreta")

    await service.generate_response(request=_build_request())

    assert capturadas[0].headers["Authorization"] == "Bearer sk-chave-secreta"


async def test_envia_a_organizacao_quando_configurada() -> None:
    capturadas: list[httpx.Request] = []
    service = _build_service(capturadas=capturadas, openai_organization="org-123")

    await service.generate_response(request=_build_request())

    assert capturadas[0].headers["OpenAI-Organization"] == "org-123"


async def test_omite_a_organizacao_quando_nao_configurada() -> None:
    capturadas: list[httpx.Request] = []
    service = _build_service(capturadas=capturadas, openai_organization="")

    await service.generate_response(request=_build_request())

    assert "OpenAI-Organization" not in capturadas[0].headers


# ── Esforço de raciocínio ────────────────────────────────────────────────────

async def test_envia_o_esforco_de_raciocinio_como_parametro_nativo() -> None:
    capturadas: list[httpx.Request] = []
    service = _build_service(capturadas=capturadas, llm_reasoning_effort="low")

    await service.generate_response(request=_build_request())

    assert json.loads(capturadas[0].content)["reasoning_effort"] == "low"


async def test_omite_o_esforco_de_raciocinio_quando_nao_configurado() -> None:
    capturadas: list[httpx.Request] = []
    service = _build_service(capturadas=capturadas, llm_reasoning_effort="")

    await service.generate_response(request=_build_request())

    assert "reasoning_effort" not in json.loads(capturadas[0].content)


# ── Mensagens de erro ────────────────────────────────────────────────────────

async def test_erro_http_nomeia_a_openai() -> None:
    service = _build_service(body={"error": "rate limited"}, status_code=429)

    with pytest.raises(RuntimeError, match="OpenAI API returned HTTP 429"):
        await service.generate_response(request=_build_request())
