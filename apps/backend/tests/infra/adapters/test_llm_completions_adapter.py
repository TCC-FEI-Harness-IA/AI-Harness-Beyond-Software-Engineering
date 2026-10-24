import logging
from datetime import UTC, datetime
from typing import Any

import pytest

from src.domain.entities.llm.llm_provider_response import LLMProviderResponse
from src.domain.entities.llm.message import Message
from src.domain.enums.message_source_enum import MessageSourceEnum
from src.domain.enums.model_provider_enum import ModelProviderEnum
from src.domain.errors.empty_completion_error import EmptyCompletionError
from src.infra.adapters.llm_completions_adapter import LLMCompletionsAdapter
from tests.doubles.fake_llm_service import FakeLLMService
from tests.doubles.fake_model_catalog import FakeModelCatalog
from tests.doubles.fake_settings import FakeSettings


def _build_message(text: str = "pergunta", source: MessageSourceEnum = MessageSourceEnum.USER) -> Message:
    return Message(creation_timestamp=datetime.now(tz=UTC), text=text, source=source)


def _build_adapter(
    llm_services: list[FakeLLMService] | None = None,
    model_catalog: FakeModelCatalog | None = None,
    **settings_overrides: Any,
) -> LLMCompletionsAdapter:
    return LLMCompletionsAdapter(
        llm_services=[FakeLLMService()] if llm_services is None else list(llm_services),
        model_catalog=model_catalog or FakeModelCatalog(),
        logger=logging.getLogger("teste"),
        settings=FakeSettings(**settings_overrides),
    )


def _build_all_providers() -> dict[ModelProviderEnum, FakeLLMService]:
    return {provider: FakeLLMService(provider=provider) for provider in ModelProviderEnum}


# ── Defaults e sobrescritas ──────────────────────────────────────────────────

async def test_sem_sobrescritas_usa_os_defaults_das_configuracoes() -> None:
    service = FakeLLMService()
    adapter = _build_adapter(
        llm_services=[service],
        llm_model="vendor/padrao",
        llm_max_tokens=512,
        llm_temperature=0.4,
    )

    await adapter.send_message(input_message=_build_message())

    enviada = service.requests[0]
    assert enviada.llm_model.model_name == "vendor/padrao"
    assert enviada.max_tokens == 512
    assert enviada.temperature == 0.4


async def test_sobrescritas_vencem_os_defaults() -> None:
    service = FakeLLMService()
    adapter = _build_adapter(llm_services=[service], llm_model="vendor/padrao")

    await adapter.send_message(
        input_message=_build_message(),
        model_name="vendor/especifico",
        max_tokens=64,
        temperature=0.1,
    )

    enviada = service.requests[0]
    assert enviada.llm_model.model_name == "vendor/especifico"
    assert enviada.max_tokens == 64
    assert enviada.temperature == 0.1


async def test_consulta_o_catalogo_de_modelos_antes_de_chamar_o_provedor() -> None:
    catalog = FakeModelCatalog()
    adapter = _build_adapter(model_catalog=catalog, llm_model="vendor/padrao")

    await adapter.send_message(input_message=_build_message())

    assert catalog.resolved == [("vendor/padrao", ModelProviderEnum.OPEN_ROUTER)]


async def test_modelo_recusado_pelo_catalogo_propaga_o_erro() -> None:
    catalog = FakeModelCatalog(error=ValueError("Model 'vendor/padrao' is not available."))
    adapter = _build_adapter(model_catalog=catalog)

    with pytest.raises(ValueError, match="is not available"):
        await adapter.send_message(input_message=_build_message())


# ── Escolha do provedor ──────────────────────────────────────────────────────

@pytest.mark.parametrize("provider", list(ModelProviderEnum))
async def test_a_chamada_vai_para_o_servico_do_provedor_pedido(provider: ModelProviderEnum) -> None:
    servicos = _build_all_providers()
    adapter = _build_adapter(llm_services=list(servicos.values()))

    await adapter.send_message(input_message=_build_message(), provider=provider)

    assert len(servicos[provider].requests) == 1
    assert all(not servico.requests for outro, servico in servicos.items() if outro is not provider)


