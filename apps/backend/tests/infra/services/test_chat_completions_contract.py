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


# ── Validação local sem rede ─────────────────────────────────────────────────

def test_validate_request_aceita_requisicao_valida_sem_chamar_a_rede(spec: ProviderSpec) -> None:
    capturadas: list[httpx.Request] = []

    _build(spec, capturadas=capturadas).validate_request(request=_build_request(spec))

    assert capturadas == []


def test_validate_request_recusa_credencial_ausente_citando_a_variavel(spec: ProviderSpec) -> None:
    capturadas: list[httpx.Request] = []
    service = _build(spec, capturadas=capturadas, **{spec.api_key_setting: ""})

    with pytest.raises(ValueError, match=spec.api_key_variable):
        service.validate_request(request=_build_request(spec))

    assert capturadas == []


def test_validate_request_recusa_conteudo_em_branco(spec: ProviderSpec) -> None:
    mensagens = [LLMProviderMessage(role="user", content="  ")]

    with pytest.raises(ValueError, match="content"):
        _build(spec).validate_request(request=_build_request(spec, messages=mensagens))


# ── Resposta bem-sucedida ────────────────────────────────────────────────────

async def test_extrai_texto_tokens_e_motivo_de_termino(spec: ProviderSpec) -> None:
    resposta = await _build(spec).generate_response(request=_build_request(spec))

    assert resposta.output_text == "resposta do modelo"
    assert resposta.input_tokens == 11
    assert resposta.output_tokens == 22
    assert resposta.finish_reason == "stop"
    assert resposta.raw_response == RESPOSTA_COMPLETA


async def test_extrai_o_identificador_da_resposta_do_provedor(spec: ProviderSpec) -> None:
    body = {"id": "gen-9", "choices": [{"message": {"content": "texto"}}]}

    resposta = await _build(spec, body=body).generate_response(request=_build_request(spec))

    assert resposta.response_id == "gen-9"


async def test_identificador_ausente_fica_vazio(spec: ProviderSpec) -> None:
    body = {"choices": [{"message": {"content": "texto"}}]}

    resposta = await _build(spec, body=body).generate_response(request=_build_request(spec))

    assert resposta.response_id is None


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


async def test_completion_vazia_preserva_o_consumo_informado_pelo_provedor(spec: ProviderSpec) -> None:
    """A chamada custou mesmo sem texto: o uso do provedor viaja no erro, em vez de ser descartado."""
    body = {
        "id": "gen-123",
        "choices": [{"message": {"content": None}, "finish_reason": "length"}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 40},
    }

    with pytest.raises(EmptyCompletionError) as excinfo:
        await _build(spec, body=body).generate_response(request=_build_request(spec))

    assert excinfo.value.tokens_input == 100
    assert excinfo.value.tokens_output == 40
    assert excinfo.value.response_id == "gen-123"


@pytest.mark.parametrize("usage", [None, "nao-e-dict", {}, {"prompt_tokens": None, "completion_tokens": None}])
async def test_completion_vazia_sem_uso_informado_deixa_o_consumo_desconhecido(
    spec: ProviderSpec, usage: Any
) -> None:
    body: dict[str, Any] = {"choices": [{"message": {"content": ""}}]}
    if usage is not None:
        body["usage"] = usage

    with pytest.raises(EmptyCompletionError) as excinfo:
        await _build(spec, body=body).generate_response(request=_build_request(spec))

    assert excinfo.value.tokens_input is None
    assert excinfo.value.tokens_output is None
    assert excinfo.value.response_id is None


async def test_completion_vazia_com_apenas_um_dos_consumos_preserva_so_esse(spec: ProviderSpec) -> None:
    body = {"choices": [{"message": {"content": ""}}], "usage": {"completion_tokens": 7}}

    with pytest.raises(EmptyCompletionError) as excinfo:
        await _build(spec, body=body).generate_response(request=_build_request(spec))

    assert excinfo.value.tokens_input is None
    assert excinfo.value.tokens_output == 7


async def test_apenas_blocos_sem_texto_sao_recusados(spec: ProviderSpec) -> None:
    body = {"choices": [{"message": {"content": [{"type": "image", "text": "ignorado"}]}}]}

    with pytest.raises(EmptyCompletionError):
        await _build(spec, body=body).generate_response(request=_build_request(spec))


async def test_usage_ausente_deixa_os_dois_contadores_desconhecidos(spec: ProviderSpec) -> None:
    body = {"choices": [{"message": {"content": "texto"}}]}

    resposta = await _build(spec, body=body).generate_response(request=_build_request(spec))

    assert resposta.input_tokens is None
    assert resposta.output_tokens is None


async def test_usage_de_tipo_invalido_deixa_os_contadores_desconhecidos(spec: ProviderSpec) -> None:
    body = {"choices": [{"message": {"content": "texto"}}], "usage": "nao-e-dict"}

    resposta = await _build(spec, body=body).generate_response(request=_build_request(spec))

    assert resposta.input_tokens is None
    assert resposta.output_tokens is None


async def test_tokens_nulos_no_usage_continuam_desconhecidos(spec: ProviderSpec) -> None:
    body = {
        "choices": [{"message": {"content": "texto"}}],
        "usage": {"prompt_tokens": None, "completion_tokens": None},
    }

    resposta = await _build(spec, body=body).generate_response(request=_build_request(spec))

    assert resposta.input_tokens is None
    assert resposta.output_tokens is None


async def test_uso_parcial_so_a_entrada_preserva_a_saida_como_desconhecida(spec: ProviderSpec) -> None:
    body = {"choices": [{"message": {"content": "texto"}}], "usage": {"prompt_tokens": 10}}

    resposta = await _build(spec, body=body).generate_response(request=_build_request(spec))

    assert resposta.input_tokens == 10
    assert resposta.output_tokens is None


async def test_uso_parcial_so_a_saida_preserva_a_entrada_como_desconhecida(spec: ProviderSpec) -> None:
    body = {"choices": [{"message": {"content": "texto"}}], "usage": {"completion_tokens": 7}}

    resposta = await _build(spec, body=body).generate_response(request=_build_request(spec))

    assert resposta.input_tokens is None
    assert resposta.output_tokens == 7


async def test_zero_informado_pelo_provedor_continua_sendo_zero_conhecido(spec: ProviderSpec) -> None:
    body = {
        "choices": [{"message": {"content": "texto"}}],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0},
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


async def test_envia_a_temperatura_zero_e_fracionaria_sem_arredondar(spec: ProviderSpec) -> None:
    for temperatura in (0, 0.25, 0.66):
        capturadas: list[httpx.Request] = []

        await _build(spec, capturadas=capturadas).generate_response(
            request=_build_request(spec, temperature=temperatura)
        )

        assert json.loads(capturadas[0].content)["temperature"] == temperatura
