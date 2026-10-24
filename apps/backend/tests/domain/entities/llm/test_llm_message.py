from datetime import UTC, datetime
from uuid import UUID

from src.domain.entities.llm.genai_model import GenaiModel
from src.domain.entities.llm.llm_message import LLMMessage
from src.domain.entities.llm.message import Message
from src.domain.entities.llm.tokens_usage import TokensUsage
from src.domain.enums.message_source_enum import MessageSourceEnum
from src.domain.enums.model_provider_enum import ModelProviderEnum


def _build_message(text: str, source: MessageSourceEnum) -> Message:
    return Message(creation_timestamp=datetime.now(tz=UTC), text=text, source=source)


def _build_tokens() -> TokensUsage:
    return TokensUsage(
        tokens_input=10,
        tokens_output=20,
        llm_model=GenaiModel(model_name="vendor/modelo", model_provider=ModelProviderEnum.OPEN_ROUTER),
    )


def test_new_popula_todos_os_campos() -> None:
    entrada = _build_message(text="pergunta", source=MessageSourceEnum.USER)
    saida = _build_message(text="resposta", source=MessageSourceEnum.LLM_AGENT)
    tokens = _build_tokens()

    llm_message = LLMMessage.new(input_message=entrada, output_message=saida, tokens=tokens)

    assert isinstance(llm_message.id, UUID)
    assert llm_message.input_message is entrada
    assert llm_message.output_message is saida
    assert llm_message.tokens is tokens


def test_new_gera_timestamp_em_utc() -> None:
    llm_message = LLMMessage.new(
        input_message=_build_message(text="pergunta", source=MessageSourceEnum.USER),
        output_message=_build_message(text="resposta", source=MessageSourceEnum.LLM_AGENT),
        tokens=_build_tokens(),
    )

    assert llm_message.creation_timestamp is not None
    assert llm_message.creation_timestamp.tzinfo is not None
    assert llm_message.creation_timestamp.utcoffset() == UTC.utcoffset(None)


def test_new_gera_identificadores_distintos_a_cada_chamada() -> None:
    entrada = _build_message(text="pergunta", source=MessageSourceEnum.USER)
    saida = _build_message(text="resposta", source=MessageSourceEnum.LLM_AGENT)
    tokens = _build_tokens()

    primeiro = LLMMessage.new(input_message=entrada, output_message=saida, tokens=tokens)
    segundo = LLMMessage.new(input_message=entrada, output_message=saida, tokens=tokens)

    assert primeiro.id != segundo.id


def test_construcao_direta_deixa_todos_os_campos_vazios() -> None:
    llm_message = LLMMessage()

    assert llm_message.id is None
    assert llm_message.creation_timestamp is None
    assert llm_message.input_message is None
    assert llm_message.output_message is None
    assert llm_message.tokens is None


def test_new_aceita_motivo_de_termino_e_identificador_do_provedor() -> None:
    llm_message = LLMMessage.new(
        input_message=_build_message(text="pergunta", source=MessageSourceEnum.USER),
        output_message=_build_message(text="resposta", source=MessageSourceEnum.LLM_AGENT),
        tokens=_build_tokens(),
        finish_reason="stop",
        provider_response_id="resp-1",
    )

    assert llm_message.finish_reason == "stop"
    assert llm_message.provider_response_id == "resp-1"


def test_new_deixa_motivo_de_termino_e_identificador_vazios_por_padrao() -> None:
    llm_message = LLMMessage.new(
        input_message=_build_message(text="pergunta", source=MessageSourceEnum.USER),
        output_message=_build_message(text="resposta", source=MessageSourceEnum.LLM_AGENT),
        tokens=_build_tokens(),
    )

    assert llm_message.finish_reason is None
    assert llm_message.provider_response_id is None