@pytest.mark.parametrize("provider", list(ModelProviderEnum))
async def test_sem_provedor_na_chamada_usa_o_configurado(provider: ModelProviderEnum) -> None:
    servicos = _build_all_providers()
    adapter = _build_adapter(llm_services=list(servicos.values()), llm_provider=provider)

    await adapter.send_message(input_message=_build_message())

    assert len(servicos[provider].requests) == 1


async def test_o_provedor_escolhido_chega_ao_catalogo_e_ao_modelo() -> None:
    catalog = FakeModelCatalog()
    servicos = _build_all_providers()
    adapter = _build_adapter(llm_services=list(servicos.values()), model_catalog=catalog)

    await adapter.send_message(input_message=_build_message(), provider=ModelProviderEnum.OPENAI)

    assert catalog.resolved[0][1] is ModelProviderEnum.OPENAI
    assert servicos[ModelProviderEnum.OPENAI].requests[0].llm_model.model_provider is ModelProviderEnum.OPENAI


async def test_provedor_sem_servico_registrado_e_recusado() -> None:
    adapter = _build_adapter(llm_services=[FakeLLMService(provider=ModelProviderEnum.OPEN_ROUTER)])

    with pytest.raises(ValueError, match="openai"):
        await adapter.send_message(input_message=_build_message(), provider=ModelProviderEnum.OPENAI)


def test_provedor_padrao_sem_servico_registrado_e_recusado_na_construcao() -> None:
    """O erro aparece na composição, e não na primeira pergunta do usuário."""
    with pytest.raises(ValueError, match="openai"):
        _build_adapter(
            llm_services=[FakeLLMService(provider=ModelProviderEnum.OPEN_ROUTER)],
            llm_provider=ModelProviderEnum.OPENAI,
        )


def test_dois_servicos_para_o_mesmo_provedor_sao_recusados() -> None:
    servicos = [FakeLLMService(), FakeLLMService()]

    with pytest.raises(ValueError, match="open_router"):
        _build_adapter(llm_services=servicos)


def test_lista_de_servicos_vazia_e_recusada() -> None:
    with pytest.raises(ValueError, match="llm_services"):
        _build_adapter(llm_services=[])


# ── Validações ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("model_name", ["", "   "])
async def test_nome_de_modelo_em_branco_e_recusado(model_name: str) -> None:
    with pytest.raises(ValueError, match="model_name"):
        await _build_adapter().send_message(input_message=_build_message(), model_name=model_name)


def test_nome_de_modelo_padrao_em_branco_e_recusado_na_construcao() -> None:
    with pytest.raises(ValueError, match="model_name"):
        _build_adapter(llm_model="   ")


@pytest.mark.parametrize("max_tokens", [0, -5])
async def test_max_tokens_nao_positivo_e_recusado(max_tokens: int) -> None:
    with pytest.raises(ValueError, match="max_tokens"):
        await _build_adapter().send_message(input_message=_build_message(), max_tokens=max_tokens)


@pytest.mark.parametrize("temperature", [-0.1, 1.1])
async def test_temperatura_fora_do_intervalo_e_recusada(temperature: float) -> None:
    with pytest.raises(ValueError, match="temperature"):
        await _build_adapter().send_message(input_message=_build_message(), temperature=temperature)


@pytest.mark.parametrize("temperature", [float("nan"), float("inf")])
async def test_temperatura_nao_finita_e_recusada(temperature: float) -> None:
    with pytest.raises(ValueError, match="temperature"):
        await _build_adapter().send_message(input_message=_build_message(), temperature=temperature)


@pytest.mark.parametrize("temperature", [0, 0.25, 0.66])
async def test_temperatura_solicitada_chega_ao_servico_sem_arredondamento(temperature: float) -> None:
    service = FakeLLMService()

    await _build_adapter(llm_services=[service]).send_message(
        input_message=_build_message(), temperature=temperature
    )

    assert service.requests[0].temperature == temperature


