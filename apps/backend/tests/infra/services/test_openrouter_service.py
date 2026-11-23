"""O que é próprio da OpenRouter. O comportamento comum às três implementações está em
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
from src.infra.services.openrouter_service import OpenRouterService
from tests.infra.services.provider_spec import build_service


def _build_request() -> LLMProviderRequest:
    return LLMProviderRequest(
        llm_model=GenaiModel(model_name="vendor/modelo", model_provider=ModelProviderEnum.OPEN_ROUTER),
        messages=[LLMProviderMessage(role="user", content="pergunta")],
        max_tokens=100,
        temperature=0.3,
    )


def _build_service(**kwargs: Any) -> OpenRouterService:
    service = build_service(OpenRouterService, **kwargs)
    assert isinstance(service, OpenRouterService)
    return service


# ── Endpoint e headers ───────────────────────────────────────────────────────

async def test_chama_o_endpoint_configurado() -> None:
    capturadas: list[httpx.Request] = []
    service = _build_service(capturadas=capturadas, openrouter_api_url="https://openrouter.test/completions")

    await service.generate_response(request=_build_request())

    assert str(capturadas[0].url) == "https://openrouter.test/completions"


async def test_envia_authorization_e_headers_opcionais_quando_configurados() -> None:
    capturadas: list[httpx.Request] = []
    service = _build_service(
        capturadas=capturadas,
        openrouter_api_key="chave-secreta",
        openrouter_http_referer="https://referer.test",
        openrouter_x_title="Titulo",
    )

    await service.generate_response(request=_build_request())

    headers = capturadas[0].headers
    assert headers["Authorization"] == "Bearer chave-secreta"
    assert headers["HTTP-Referer"] == "https://referer.test"
    assert headers["X-Title"] == "Titulo"


async def test_omite_headers_opcionais_quando_nao_configurados() -> None:
    capturadas: list[httpx.Request] = []
    service = _build_service(capturadas=capturadas, openrouter_http_referer="", openrouter_x_title="")

    await service.generate_response(request=_build_request())

    headers = capturadas[0].headers
    assert "HTTP-Referer" not in headers
    assert "X-Title" not in headers


# ── Esforço de raciocínio ────────────────────────────────────────────────────
#
# A OpenRouter usa um bloco `reasoning` próprio, e não o `reasoning_effort` das demais
# APIs compatíveis com a OpenAI.

async def test_limita_o_esforco_de_raciocinio_quando_configurado() -> None:
    """`max_tokens` cobre raciocínio + resposta: sem limite, sobra zero para a resposta."""
    capturadas: list[httpx.Request] = []
    service = _build_service(capturadas=capturadas, llm_reasoning_effort="low")

    await service.generate_response(request=_build_request())

    enviado = json.loads(capturadas[0].content)
    assert enviado["reasoning"] == {"effort": "low"}
    assert "reasoning_effort" not in enviado


async def test_omite_o_bloco_de_raciocinio_quando_nao_configurado() -> None:
    capturadas: list[httpx.Request] = []
    service = _build_service(capturadas=capturadas, llm_reasoning_effort="")

    await service.generate_response(request=_build_request())

    assert "reasoning" not in json.loads(capturadas[0].content)


async def test_desliga_o_raciocinio_quando_esforco_e_minimal() -> None:
    """"minimal" não é um `effort` nativo de todo provedor (ex.: DeepSeek); a OpenRouter
    ignora o valor nesse caso e o modelo raciocina sem limite. `enabled: false` é o jeito
    que funciona em qualquer provedor para pedir zero raciocínio.
    """
    capturadas: list[httpx.Request] = []
    service = _build_service(capturadas=capturadas, llm_reasoning_effort="minimal")

    await service.generate_response(request=_build_request())

    assert json.loads(capturadas[0].content)["reasoning"] == {"enabled": False}


# ── Mensagens de erro ────────────────────────────────────────────────────────

async def test_erro_http_nomeia_a_openrouter() -> None:
    service = _build_service(body={"error": "rate limited"}, status_code=429)

    with pytest.raises(RuntimeError, match="OpenRouter API returned HTTP 429"):
        await service.generate_response(request=_build_request())
