import logging
from datetime import UTC, datetime

import pytest

from src.application.dtos.default_message_input_dto import DefaultMessageInputDTO
from src.application.usecases.default_message_usecase import DefaultMessageUseCase
from src.domain.entities.llm.genai_model import GenaiModel
from src.domain.entities.llm.llm_message import LLMMessage
from src.domain.entities.llm.message import Message
from src.domain.entities.llm.tokens_usage import TokensUsage
from src.domain.enums.invocation_outcome_enum import InvocationOutcomeEnum
from src.domain.enums.message_source_enum import MessageSourceEnum
from src.domain.enums.model_provider_enum import ModelProviderEnum
from src.domain.enums.session_status_enum import SessionStatusEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.domain.errors.empty_completion_error import EmptyCompletionError
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
    assert sessao.provider is ModelProviderEnum.OPEN_ROUTER


async def test_temperatura_zero_e_registrada_e_enviada_como_pedida() -> None:
    repositorio = InMemorySessionRepository()
    completions = FakeLLMCompletions(result=_build_llm_message(output_message=_build_output_message()))
    entrada = DefaultMessageInputDTO(
        user_input="pergunta do usuario",
        model_name="vendor/modelo",
        max_tokens=100,
        temperature=0.0,
        provider=ModelProviderEnum.OPEN_ROUTER,
    )

    await _build_usecase(completions=completions, repository=repositorio).execute(user_input=entrada)

    sessao = await repositorio.find_by_id(session_id="sess_1")
    assert sessao is not None
    assert sessao.temperature == 0.0
    assert completions.calls[0]["temperature"] == 0.0


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


async def test_a_chamada_unica_vira_uma_invocacao_registrada() -> None:
    repositorio = InMemorySessionRepository()
    resultado = _build_llm_message(output_message=_build_output_message())
    resultado.finish_reason = "stop"
    resultado.provider_response_id = "resp-1"
    completions = FakeLLMCompletions(result=resultado)

    await _build_usecase(completions=completions, repository=repositorio).execute(user_input=_ENTRADA)

    sessao = await repositorio.find_by_id(session_id="sess_1")
    assert sessao is not None
    (invocacao,) = sessao.invocations
    assert invocacao.phase is ThinkingPhaseEnum.DIRECT_INFERENCE
    assert invocacao.task_id is None
    assert invocacao.context_id is None
    assert invocacao.model_name == "vendor/modelo"
    assert invocacao.provider is ModelProviderEnum.OPEN_ROUTER
    assert invocacao.outcome is InvocationOutcomeEnum.SUCCESS
    assert (invocacao.tokens_input, invocacao.tokens_output) == (11, 22)
    assert invocacao.duration_ms == 812
    assert invocacao.finish_reason == "stop"
    assert invocacao.provider_response_id == "resp-1"
    assert invocacao.temperature == 0.3


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


async def test_a_resposta_gravada_guarda_a_pergunta_enviada_como_prompt_de_entrada() -> None:
    repositorio = InMemorySessionRepository()
    completions = FakeLLMCompletions(result=_build_llm_message(output_message=_build_output_message()))

    await _build_usecase(completions=completions, repository=repositorio).execute(user_input=_ENTRADA)

    sessao = await repositorio.find_by_id(session_id="sess_1")
    assert sessao is not None
    pergunta, resposta = sessao.messages
    assert pergunta.prompt_input == ()
    assert resposta.prompt_input == tuple(completions.conversations[0])
    assert [mensagem.text for mensagem in resposta.prompt_input] == ["pergunta do usuario"]


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
    assert sessao.totals.total_llm_calls == 1
    assert sessao.invocations[0].usage_known is False
    assert sessao.messages[1].model_name == "vendor/modelo"


async def test_resposta_com_consumo_desconhecido_conta_a_chamada_sem_inventar_custo() -> None:
    repositorio = InMemorySessionRepository()
    resultado = _build_llm_message(output_message=_build_output_message())
    resultado.tokens = TokensUsage(
        tokens_input=0,
        tokens_output=0,
        llm_model=GenaiModel(model_name="vendor/modelo", model_provider=ModelProviderEnum.OPEN_ROUTER),
        input_known=False,
        output_known=False,
    )

    await _build_usecase(completions=FakeLLMCompletions(result=resultado), repository=repositorio).execute(
        user_input=_ENTRADA
    )

    sessao = await repositorio.find_by_id(session_id="sess_1")
    assert sessao is not None
    assert (sessao.invocations[0].tokens_input, sessao.invocations[0].tokens_output) == (None, None)
    assert sessao.totals.total_llm_calls == 1


async def test_resposta_com_consumo_parcial_preserva_o_contador_ausente_como_desconhecido() -> None:
    repositorio = InMemorySessionRepository()
    resultado = _build_llm_message(output_message=_build_output_message())
    resultado.tokens = TokensUsage(
        tokens_input=10,
        tokens_output=0,
        llm_model=GenaiModel(model_name="vendor/modelo", model_provider=ModelProviderEnum.OPEN_ROUTER),
        output_known=False,
    )

    await _build_usecase(completions=FakeLLMCompletions(result=resultado), repository=repositorio).execute(
        user_input=_ENTRADA
    )

    sessao = await repositorio.find_by_id(session_id="sess_1")
    assert sessao is not None
    assert (sessao.invocations[0].tokens_input, sessao.invocations[0].tokens_output) == (10, None)
    assert sessao.totals.tokens_input == 10
    assert sessao.totals.tokens_output == 0


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
    assert sessao.invocations[0].outcome is InvocationOutcomeEnum.PROVIDER_ERROR
    assert sessao.invocations[0].usage_known is False
    assert sessao.totals.total_llm_calls == 1