async def test_temperatura_zero_nao_e_confundida_com_ausencia() -> None:
    service = FakeLLMService()

    await _build_adapter(llm_services=[service], llm_temperature=0.4).send_message(
        input_message=_build_message(), temperature=0
    )

    assert service.requests[0].temperature == 0


# ── Conversa multi-turno ─────────────────────────────────────────────────────

async def test_conversa_preserva_a_ordem_e_mapeia_os_papeis() -> None:
    service = FakeLLMService()
    conversa = [
        _build_message(text="pergunta", source=MessageSourceEnum.USER),
        _build_message(text="resposta anterior", source=MessageSourceEnum.LLM_AGENT),
        _build_message(text="instrucao", source=MessageSourceEnum.SYSTEM),
    ]

    await _build_adapter(llm_services=[service]).send_conversation(conversation=conversa)

    enviadas = service.requests[0].messages
    assert [(item.role, item.content) for item in enviadas] == [
        ("user", "pergunta"),
        ("assistant", "resposta anterior"),
        ("system", "instrucao"),
    ]


async def test_conversa_vazia_e_recusada() -> None:
    with pytest.raises(ValueError, match="conversation must contain at least one message."):
        await _build_adapter().send_conversation(conversation=[])


async def test_conversa_usa_a_ultima_mensagem_como_entrada_do_resultado() -> None:
    ultima = _build_message(text="ultima pergunta", source=MessageSourceEnum.USER)
    conversa = [_build_message(text="primeira", source=MessageSourceEnum.USER), ultima]

    resultado = await _build_adapter().send_conversation(conversation=conversa)

    assert resultado.input_message is ultima


# ── Resultado ────────────────────────────────────────────────────────────────

async def test_resultado_carrega_texto_tokens_e_origem_do_modelo() -> None:
    adapter = _build_adapter(llm_model="vendor/padrao")

    resultado = await adapter.send_message(input_message=_build_message())

    assert resultado.output_message is not None
    assert resultado.output_message.text == "resposta do modelo"
    assert resultado.output_message.source is MessageSourceEnum.LLM_AGENT
    assert resultado.tokens is not None
    assert resultado.tokens.tokens_input == 11
    assert resultado.tokens.tokens_output == 22
    assert resultado.tokens.llm_model.model_name == "vendor/padrao"


async def test_envio_simples_produz_exatamente_uma_chamada_ao_servico() -> None:
    service = FakeLLMService()

    await _build_adapter(llm_services=[service]).send_message(input_message=_build_message())

    assert len(service.requests) == 1
    assert len(service.requests[0].messages) == 1


async def test_repassa_motivo_de_termino_identificador_e_consumo_conhecido() -> None:
    service = FakeLLMService(
        response=LLMProviderResponse(
            output_text="texto", input_tokens=3, output_tokens=4, finish_reason="stop", response_id="gen-1"
        )
    )

    resultado = await _build_adapter(llm_services=[service]).send_message(input_message=_build_message())

    assert resultado.finish_reason == "stop"
    assert resultado.provider_response_id == "gen-1"
    assert (resultado.tokens.input_known, resultado.tokens.output_known) == (True, True)


async def test_consumo_desconhecido_do_provedor_e_sinalizado_nos_tokens() -> None:
    service = FakeLLMService(
        response=LLMProviderResponse(output_text="texto", input_tokens=None, output_tokens=None)
    )

    resultado = await _build_adapter(llm_services=[service]).send_message(input_message=_build_message())

    assert (resultado.tokens.input_known, resultado.tokens.output_known) == (False, False)
    assert (resultado.tokens.known_input, resultado.tokens.known_output) == (None, None)


