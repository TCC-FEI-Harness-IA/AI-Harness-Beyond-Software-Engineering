"""Contrato comum às três implementações de chat completions.

Cada caso roda uma vez por provedor. O que é próprio de um provedor tem o seu próprio
arquivo (`test_openrouter_service.py`, `test_openai_service.py`,
`test_azure_ai_foundry_service.py`).
"""
import json
from typing import Any

import httpx
import pytest

from src.domain.entities.llm.genai_model import GenaiModel
from src.domain.entities.llm.llm_provider_message import LLMProviderMessage
from src.domain.entities.llm.llm_provider_request import LLMProviderRequest
from src.domain.errors.empty_completion_error import EmptyCompletionError
from src.infra.services.base_chat_completions_service import BaseChatCompletionsService
from tests.infra.services.provider_spec import (
    PROVIDER_SPECS,
    RESPOSTA_COMPLETA,
    ProviderSpec,
    build_service,
)

pytestmark = pytest.mark.parametrize("spec", PROVIDER_SPECS, ids=str)


def _build_request(spec: ProviderSpec, **overrides: Any) -> LLMProviderRequest:
    campos: dict[str, Any] = {
        "llm_model": GenaiModel(model_name="vendor/modelo", model_provider=spec.provider),
        "messages": [LLMProviderMessage(role="user", content="pergunta")],
        "max_tokens": 100,
        "temperature": 0.3,
    }
    campos.update(overrides)
    return LLMProviderRequest(**campos)


def _build(spec: ProviderSpec, **kwargs: Any) -> BaseChatCompletionsService:
    return build_service(spec.service_class, **kwargs)


# ── Contrato básico ──────────────────────────────────────────────────────────

def test_declara_o_provedor_atendido(spec: ProviderSpec) -> None:
    assert _build(spec).provider is spec.provider


def test_configuracao_valida_quando_ha_credencial(spec: ProviderSpec) -> None:
    assert _build(spec, **{spec.api_key_setting: "chave"}).verify_provider_settings() is True


def test_configuracao_invalida_quando_a_credencial_esta_vazia(spec: ProviderSpec) -> None:
    assert _build(spec, **{spec.api_key_setting: ""}).verify_provider_settings() is False


# ── Validações de entrada ────────────────────────────────────────────────────

async def test_chamada_sem_credencial_e_recusada_citando_a_variavel(spec: ProviderSpec) -> None:
    service = _build(spec, **{spec.api_key_setting: ""})

    with pytest.raises(ValueError, match=spec.api_key_variable):
        await service.generate_response(request=_build_request(spec))


async def test_provedor_diferente_do_atendido_e_recusado(spec: ProviderSpec) -> None:
    outro_provedor: Any = "outro_provedor"
    modelo_de_outro_provedor = GenaiModel(model_name="vendor/modelo", model_provider=outro_provedor)

    with pytest.raises(ValueError, match=spec.provider.name):
        await _build(spec).generate_response(request=_build_request(spec, llm_model=modelo_de_outro_provedor))


@pytest.mark.parametrize("model_name", ["", "   "])
async def test_nome_de_modelo_em_branco_e_recusado(spec: ProviderSpec, model_name: str) -> None:
    modelo = GenaiModel(model_name=model_name, model_provider=spec.provider)

    with pytest.raises(ValueError, match="model_name"):
        await _build(spec).generate_response(request=_build_request(spec, llm_model=modelo))


@pytest.mark.parametrize("max_tokens", [0, -1])
async def test_max_tokens_nao_positivo_e_recusado(spec: ProviderSpec, max_tokens: int) -> None:
    with pytest.raises(ValueError, match="max_tokens"):
        await _build(spec).generate_response(request=_build_request(spec, max_tokens=max_tokens))


async def test_conversa_vazia_e_recusada(spec: ProviderSpec) -> None:
    with pytest.raises(ValueError, match="at least one message"):
        await _build(spec).generate_response(request=_build_request(spec, messages=[]))


