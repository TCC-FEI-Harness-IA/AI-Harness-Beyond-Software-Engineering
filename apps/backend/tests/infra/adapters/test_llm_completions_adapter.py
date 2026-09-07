import logging
from datetime import UTC, datetime
from typing import Any

import pytest

from src.domain.entities.llm.message import Message
from src.domain.enums.message_source_enum import MessageSourceEnum
from src.domain.enums.model_provider_enum import ModelProviderEnum
from src.infra.adapters.llm_completions_adapter import LLMCompletionsAdapter
from tests.doubles.fake_llm_service import FakeLLMService
from tests.doubles.fake_model_catalog import FakeModelCatalog
from tests.doubles.fake_settings import FakeSettings


def _build_message(text: str = "pergunta", source: MessageSourceEnum = MessageSourceEnum.USER) -> Message:
    return Message(creation_timestamp=datetime.now(tz=UTC), text=text, source=source)


def _build_adapter(
    llm_service: FakeLLMService | None = None,
    model_catalog: FakeModelCatalog | None = None,
    **settings_overrides: Any,
) -> LLMCompletionsAdapter:
    return LLMCompletionsAdapter(
        llm_service=llm_service or FakeLLMService(),
        model_catalog=model_catalog or FakeModelCatalog(),
        logger=logging.getLogger("teste"),
        settings=FakeSettings(**settings_overrides),
    )


# ── Defaults e sobrescritas ──────────────────────────────────────────────────

async def test_sem_sobrescritas_usa_os_defaults_das_configuracoes() -> None:
    service = FakeLLMService()
    adapter = _build_adapter(
        llm_service=service,
        openrouter_model="vendor/padrao",
        openrouter_max_tokens=512,
        openrouter_temperature=0.4,
    )

    await adapter.send_message(input_message=_build_message())

    enviada = service.requests[0]
    assert enviada.llm_model.model_name == "vendor/padrao"
    assert enviada.max_tokens == 512
    assert enviada.temperature == 0.4


async def test_sobrescritas_vencem_os_defaults() -> None:
    service = FakeLLMService()
    adapter = _build_adapter(llm_service=service, openrouter_model="vendor/padrao")

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
    adapter = _build_adapter(model_catalog=catalog, openrouter_model="vendor/padrao")

    await adapter.send_message(input_message=_build_message())

    assert catalog.resolved == [("vendor/padrao", ModelProviderEnum.OPEN_ROUTER)]


async def test_modelo_recusado_pelo_catalogo_propaga_o_erro() -> None:
    catalog = FakeModelCatalog(error=ValueError("Model 'vendor/padrao' is not available."))
    adapter = _build_adapter(model_catalog=catalog)

    with pytest.raises(ValueError, match="is not available"):
        await adapter.send_message(input_message=_build_message())


# ── Validações ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("model_name", ["", "   "])
async def test_nome_de_modelo_em_branco_e_recusado(model_name: str) -> None:
    with pytest.raises(ValueError, match="model_name"):
        await _build_adapter().send_message(input_message=_build_message(), model_name=model_name)


def test_nome_de_modelo_padrao_em_branco_e_recusado_na_construcao() -> None:
    with pytest.raises(ValueError, match="model_name"):
        _build_adapter(openrouter_model="   ")


@pytest.mark.parametrize("max_tokens", [0, -5])
async def test_max_tokens_nao_positivo_e_recusado(max_tokens: int) -> None:
    with pytest.raises(ValueError, match="max_tokens"):
        await _build_adapter().send_message(input_message=_build_message(), max_tokens=max_tokens)


@pytest.mark.parametrize("temperature", [-0.1, 1.1])
async def test_temperatura_fora_do_intervalo_e_recusada(temperature: float) -> None:
    with pytest.raises(ValueError, match="temperature"):
        await _build_adapter().send_message(input_message=_build_message(), temperature=temperature)


async def test_temperatura_e_arredondada_para_uma_casa() -> None:
    service = FakeLLMService()

    await _build_adapter(llm_service=service).send_message(input_message=_build_message(), temperature=0.66)

    assert service.requests[0].temperature == 0.7


# ── Conversa multi-turno ─────────────────────────────────────────────────────

async def test_conversa_preserva_a_ordem_e_mapeia_os_papeis() -> None:
    service = FakeLLMService()
    conversa = [
        _build_message(text="pergunta", source=MessageSourceEnum.USER),
        _build_message(text="resposta anterior", source=MessageSourceEnum.LLM_AGENT),
        _build_message(text="instrucao", source=MessageSourceEnum.SYSTEM),
    ]

    await _build_adapter(llm_service=service).send_conversation(conversation=conversa)

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
    adapter = _build_adapter(openrouter_model="vendor/padrao")

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

    await _build_adapter(llm_service=service).send_message(input_message=_build_message())

    assert len(service.requests) == 1
    assert len(service.requests[0].messages) == 1