async def test_consumo_parcial_do_provedor_e_sinalizado_por_contador() -> None:
    service = FakeLLMService(
        response=LLMProviderResponse(output_text="texto", input_tokens=10, output_tokens=None)
    )

    resultado = await _build_adapter(llm_services=[service]).send_message(input_message=_build_message())

    assert resultado.tokens.known_input == 10
    assert resultado.tokens.known_output is None
    assert resultado.tokens.tokens_output == 0


async def test_completion_vazia_do_servico_chega_intacta_ao_chamador() -> None:
    erro = EmptyCompletionError(finish_reason="length", tokens_input=10, tokens_output=5)
    service = FakeLLMService(error=erro)

    with pytest.raises(EmptyCompletionError) as excinfo:
        await _build_adapter(llm_services=[service]).send_message(input_message=_build_message())

    assert excinfo.value is erro


# ── Validação local anterior ao envio ────────────────────────────────────────


def test_validacao_local_aceita_uma_conversa_valida_sem_enviar_nada() -> None:
    service = FakeLLMService()

    _build_adapter(llm_services=[service]).validate_conversation(
        conversation=[_build_message(text="pergunta")], temperature=0
    )

    assert service.requests == []
    (validada,) = service.validated_requests
    assert validada.messages[0].content == "pergunta"
    assert validada.temperature == 0


def test_validacao_local_consulta_o_catalogo_com_o_modelo_e_o_provedor_pedidos() -> None:
    catalogo = FakeModelCatalog()
    services = _build_all_providers()

    _build_adapter(llm_services=list(services.values()), model_catalog=catalogo).validate_conversation(
        conversation=[_build_message()], model_name="vendor/outro", provider=ModelProviderEnum.OPENAI
    )

    assert catalogo.resolved == [("vendor/outro", ModelProviderEnum.OPENAI)]
    assert len(services[ModelProviderEnum.OPENAI].validated_requests) == 1
    assert services[ModelProviderEnum.OPEN_ROUTER].validated_requests == []


def test_validacao_local_recusa_conversa_vazia() -> None:
    with pytest.raises(ValueError, match="conversation"):
        _build_adapter().validate_conversation(conversation=[])


def test_validacao_local_recusa_modelo_recusado_pelo_catalogo() -> None:
    catalogo = FakeModelCatalog(error=ValueError("modelo fora do catálogo"))

    with pytest.raises(ValueError, match="modelo fora do catálogo"):
        _build_adapter(model_catalog=catalogo).validate_conversation(conversation=[_build_message()])


def test_validacao_local_recusa_provedor_sem_servico() -> None:
    with pytest.raises(ValueError, match="Não há serviço registrado"):
        _build_adapter().validate_conversation(
            conversation=[_build_message()], provider=ModelProviderEnum.AZURE_AI_FOUNDRY
        )


@pytest.mark.parametrize("max_tokens", [0, -5])
def test_validacao_local_recusa_max_tokens_nao_positivo(max_tokens: int) -> None:
    with pytest.raises(ValueError, match="max_tokens"):
        _build_adapter().validate_conversation(conversation=[_build_message()], max_tokens=max_tokens)


@pytest.mark.parametrize("temperature", [-0.1, 1.1, float("nan")])
def test_validacao_local_recusa_temperatura_invalida(temperature: float) -> None:
    with pytest.raises(ValueError, match="temperature"):
        _build_adapter().validate_conversation(conversation=[_build_message()], temperature=temperature)


def test_validacao_local_propaga_a_recusa_do_servico() -> None:
    service = FakeLLMService(validation_error=ValueError("Missing OpenRouter settings."))

    with pytest.raises(ValueError, match="Missing OpenRouter settings"):
        _build_adapter(llm_services=[service]).validate_conversation(conversation=[_build_message()])

    assert service.requests == []


async def test_o_envio_continua_validando_antes_de_chamar_o_servico() -> None:
    service = FakeLLMService(validation_error=ValueError("Missing OpenRouter settings."))

    with pytest.raises(ValueError, match="Missing OpenRouter settings"):
        await _build_adapter(llm_services=[service]).send_message(input_message=_build_message())

    assert service.requests == []