async def test_papel_em_branco_e_recusado(spec: ProviderSpec) -> None:
    mensagens = [LLMProviderMessage(role="   ", content="pergunta")]

    with pytest.raises(ValueError, match="role"):
        await _build(spec).generate_response(request=_build_request(spec, messages=mensagens))


async def test_conteudo_em_branco_e_recusado(spec: ProviderSpec) -> None:
    mensagens = [LLMProviderMessage(role="user", content="   ")]

    with pytest.raises(ValueError, match="content"):
        await _build(spec).generate_response(request=_build_request(spec, messages=mensagens))


# ── Resposta bem-sucedida ────────────────────────────────────────────────────

async def test_extrai_texto_tokens_e_motivo_de_termino(spec: ProviderSpec) -> None:
    resposta = await _build(spec).generate_response(request=_build_request(spec))

    assert resposta.output_text == "resposta do modelo"
    assert resposta.input_tokens == 11
    assert resposta.output_tokens == 22
    assert resposta.finish_reason == "stop"
    assert resposta.raw_response == RESPOSTA_COMPLETA


async def test_conteudo_como_lista_de_blocos_de_texto_e_concatenado(spec: ProviderSpec) -> None:
    body = {
        "choices": [
            {
                "message": {
                    "content": [
                        {"type": "text", "text": "parte 1 "},
                        {"type": "image", "text": "ignorado"},
                        {"type": "text", "text": "parte 2"},
                    ]
                }
            }
        ]
    }

    resposta = await _build(spec, body=body).generate_response(request=_build_request(spec))

    assert resposta.output_text == "parte 1 parte 2"


async def test_conteudo_como_lista_de_strings_e_concatenado(spec: ProviderSpec) -> None:
    body = {"choices": [{"message": {"content": ["parte 1 ", "parte 2"]}}]}

    resposta = await _build(spec, body=body).generate_response(request=_build_request(spec))

    assert resposta.output_text == "parte 1 parte 2"


async def test_conteudo_de_tipo_inesperado_e_convertido_para_texto(spec: ProviderSpec) -> None:
    body = {"choices": [{"message": {"content": 42}}]}

    resposta = await _build(spec, body=body).generate_response(request=_build_request(spec))

    assert resposta.output_text == "42"


# ── Completion sem conteúdo ──────────────────────────────────────────────────
#
# Uma resposta em branco não pode seguir o fluxo: no baseline ela chegaria ao usuário como
# resposta vazia e no harness gastaria todas as retentativas de parsing sobre um texto que
# nunca existiu ("Nenhum objeto JSON válido foi encontrado na saída").

@pytest.mark.parametrize(
    "body",
    [
        {},
        {"choices": []},
        {"choices": "nao-e-lista"},
        {"choices": ["nao-e-dict"]},
        {"choices": [{}]},
        {"choices": [{"message": "nao-e-dict"}]},
        {"choices": [{"message": {"content": ""}}]},
        {"choices": [{"message": {"content": "   \n  "}}]},
        {"choices": [{"message": {"content": []}}]},
    ],
)
async def test_respostas_sem_conteudo_utilizavel_sao_recusadas(
    spec: ProviderSpec, body: dict[str, Any]
) -> None:
    with pytest.raises(EmptyCompletionError):
        await _build(spec, body=body).generate_response(request=_build_request(spec))


async def test_content_nulo_nao_vira_a_string_none(spec: ProviderSpec) -> None:
    """Regressão: `str(None)` entregava a string literal "None" como resposta do modelo."""
    body = {"choices": [{"message": {"content": None, "reasoning": "pensou e não escreveu"}}]}

    with pytest.raises(EmptyCompletionError) as excinfo:
        await _build(spec, body=body).generate_response(request=_build_request(spec))

    assert "None" not in str(excinfo.value).replace("'None'", "")


