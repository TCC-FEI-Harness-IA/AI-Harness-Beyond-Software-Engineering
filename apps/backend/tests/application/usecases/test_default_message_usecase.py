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
from src.domain.enums.session_status_enum import SessionStatusEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.infra.adapters.session_recorder_adapter import SessionRecorderAdapter
from tests.doubles.fake_clock import FakeClock
from tests.doubles.fake_id_generator import FakeIdGenerator
from tests.doubles.fake_llm_completions import FakeLLMCompletions
from tests.doubles.fake_settings import FakeSettings
from tests.doubles.in_memory_session_repository import InMemorySessionRepository

_ENTRADA = DefaultMessageInputDTO(
    user_input="pergunta do usuario",
    model_name="vendor/modelo",
    max_tokens=100,
    temperature=0.3,
    provider=ModelProviderEnum.OPEN_ROUTER,
)
_INSTANTE = datetime(2026, 8, 31, 12, 0, tzinfo=UTC)
_MONOTONICOS = [1000, 1100, 1912, 22008]


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


def _build_usecase(
    completions: FakeLLMCompletions,
    repository: InMemorySessionRepository | None = None,
) -> DefaultMessageUseCase:
    clock = FakeClock(now_values=[_INSTANTE], monotonic_values=_MONOTONICOS)
    recorder = SessionRecorderAdapter(
        repository=repository if repository is not None else InMemorySessionRepository(),
        clock=clock,
        id_generator=FakeIdGenerator(),
        settings=FakeSettings(),
        logger=logging.getLogger("teste"),
    )
    return DefaultMessageUseCase(
        llm_completions=completions,
        session_recorder=recorder,
        clock=clock,
        logger=logging.getLogger("teste"),
    )


async def test_devolve_pergunta_resposta_e_metricas() -> None:
    completions = FakeLLMCompletions(result=_build_llm_message(output_message=_build_output_message()))

    saida = await _build_usecase(completions=completions).execute(user_input=_ENTRADA)

    assert saida.message == "pergunta do usuario"
    assert saida.response == "resposta do modelo"
    assert saida.tokens_input == 11
    assert saida.tokens_output == 22
    assert saida.inference_time_ms == 812
    assert saida.session_id == "sess_1"


async def test_grava_a_sessao_com_as_duas_mensagens_do_fluxo() -> None:
    repositorio = InMemorySessionRepository()
    completions = FakeLLMCompletions(result=_build_llm_message(output_message=_build_output_message()))

    await _build_usecase(completions=completions, repository=repositorio).execute(user_input=_ENTRADA)

    sessao = await repositorio.find_by_id(session_id="sess_1")
    assert sessao is not None
    assert sessao.status is SessionStatusEnum.COMPLETED
    assert sessao.final_answer == "resposta do modelo"
    assert [mensagem.source for mensagem in sessao.messages] == [
        MessageSourceEnum.USER,
        MessageSourceEnum.LLM_AGENT,
    ]
    assert [mensagem.content for mensagem in sessao.messages] == [
        "pergunta do usuario",
        "resposta do modelo",
    ]


async def test_sessao_usa_o_fluxo_de_inferencia_direta() -> None:
    repositorio = InMemorySessionRepository()
    completions = FakeLLMCompletions(result=_build_llm_message(output_message=_build_output_message()))

    await _build_usecase(completions=completions, repository=repositorio).execute(user_input=_ENTRADA)

    sessao = await repositorio.find_by_id(session_id="sess_1")
    assert sessao is not None
    assert sessao.flow is ThinkingPhaseEnum.DIRECT_INFERENCE
    assert all(mensagem.phase is ThinkingPhaseEnum.DIRECT_INFERENCE for mensagem in sessao.messages)


async def test_sessao_registra_a_configuracao_do_modelo() -> None:
    repositorio = InMemorySessionRepository()
    completions = FakeLLMCompletions(result=_build_llm_message(output_message=_build_output_message()))

    await _build_usecase(completions=completions, repository=repositorio).execute(user_input=_ENTRADA)

    sessao = await repositorio.find_by_id(session_id="sess_1")
    assert sessao is not None
    assert sessao.user_question == "pergunta do usuario"
    assert sessao.model_name == "vendor/modelo"
    assert sessao.max_tokens == 100
    assert sessao.temperature == 0.3


