import logging
from datetime import UTC, datetime

import pytest

from src.application.dtos.default_message_input_dto import DefaultMessageInputDTO
from src.application.usecases.default_message_usecase import DefaultMessageUseCase
from src.domain.entities.llm.genai_model import GenaiModel
from src.domain.entities.llm.llm_message import LLMMessage
from src.domain.entities.llm.message import Message
from src.domain.entities.llm.tokens_usage import TokensUsage
from src.domain.enums.message_source_enum import MessageSourceEnum
from src.domain.enums.model_provider_enum import ModelProviderEnum
from tests.doubles.fake_llm_completions import FakeLLMCompletions

_ENTRADA = DefaultMessageInputDTO(
    user_input="pergunta do usuario",
    model_name="vendor/modelo",
    max_tokens=100,
    temperature=0.3,
)


def _build_llm_message(output_message: Message | None) -> LLMMessage:
    return LLMMessage(
        input_message=Message(
            creation_timestamp=datetime.now(tz=UTC),
            text="pergunta do usuario",
            source=MessageSourceEnum.USER,
        ),
        output_message=output_message,
        tokens=TokensUsage(
            tokens_input=11,
            tokens_output=22,
            llm_model=GenaiModel(model_name="vendor/modelo", model_provider=ModelProviderEnum.OPEN_ROUTER),
        ),
    )


def _build_output_message(text: str = "resposta do modelo") -> Message:
    return Message(creation_timestamp=datetime.now(tz=UTC), text=text, source=MessageSourceEnum.LLM_AGENT)


def _build_usecase(completions: FakeLLMCompletions) -> DefaultMessageUseCase:
    return DefaultMessageUseCase(llm_completions=completions, logger=logging.getLogger("teste"))


async def test_devolve_pergunta_resposta_e_metricas() -> None:
    completions = FakeLLMCompletions(result=_build_llm_message(output_message=_build_output_message()))

    saida = await _build_usecase(completions=completions).execute(user_input=_ENTRADA)

    assert saida.message == "pergunta do usuario"
    assert saida.response == "resposta do modelo"
    assert saida.tokens_input == 11
    assert saida.tokens_output == 22
    assert saida.inference_time_ms == 0


async def test_repassa_os_parametros_do_modelo_para_o_provedor() -> None:
    completions = FakeLLMCompletions(result=_build_llm_message(output_message=_build_output_message()))

    await _build_usecase(completions=completions).execute(user_input=_ENTRADA)

    assert completions.calls[0] == {"model_name": "vendor/modelo", "max_tokens": 100, "temperature": 0.3}


async def test_envia_a_pergunta_como_mensagem_do_usuario_em_utc() -> None:
    completions = FakeLLMCompletions(result=_build_llm_message(output_message=_build_output_message()))

    await _build_usecase(completions=completions).execute(user_input=_ENTRADA)

    enviada = completions.conversations[0][0]
    assert enviada.text == "pergunta do usuario"
    assert enviada.source is MessageSourceEnum.USER
    assert enviada.creation_timestamp.tzinfo is not None


async def test_resultado_nulo_do_provedor_e_recusado() -> None:
    completions = FakeLLMCompletions(result=None)

    with pytest.raises(ValueError, match="Resposta do LLM veio como None."):
        await _build_usecase(completions=completions).execute(user_input=_ENTRADA)


async def test_resposta_sem_mensagem_de_saida_vira_texto_vazio() -> None:
    completions = FakeLLMCompletions(result=_build_llm_message(output_message=None))

    saida = await _build_usecase(completions=completions).execute(user_input=_ENTRADA)

    assert saida.response == ""


async def test_resposta_sem_tokens_zera_as_metricas() -> None:
    resultado = _build_llm_message(output_message=_build_output_message())
    resultado.tokens = None
    completions = FakeLLMCompletions(result=resultado)

    saida = await _build_usecase(completions=completions).execute(user_input=_ENTRADA)

    assert saida.tokens_input == 0
    assert saida.tokens_output == 0


async def test_falha_do_provedor_e_propagada_e_registrada(caplog: pytest.LogCaptureFixture) -> None:
    completions = FakeLLMCompletions(error=RuntimeError("provedor fora do ar"))

    with caplog.at_level(logging.ERROR):
        with pytest.raises(RuntimeError, match="provedor fora do ar"):
            await _build_usecase(completions=completions).execute(user_input=_ENTRADA)

    assert "Erro ao executar DefaultMessageUseCase" in caplog.text
