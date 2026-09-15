import logging
from typing import Any

import httpx
import pytest

from src.domain.entities.llm.genai_model import GenaiModel
from src.domain.entities.llm.llm_provider_message import LLMProviderMessage
from src.domain.entities.llm.llm_provider_request import LLMProviderRequest
from src.domain.enums.model_provider_enum import ModelProviderEnum
from src.domain.errors.empty_completion_error import EmptyCompletionError
from src.infra.services.openrouter_service import OpenRouterService
from tests.doubles.fake_settings import FakeSettings

_RESPOSTA_COMPLETA: dict[str, Any] = {
    "choices": [{"message": {"content": "resposta do modelo"}, "finish_reason": "stop"}],
    "usage": {"prompt_tokens": 11, "completion_tokens": 22},
}


def _build_request(**overrides: Any) -> LLMProviderRequest:
    campos: dict[str, Any] = {
        "llm_model": GenaiModel(model_name="vendor/modelo", model_provider=ModelProviderEnum.OPEN_ROUTER),
        "messages": [LLMProviderMessage(role="user", content="pergunta")],
        "max_tokens": 100,
        "temperature": 0.3,
    }
    campos.update(overrides)
    return LLMProviderRequest(**campos)


def _build_service(
    body: Any = None,
    status_code: int = 200,
    capturadas: list[httpx.Request] | None = None,
    erro: Exception | None = None,
    **settings_overrides: Any,
) -> OpenRouterService:
    def handler(request: httpx.Request) -> httpx.Response:
        if capturadas is not None:
            capturadas.append(request)
        if erro is not None:
            raise erro
        return httpx.Response(status_code=status_code, json=body if body is not None else _RESPOSTA_COMPLETA)

    return OpenRouterService(
        logger=logging.getLogger("teste"),
        settings=FakeSettings(**settings_overrides),
        transport=httpx.MockTransport(handler),
    )


# ── Contrato básico ──────────────────────────────────────────────────────────

def test_declara_o_provedor_atendido() -> None:
    assert _build_service().provider is ModelProviderEnum.OPEN_ROUTER


def test_configuracao_valida_quando_ha_api_key() -> None:
    assert _build_service(openrouter_api_key="chave").verify_provider_settings() is True


def test_configuracao_invalida_quando_a_api_key_esta_vazia() -> None:
    assert _build_service(openrouter_api_key="").verify_provider_settings() is False


# ── Validações de entrada ────────────────────────────────────────────────────

async def test_chamada_sem_api_key_e_recusada() -> None:
    service = _build_service(openrouter_api_key="")

    with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
        await service.generate_response(request=_build_request())


async def test_provedor_diferente_do_atendido_e_recusado() -> None:
    outro_provedor: Any = "outro_provedor"
    modelo_de_outro_provedor = GenaiModel(model_name="vendor/modelo", model_provider=outro_provedor)

    with pytest.raises(ValueError, match="OPEN_ROUTER"):
        await _build_service().generate_response(request=_build_request(llm_model=modelo_de_outro_provedor))


@pytest.mark.parametrize("model_name", ["", "   "])
async def test_nome_de_modelo_em_branco_e_recusado(model_name: str) -> None:
    modelo = GenaiModel(model_name=model_name, model_provider=ModelProviderEnum.OPEN_ROUTER)

    with pytest.raises(ValueError, match="model_name"):
        await _build_service().generate_response(request=_build_request(llm_model=modelo))


@pytest.mark.parametrize("max_tokens", [0, -1])
async def test_max_tokens_nao_positivo_e_recusado(max_tokens: int) -> None:
    with pytest.raises(ValueError, match="max_tokens"):
        await _build_service().generate_response(request=_build_request(max_tokens=max_tokens))


async def test_conversa_vazia_e_recusada() -> None:
    with pytest.raises(ValueError, match="at least one message"):
        await _build_service().generate_response(request=_build_request(messages=[]))


async def test_papel_em_branco_e_recusado() -> None:
    mensagens = [LLMProviderMessage(role="   ", content="pergunta")]

    with pytest.raises(ValueError, match="role"):
        await _build_service().generate_response(request=_build_request(messages=mensagens))


async def test_conteudo_em_branco_e_recusado() -> None:
    mensagens = [LLMProviderMessage(role="user", content="   ")]

    with pytest.raises(ValueError, match="content"):
        await _build_service().generate_response(request=_build_request(messages=mensagens))


# ── Resposta bem-sucedida ────────────────────────────────────────────────────

async def test_extrai_texto_tokens_e_motivo_de_termino() -> None:
    resposta = await _build_service().generate_response(request=_build_request())

    assert resposta.output_text == "resposta do modelo"
    assert resposta.input_tokens == 11
    assert resposta.output_tokens == 22
    assert resposta.finish_reason == "stop"
    assert resposta.raw_response == _RESPOSTA_COMPLETA


async def test_conteudo_como_lista_de_blocos_de_texto_e_concatenado() -> None:
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

    resposta = await _build_service(body=body).generate_response(request=_build_request())

    assert resposta.output_text == "parte 1 parte 2"


async def test_conteudo_como_lista_de_strings_e_concatenado() -> None:
    body = {"choices": [{"message": {"content": ["parte 1 ", "parte 2"]}}]}

    resposta = await _build_service(body=body).generate_response(request=_build_request())

    assert resposta.output_text == "parte 1 parte 2"