async def test_completion_vazia_falha_sem_retry_e_preserva_o_consumo_conhecido() -> None:
    repositorio = InMemorySessionRepository()
    completions = FakeLLMCompletions(
        error=EmptyCompletionError(finish_reason="length", tokens_input=100, tokens_output=40, response_id="gen-1")
    )

    with pytest.raises(EmptyCompletionError):
        await _build_usecase(completions=completions, repository=repositorio).execute(user_input=_ENTRADA)

    assert len(completions.conversations) == 1
    sessao = await repositorio.find_by_id(session_id="sess_1")
    assert sessao is not None
    assert sessao.status is SessionStatusEnum.FAILED
    assert sessao.invocations[0].outcome is InvocationOutcomeEnum.EMPTY_COMPLETION
    assert sessao.invocations[0].finish_reason == "length"
    assert sessao.invocations[0].provider_response_id == "gen-1"
    assert sessao.totals.total_llm_calls == 1
    assert sessao.totals.total_tokens == 140


async def test_resultado_nulo_do_provedor_conta_a_chamada_como_erro() -> None:
    repositorio = InMemorySessionRepository()

    with pytest.raises(ValueError):
        await _build_usecase(completions=FakeLLMCompletions(result=None), repository=repositorio).execute(
            user_input=_ENTRADA
        )

    sessao = await repositorio.find_by_id(session_id="sess_1")
    assert sessao is not None
    assert sessao.invocations[0].outcome is InvocationOutcomeEnum.PROVIDER_ERROR
    assert sessao.totals.total_llm_calls == 1


async def test_recusa_local_da_requisicao_nao_gera_invocacao_nem_conta_chamada() -> None:
    repositorio = InMemorySessionRepository()
    completions = FakeLLMCompletions(validation_error=ValueError("Missing OpenRouter settings."))

    with pytest.raises(ValueError, match="Missing OpenRouter settings"):
        await _build_usecase(completions=completions, repository=repositorio).execute(user_input=_ENTRADA)

    assert completions.conversations == []
    sessao = await repositorio.find_by_id(session_id="sess_1")
    assert sessao is not None
    assert sessao.status is SessionStatusEnum.FAILED
    assert sessao.invocations == []
    assert sessao.totals.total_llm_calls == 0


async def test_falha_ao_gravar_a_resposta_encerra_a_sessao_como_falha_e_propaga_a_falha_original() -> None:
    repositorio = InMemorySessionRepository(failing_save_calls={5})
    completions = FakeLLMCompletions(result=_build_llm_message(output_message=_build_output_message()))

    with pytest.raises(OSError, match=r"gravação 5"):
        await _build_usecase(completions=completions, repository=repositorio).execute(user_input=_ENTRADA)

    sessao = await repositorio.find_by_id(session_id="sess_1")
    assert sessao is not None
    assert sessao.status is SessionStatusEnum.FAILED
    assert sessao.final_answer is None
    assert sessao.totals.total_llm_calls == 1
    assert sessao.invocations[0].outcome is InvocationOutcomeEnum.SUCCESS


async def test_falha_ao_gravar_a_conclusao_encerra_a_sessao_como_falha() -> None:
    repositorio = InMemorySessionRepository(failing_saves={SessionStatusEnum.COMPLETED: 1})
    completions = FakeLLMCompletions(result=_build_llm_message(output_message=_build_output_message()))

    with pytest.raises(OSError, match="persistência indisponível"):
        await _build_usecase(completions=completions, repository=repositorio).execute(user_input=_ENTRADA)

    sessao = await repositorio.find_by_id(session_id="sess_1")
    assert sessao is not None
    assert sessao.status is SessionStatusEnum.FAILED
    assert sessao.final_answer is None


async def test_falha_ao_gravar_a_pergunta_do_usuario_encerra_a_sessao_como_falha() -> None:
    repositorio = InMemorySessionRepository(failing_save_calls={2})
    completions = FakeLLMCompletions(result=_build_llm_message(output_message=_build_output_message()))

    with pytest.raises(OSError, match=r"gravação 2"):
        await _build_usecase(completions=completions, repository=repositorio).execute(user_input=_ENTRADA)

    sessao = await repositorio.find_by_id(session_id="sess_1")
    assert sessao is not None
    assert sessao.status is SessionStatusEnum.FAILED
    assert completions.conversations == []


async def test_persistencia_indisponivel_tambem_no_encerramento_preserva_a_falha_original(
    caplog: pytest.LogCaptureFixture,
) -> None:
    repositorio = InMemorySessionRepository(failing_save_calls={5, 6})
    completions = FakeLLMCompletions(result=_build_llm_message(output_message=_build_output_message()))

    with caplog.at_level(logging.ERROR):
        with pytest.raises(OSError, match=r"gravação 5"):
            await _build_usecase(completions=completions, repository=repositorio).execute(user_input=_ENTRADA)

    assert "Não foi possível encerrar a sessão" in caplog.text