async def test_totais_da_sessao_batem_com_o_consumo_da_chamada() -> None:
    repositorio = InMemorySessionRepository()
    completions = FakeLLMCompletions(result=_build_llm_message(output_message=_build_output_message()))

    await _build_usecase(completions=completions, repository=repositorio).execute(user_input=_ENTRADA)

    sessao = await repositorio.find_by_id(session_id="sess_1")
    assert sessao is not None
    assert sessao.totals.total_messages == 2
    assert sessao.totals.total_llm_calls == 1
    assert sessao.totals.tokens_input == 11
    assert sessao.totals.tokens_output == 22
    assert sessao.totals.total_tokens == 33
    assert sessao.totals.inference_time_ms == 812
    assert sessao.totals.wall_time_ms == 21008


async def test_tempo_de_inferencia_e_medido_por_mensagem() -> None:
    repositorio = InMemorySessionRepository()
    completions = FakeLLMCompletions(result=_build_llm_message(output_message=_build_output_message()))

    await _build_usecase(completions=completions, repository=repositorio).execute(user_input=_ENTRADA)

    sessao = await repositorio.find_by_id(session_id="sess_1")
    assert sessao is not None
    assert [mensagem.inference_time_ms for mensagem in sessao.messages] == [0, 812]
    assert [mensagem.total_tokens for mensagem in sessao.messages] == [0, 33]


async def test_repassa_os_parametros_do_modelo_para_o_provedor() -> None:
    completions = FakeLLMCompletions(result=_build_llm_message(output_message=_build_output_message()))

    await _build_usecase(completions=completions).execute(user_input=_ENTRADA)

    assert completions.calls[0] == {
        "model_name": "vendor/modelo",
        "max_tokens": 100,
        "temperature": 0.3,
        "provider": ModelProviderEnum.OPEN_ROUTER,
    }


async def test_envia_a_pergunta_como_mensagem_do_usuario_em_utc() -> None:
    completions = FakeLLMCompletions(result=_build_llm_message(output_message=_build_output_message()))

    await _build_usecase(completions=completions).execute(user_input=_ENTRADA)

    enviada = completions.conversations[0][0]
    assert enviada.text == "pergunta do usuario"
    assert enviada.source is MessageSourceEnum.USER
    assert enviada.creation_timestamp == _INSTANTE


async def test_resultado_nulo_do_provedor_e_recusado() -> None:
    repositorio = InMemorySessionRepository()
    completions = FakeLLMCompletions(result=None)

    with pytest.raises(ValueError, match="Resposta do LLM veio como None."):
        await _build_usecase(completions=completions, repository=repositorio).execute(user_input=_ENTRADA)

    sessao = await repositorio.find_by_id(session_id="sess_1")
    assert sessao is not None
    assert sessao.status is SessionStatusEnum.FAILED


async def test_resposta_sem_mensagem_de_saida_vira_texto_vazio() -> None:
    completions = FakeLLMCompletions(result=_build_llm_message(output_message=None))

    saida = await _build_usecase(completions=completions).execute(user_input=_ENTRADA)

    assert saida.response == ""


async def test_resposta_sem_tokens_zera_as_metricas() -> None:
    repositorio = InMemorySessionRepository()
    resultado = _build_llm_message(output_message=_build_output_message())
    resultado.tokens = None
    completions = FakeLLMCompletions(result=resultado)

    saida = await _build_usecase(completions=completions, repository=repositorio).execute(user_input=_ENTRADA)

    assert saida.tokens_input == 0
    assert saida.tokens_output == 0
    sessao = await repositorio.find_by_id(session_id="sess_1")
    assert sessao is not None
    assert sessao.totals.total_tokens == 0
    assert sessao.totals.total_llm_calls == 0
    assert sessao.messages[1].model_name == "vendor/modelo"


async def test_falha_do_provedor_encerra_a_sessao_como_falha_e_propaga(
    caplog: pytest.LogCaptureFixture,
) -> None:
    repositorio = InMemorySessionRepository()
    completions = FakeLLMCompletions(error=RuntimeError("provedor fora do ar"))

    with caplog.at_level(logging.ERROR):
        with pytest.raises(RuntimeError, match="provedor fora do ar"):
            await _build_usecase(completions=completions, repository=repositorio).execute(user_input=_ENTRADA)

    assert "Erro ao executar DefaultMessageUseCase" in caplog.text
    sessao = await repositorio.find_by_id(session_id="sess_1")
    assert sessao is not None
    assert sessao.status is SessionStatusEnum.FAILED
    assert sessao.final_answer is None
    assert len(sessao.messages) == 1