async def test_conteudo_de_tipo_inesperado_e_convertido_para_texto() -> None:
    body = {"choices": [{"message": {"content": 42}}]}

    resposta = await _build_service(body=body).generate_response(request=_build_request())

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
async def test_respostas_sem_conteudo_utilizavel_sao_recusadas(body: dict[str, Any]) -> None:
    with pytest.raises(EmptyCompletionError):
        await _build_service(body=body).generate_response(request=_build_request())


async def test_content_nulo_nao_vira_a_string_none() -> None:
    """Regressão: `str(None)` entregava a string literal "None" como resposta do modelo."""
    body = {"choices": [{"message": {"content": None, "reasoning": "pensou e não escreveu"}}]}

    with pytest.raises(EmptyCompletionError) as excinfo:
        await _build_service(body=body).generate_response(request=_build_request())

    assert "None" not in str(excinfo.value).replace("'None'", "")


async def test_completion_truncada_por_teto_de_tokens_explica_a_causa() -> None:
    """Modelo de raciocínio que gasta todo o `max_tokens` pensando: `content` nulo e 'length'."""
    body = {
        "choices": [{"message": {"content": None, "reasoning": "..."}, "finish_reason": "length"}],
        "usage": {"prompt_tokens": 114, "completion_tokens": 1200},
    }

    with pytest.raises(EmptyCompletionError) as excinfo:
        await _build_service(body=body).generate_response(request=_build_request())

    assert excinfo.value.finish_reason == "length"
    assert "max_tokens" in str(excinfo.value)
    assert "OPENROUTER_REASONING_EFFORT" in str(excinfo.value)


async def test_apenas_blocos_sem_texto_sao_recusados() -> None:
    body = {"choices": [{"message": {"content": [{"type": "image", "text": "ignorado"}]}}]}

    with pytest.raises(EmptyCompletionError):
        await _build_service(body=body).generate_response(request=_build_request())


async def test_usage_ausente_zera_os_tokens() -> None:
    body = {"choices": [{"message": {"content": "texto"}}]}

    resposta = await _build_service(body=body).generate_response(request=_build_request())

    assert resposta.input_tokens == 0
    assert resposta.output_tokens == 0


async def test_usage_de_tipo_invalido_zera_os_tokens() -> None:
    body = {"choices": [{"message": {"content": "texto"}}], "usage": "nao-e-dict"}

    resposta = await _build_service(body=body).generate_response(request=_build_request())

    assert resposta.input_tokens == 0
    assert resposta.output_tokens == 0


async def test_tokens_nulos_no_usage_viram_zero() -> None:
    body = {
        "choices": [{"message": {"content": "texto"}}],
        "usage": {"prompt_tokens": None, "completion_tokens": None},
    }

    resposta = await _build_service(body=body).generate_response(request=_build_request())

    assert resposta.input_tokens == 0
    assert resposta.output_tokens == 0


# ── Falhas de transporte ─────────────────────────────────────────────────────

async def test_erro_http_vira_runtime_error_com_status_e_corpo() -> None:
    service = _build_service(body={"error": "rate limited"}, status_code=429)

    with pytest.raises(RuntimeError, match="429"):
        await service.generate_response(request=_build_request())


async def test_falha_de_conexao_vira_runtime_error() -> None:
    service = _build_service(erro=httpx.ConnectError("sem rede"))

    with pytest.raises(RuntimeError, match="Failed to connect to OpenRouter API."):
        await service.generate_response(request=_build_request())


async def test_payload_que_nao_e_objeto_json_e_recusado() -> None:
    service = _build_service(body=["nao", "e", "objeto"])

    with pytest.raises(RuntimeError, match="invalid payload"):
        await service.generate_response(request=_build_request())


# ── Headers e payload enviados ───────────────────────────────────────────────

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


async def test_envia_o_payload_esperado_para_o_endpoint_configurado() -> None:
    import json

    capturadas: list[httpx.Request] = []
    service = _build_service(capturadas=capturadas, openrouter_api_url="https://openrouter.test/completions")

    await service.generate_response(request=_build_request())

    enviada = capturadas[0]
    payload = json.loads(enviada.content)
    assert str(enviada.url) == "https://openrouter.test/completions"
    assert payload["model"] == "vendor/modelo"
    assert payload["messages"] == [{"role": "user", "content": "pergunta"}]
    assert payload["max_tokens"] == 100
    assert payload["temperature"] == 0.3


async def test_limita_o_esforco_de_raciocinio_quando_configurado() -> None:
    """`max_tokens` cobre raciocínio + resposta: sem limite, sobra zero para a resposta."""
    import json

    capturadas: list[httpx.Request] = []
    service = _build_service(capturadas=capturadas, openrouter_reasoning_effort="low")

    await service.generate_response(request=_build_request())

    assert json.loads(capturadas[0].content)["reasoning"] == {"effort": "low"}


async def test_omite_o_bloco_de_raciocinio_quando_nao_configurado() -> None:
    import json

    capturadas: list[httpx.Request] = []
    service = _build_service(capturadas=capturadas, openrouter_reasoning_effort="")

    await service.generate_response(request=_build_request())

    assert "reasoning" not in json.loads(capturadas[0].content)


async def test_desliga_o_raciocinio_quando_esforco_e_minimal() -> None:
    """"minimal" não é um `effort` nativo de todo provedor (ex.: DeepSeek); a OpenRouter
    ignora o valor nesse caso e o modelo raciocina sem limite. `enabled: false` é o jeito
    que funciona em qualquer provedor para pedir zero raciocínio.
    """
    import json

    capturadas: list[httpx.Request] = []
    service = _build_service(capturadas=capturadas, openrouter_reasoning_effort="minimal")

    await service.generate_response(request=_build_request())

    assert json.loads(capturadas[0].content)["reasoning"] == {"enabled": False}