async def test_completion_truncada_por_teto_de_tokens_explica_a_causa(spec: ProviderSpec) -> None:
    """Modelo de raciocínio que gasta todo o `max_tokens` pensando: `content` nulo e 'length'."""
    body = {
        "choices": [{"message": {"content": None, "reasoning": "..."}, "finish_reason": "length"}],
        "usage": {"prompt_tokens": 114, "completion_tokens": 1200},
    }

    with pytest.raises(EmptyCompletionError) as excinfo:
        await _build(spec, body=body).generate_response(request=_build_request(spec))

    assert excinfo.value.finish_reason == "length"
    assert "max_tokens" in str(excinfo.value)
    assert "LLM_REASONING_EFFORT" in str(excinfo.value)


async def test_apenas_blocos_sem_texto_sao_recusados(spec: ProviderSpec) -> None:
    body = {"choices": [{"message": {"content": [{"type": "image", "text": "ignorado"}]}}]}

    with pytest.raises(EmptyCompletionError):
        await _build(spec, body=body).generate_response(request=_build_request(spec))


async def test_usage_ausente_zera_os_tokens(spec: ProviderSpec) -> None:
    body = {"choices": [{"message": {"content": "texto"}}]}

    resposta = await _build(spec, body=body).generate_response(request=_build_request(spec))

    assert resposta.input_tokens == 0
    assert resposta.output_tokens == 0


async def test_usage_de_tipo_invalido_zera_os_tokens(spec: ProviderSpec) -> None:
    body = {"choices": [{"message": {"content": "texto"}}], "usage": "nao-e-dict"}

    resposta = await _build(spec, body=body).generate_response(request=_build_request(spec))

    assert resposta.input_tokens == 0
    assert resposta.output_tokens == 0


async def test_tokens_nulos_no_usage_viram_zero(spec: ProviderSpec) -> None:
    body = {
        "choices": [{"message": {"content": "texto"}}],
        "usage": {"prompt_tokens": None, "completion_tokens": None},
    }

    resposta = await _build(spec, body=body).generate_response(request=_build_request(spec))

    assert resposta.input_tokens == 0
    assert resposta.output_tokens == 0


# ── Falhas de transporte ─────────────────────────────────────────────────────

async def test_erro_http_vira_runtime_error_com_status_e_corpo(spec: ProviderSpec) -> None:
    service = _build(spec, body={"error": "rate limited"}, status_code=429)

    with pytest.raises(RuntimeError, match="429"):
        await service.generate_response(request=_build_request(spec))


async def test_falha_de_conexao_vira_runtime_error(spec: ProviderSpec) -> None:
    service = _build(spec, erro=httpx.ConnectError("sem rede"))

    with pytest.raises(RuntimeError, match="Failed to connect"):
        await service.generate_response(request=_build_request(spec))


async def test_payload_que_nao_e_objeto_json_e_recusado(spec: ProviderSpec) -> None:
    service = _build(spec, body=["nao", "e", "objeto"])

    with pytest.raises(RuntimeError, match="invalid payload"):
        await service.generate_response(request=_build_request(spec))


# ── Payload enviado ──────────────────────────────────────────────────────────

async def test_envia_o_payload_base_de_chat_completions(spec: ProviderSpec) -> None:
    capturadas: list[httpx.Request] = []

    await _build(spec, capturadas=capturadas).generate_response(request=_build_request(spec))

    payload = json.loads(capturadas[0].content)
    assert payload["model"] == "vendor/modelo"
    assert payload["messages"] == [{"role": "user", "content": "pergunta"}]
    assert payload["max_tokens"] == 100
    assert payload["temperature"] == 0.3


async def test_usa_o_timeout_unificado_de_todos_os_provedores(spec: ProviderSpec) -> None:
    capturadas: list[httpx.Request] = []

    await _build(spec, capturadas=capturadas, llm_timeout_seconds=12.5).generate_response(
        request=_build_request(spec)
    )

    assert capturadas[0].extensions["timeout"]["read"] == 12.5
