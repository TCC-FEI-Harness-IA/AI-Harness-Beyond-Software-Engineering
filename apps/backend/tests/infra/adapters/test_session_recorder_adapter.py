import logging
from datetime import UTC, datetime

import pytest
from dataclasses import replace
from unittest.mock import AsyncMock

from src.domain.entities.session.benchmark_details import BenchmarkDetails

from src.domain.entities.llm.genai_model import GenaiModel
from src.domain.entities.llm.message import Message
from src.domain.entities.llm.tokens_usage import TokensUsage
from src.domain.entities.session.session_failure import SessionFailure
from src.domain.enums.budget_limit_enum import BudgetLimitEnum
from src.domain.enums.invocation_outcome_enum import InvocationOutcomeEnum
from src.domain.enums.message_source_enum import MessageSourceEnum
from src.domain.enums.model_provider_enum import ModelProviderEnum
from src.domain.enums.session_failure_reason_enum import SessionFailureReasonEnum
from src.domain.enums.session_status_enum import SessionStatusEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.infra.adapters.session_recorder_adapter import SessionRecorderAdapter
from tests.doubles.fake_clock import FakeClock
from tests.doubles.fake_id_generator import FakeIdGenerator
from tests.doubles.fake_settings import FakeSettings
from tests.doubles.in_memory_session_repository import InMemorySessionRepository

_PRIMEIRO_INSTANTE = datetime(2026, 8, 31, 12, 0, tzinfo=UTC)
_SEGUNDO_INSTANTE = datetime(2026, 8, 31, 12, 0, 5, tzinfo=UTC)
_TOKENS = TokensUsage(
    tokens_input=11,
    tokens_output=22,
    llm_model=GenaiModel(model_name="vendor/modelo", model_provider=ModelProviderEnum.OPEN_ROUTER),
)
_FALHA = SessionFailure(
    reason=SessionFailureReasonEnum.RESOURCE_LIMIT,
    phase=ThinkingPhaseEnum.B2_TASK_VERIFICATION,
    description="tentativas esgotadas",
    occurred_at=_PRIMEIRO_INSTANTE,
    limit=BudgetLimitEnum.TASK_ATTEMPTS,
    task_id="T2",
    pending_criteria_ids=("AC1",),
)
_PROMPT = (
    Message(creation_timestamp=_PRIMEIRO_INSTANTE, text="prompt da fase", source=MessageSourceEnum.USER),
    Message(creation_timestamp=_SEGUNDO_INSTANTE, text="saida anterior", source=MessageSourceEnum.LLM_AGENT),
)


def _build_recorder(
    repository: InMemorySessionRepository | None = None,
    clock: FakeClock | None = None,
    flush_every_message: bool = True,
) -> SessionRecorderAdapter:
    return SessionRecorderAdapter(
        repository=repository if repository is not None else InMemorySessionRepository(),
        clock=clock if clock is not None else FakeClock(now_values=[_PRIMEIRO_INSTANTE]),
        id_generator=FakeIdGenerator(),
        settings=FakeSettings(ralph_session_flush_every_message=flush_every_message),
        logger=logging.getLogger("teste"),
    )


async def _start(recorder: SessionRecorderAdapter) -> None:
    await recorder.start(
        user_question="pergunta do usuario",
        flow=ThinkingPhaseEnum.DIRECT_INFERENCE,
        model_name="vendor/modelo",
        max_tokens=1200,
        temperature=0.3,
    )


async def test_start_cria_persiste_e_devolve_a_sessao() -> None:
    repositorio = InMemorySessionRepository()
    recorder = _build_recorder(repository=repositorio)

    sessao = await recorder.start(
        user_question="pergunta do usuario",
        flow=ThinkingPhaseEnum.DIRECT_INFERENCE,
        model_name="vendor/modelo",
        max_tokens=1200,
        temperature=0.3,
    )

    assert sessao.id == "sess_1"
    assert sessao.status is SessionStatusEnum.RUNNING
    assert sessao.user_question == "pergunta do usuario"
    assert sessao.flow is ThinkingPhaseEnum.DIRECT_INFERENCE
    assert sessao.model_name == "vendor/modelo"
    assert sessao.max_tokens == 1200
    assert sessao.temperature == 0.3
    assert sessao.created_at == _PRIMEIRO_INSTANTE
    assert sessao.updated_at == _PRIMEIRO_INSTANTE
    assert repositorio.save_calls == ["sess_1"]


async def test_start_duas_vezes_e_recusado() -> None:
    recorder = _build_recorder()
    await _start(recorder=recorder)

    with pytest.raises(ValueError, match="já foi iniciada"):
        await _start(recorder=recorder)


async def test_session_devolve_a_sessao_corrente() -> None:
    recorder = _build_recorder()
    sessao = await recorder.start(
        user_question="pergunta do usuario",
        flow=ThinkingPhaseEnum.DIRECT_INFERENCE,
        model_name="vendor/modelo",
        max_tokens=1200,
        temperature=0.3,
    )

    assert recorder.session is sessao


def test_session_antes_de_start_e_recusada() -> None:
    with pytest.raises(ValueError, match="não foi iniciada"):
        _build_recorder().session


async def test_benchmark_e_marcado_desde_o_inicio_e_avaliacao_persistida() -> None:
    recorder = _build_recorder()
    recorder.benchmark_details = BenchmarkDetails(is_banchmark=True, question_name="Q1")
    await _start(recorder)
    assert recorder.session.benchmark_details.is_banchmark
    details = replace(recorder.session.benchmark_details, is_correct=True, providade_answer="A")
    await recorder.update_benchmark_details(details)
    saved = await recorder.repository.find_by_id(recorder.session.id)
    assert saved.benchmark_details == details


async def test_falha_de_persistencia_da_avaliacao_preserva_metadados_anteriores(monkeypatch) -> None:
    recorder = _build_recorder()
    await _start(recorder)
    before = recorder.session.benchmark_details
    monkeypatch.setattr(recorder.repository, "save", AsyncMock(side_effect=OSError("disco")))
    with pytest.raises(OSError):
        await recorder.update_benchmark_details(BenchmarkDetails(is_banchmark=True))
    assert recorder.session.benchmark_details == before


async def test_record_user_input_antes_de_start_e_recusado() -> None:
    with pytest.raises(ValueError, match="não foi iniciada"):
        await _build_recorder().record_user_input(content="pergunta do usuario")


async def test_record_llm_message_antes_de_start_e_recusado() -> None:
    with pytest.raises(ValueError, match="não foi iniciada"):
        await _build_recorder().record_llm_message(
            phase=ThinkingPhaseEnum.DIRECT_INFERENCE,
            content="resposta",
            tokens=_TOKENS,
            inference_time_ms=500,
            task_id=None,
            context_id=None,
            prompt_input=_PROMPT,
        )


async def test_record_programmatic_step_antes_de_start_e_recusado() -> None:
    with pytest.raises(ValueError, match="não foi iniciada"):
        await _build_recorder().record_programmatic_step(
            phase=ThinkingPhaseEnum.B3_RESULT_STORAGE,
            content="resultado armazenado",
            task_id="T1",
            context_id="ctx_1",
        )


async def test_start_invocation_antes_de_start_e_recusado() -> None:
    with pytest.raises(ValueError, match="não foi iniciada"):
        await _build_recorder().start_invocation(
            phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION,
            task_id="T1",
            context_id="ctx_1",
            model_name="vendor/modelo",
            provider=ModelProviderEnum.OPEN_ROUTER,
        )


async def test_complete_invocation_antes_de_start_e_recusado() -> None:
    with pytest.raises(ValueError, match="não foi iniciada"):
        await _build_recorder().complete_invocation(
            invocation_id="inv_1",
            outcome=InvocationOutcomeEnum.SUCCESS,
            duration_ms=1,
            tokens_input=1,
            tokens_output=1,
        )


async def test_finish_antes_de_start_e_recusado() -> None:
    with pytest.raises(ValueError, match="não foi iniciada"):
        await _build_recorder().finish(status=SessionStatusEnum.COMPLETED, final_answer="resposta")


async def test_record_user_input_registra_mensagem_do_usuario_sem_consumo() -> None:
    recorder = _build_recorder()
    await _start(recorder=recorder)

    mensagem = await recorder.record_user_input(content="pergunta do usuario")

    assert mensagem.order == 0
    assert mensagem.id == "msg_1"
    assert mensagem.source is MessageSourceEnum.USER
    assert mensagem.phase is ThinkingPhaseEnum.DIRECT_INFERENCE
    assert mensagem.content == "pergunta do usuario"
    assert mensagem.timestamp == _PRIMEIRO_INSTANTE
    assert mensagem.task_id is None
    assert mensagem.context_id is None
    assert mensagem.tokens_input == 0
    assert mensagem.tokens_output == 0
    assert mensagem.inference_time_ms == 0
    assert mensagem.model_name is None
    assert mensagem.prompt_input == ()
    assert recorder.session.messages == [mensagem]


async def test_record_llm_message_registra_consumo_tempo_e_modelo() -> None:
    recorder = _build_recorder()
    await _start(recorder=recorder)

    mensagem = await recorder.record_llm_message(
        phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION,
        content="resposta do modelo",
        tokens=_TOKENS,
        inference_time_ms=812,
        task_id="T1",
        context_id="ctx_1",
        prompt_input=_PROMPT,
    )

    assert mensagem.source is MessageSourceEnum.LLM_AGENT
    assert mensagem.phase is ThinkingPhaseEnum.B1_TASK_RESOLUTION
    assert mensagem.tokens_input == 11
    assert mensagem.tokens_output == 22
    assert mensagem.inference_time_ms == 812
    assert mensagem.task_id == "T1"
    assert mensagem.context_id == "ctx_1"
    assert mensagem.model_name == "vendor/modelo"
    assert mensagem.content == "resposta do modelo"
    assert mensagem.prompt_input == _PROMPT


async def test_record_programmatic_step_registra_etapa_do_sistema_sem_consumo() -> None:
    recorder = _build_recorder()
    await _start(recorder=recorder)

    mensagem = await recorder.record_programmatic_step(
        phase=ThinkingPhaseEnum.B3_RESULT_STORAGE,
        content="resultado armazenado",
        task_id="T1",
        context_id="ctx_1",
    )

    assert mensagem.source is MessageSourceEnum.SYSTEM
    assert mensagem.tokens_input == 0
    assert mensagem.tokens_output == 0
    assert mensagem.inference_time_ms == 0
    assert mensagem.model_name is None
    assert mensagem.prompt_input == ()


async def test_record_programmatic_step_guarda_o_prompt_quando_registra_saida_do_modelo() -> None:
    recorder = _build_recorder()
    await _start(recorder=recorder)

    mensagem = await recorder.record_programmatic_step(
        phase=ThinkingPhaseEnum.A1_GENERAL_CRITERIA,
        content="saida invalida descartada",
        task_id=None,
        context_id="ctx_1",
        prompt_input=_PROMPT,
    )

    assert mensagem.source is MessageSourceEnum.SYSTEM
    assert mensagem.prompt_input == _PROMPT


async def test_prompt_de_entrada_e_persistido_com_a_mensagem() -> None:
    repositorio = InMemorySessionRepository()
    recorder = _build_recorder(repository=repositorio, flush_every_message=False)
    await _start(recorder=recorder)

    await recorder.record_llm_message(
        phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION,
        content="resposta do modelo",
        tokens=_TOKENS,
        inference_time_ms=812,
        task_id="T1",
        context_id="ctx_1",
        prompt_input=list(_PROMPT),
    )
    await recorder.finish(status=SessionStatusEnum.COMPLETED, final_answer="resposta final")

    gravada = await repositorio.find_by_id(session_id="sess_1")
    assert gravada is not None
    assert gravada.messages[0].prompt_input == _PROMPT


async def test_ordem_das_mensagens_e_sequencial_e_os_totais_agregam() -> None:
    recorder = _build_recorder()
    await _start(recorder=recorder)

    await recorder.record_user_input(content="pergunta do usuario")
    await recorder.record_llm_message(
        phase=ThinkingPhaseEnum.DIRECT_INFERENCE,
        content="resposta do modelo",
        tokens=_TOKENS,
        inference_time_ms=812,
        task_id=None,
        context_id=None,
        prompt_input=_PROMPT,
    )
    await recorder.record_programmatic_step(
        phase=ThinkingPhaseEnum.B3_RESULT_STORAGE,
        content="resultado armazenado",
        task_id=None,
        context_id=None,
    )

    sessao = recorder.session
    assert [mensagem.order for mensagem in sessao.messages] == [0, 1, 2]
    assert [mensagem.id for mensagem in sessao.messages] == ["msg_1", "msg_2", "msg_3"]
    assert sessao.totals.total_messages == 3
    # O consumo da mensagem é exibição: os totais vêm das invocações, para não contar duas vezes.
    assert sessao.totals.total_llm_calls == 0
    assert sessao.totals.total_tokens == 0
    assert sessao.totals.inference_time_ms == 0


async def test_flush_ligado_persiste_a_cada_registro() -> None:
    repositorio = InMemorySessionRepository()
    recorder = _build_recorder(repository=repositorio, flush_every_message=True)
    await _start(recorder=recorder)

    await recorder.record_user_input(content="pergunta do usuario")
    await recorder.record_programmatic_step(
        phase=ThinkingPhaseEnum.B3_RESULT_STORAGE,
        content="resultado armazenado",
        task_id=None,
        context_id=None,
    )

    assert len(repositorio.save_calls) == 3


async def test_flush_desligado_persiste_apenas_em_start_e_finish() -> None:
    repositorio = InMemorySessionRepository()
    recorder = _build_recorder(repository=repositorio, flush_every_message=False)
    await _start(recorder=recorder)

    await recorder.record_user_input(content="pergunta do usuario")
    await recorder.record_programmatic_step(
        phase=ThinkingPhaseEnum.B3_RESULT_STORAGE,
        content="resultado armazenado",
        task_id=None,
        context_id=None,
    )
    assert len(repositorio.save_calls) == 1

    await recorder.finish(status=SessionStatusEnum.COMPLETED, final_answer="resposta final")

    assert len(repositorio.save_calls) == 2
    gravada = await repositorio.find_by_id(session_id="sess_1")
    assert gravada is not None
    assert len(gravada.messages) == 2


async def test_finish_calcula_o_tempo_de_parede_e_persiste() -> None:
    repositorio = InMemorySessionRepository()
    recorder = _build_recorder(
        repository=repositorio,
        clock=FakeClock(now_values=[_PRIMEIRO_INSTANTE], monotonic_values=[1000, 22008]),
    )
    await _start(recorder=recorder)

    sessao = await recorder.finish(status=SessionStatusEnum.COMPLETED, final_answer="resposta final")

    assert sessao.totals.wall_time_ms == 21008
    assert sessao.status is SessionStatusEnum.COMPLETED
    assert sessao.final_answer == "resposta final"
    assert repositorio.save_calls == ["sess_1", "sess_1"]


async def test_start_registra_o_provedor_efetivo_quando_informado() -> None:
    recorder = _build_recorder()

    sessao = await recorder.start(
        user_question="pergunta",
        flow=ThinkingPhaseEnum.DIRECT_INFERENCE,
        model_name="vendor/modelo",
        max_tokens=1200,
        temperature=0.0,
        provider=ModelProviderEnum.OPENAI,
    )

    assert sessao.provider is ModelProviderEnum.OPENAI
    assert sessao.temperature == 0.0


async def test_start_sem_provedor_deixa_o_campo_vazio() -> None:
    recorder = _build_recorder()
    await _start(recorder=recorder)

    assert recorder.session.provider is None


async def test_start_invocation_registra_a_chamada_no_envio_e_persiste() -> None:
    repositorio = InMemorySessionRepository()
    recorder = _build_recorder(repository=repositorio)
    await _start(recorder=recorder)

    invocation_id = await recorder.start_invocation(
        phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION,
        task_id="T1",
        context_id="ctx_1",
        model_name="vendor/modelo",
        provider=ModelProviderEnum.OPEN_ROUTER,
    )

    assert invocation_id == "inv_1"
    invocacao = recorder.session.invocations[0]
    assert invocacao.id == "inv_1"
    assert invocacao.outcome is InvocationOutcomeEnum.STARTED
    assert invocacao.phase is ThinkingPhaseEnum.B1_TASK_RESOLUTION
    assert invocacao.task_id == "T1"
    assert invocacao.context_id == "ctx_1"
    assert invocacao.model_name == "vendor/modelo"
    assert invocacao.provider is ModelProviderEnum.OPEN_ROUTER
    assert invocacao.started_at == _PRIMEIRO_INSTANTE
    assert recorder.session.totals.total_llm_calls == 1
    gravada = await repositorio.find_by_id(session_id="sess_1")
    assert gravada is not None
    assert [i.id for i in gravada.invocations] == ["inv_1"]


async def test_complete_invocation_acumula_o_consumo_e_persiste() -> None:
    repositorio = InMemorySessionRepository()
    recorder = _build_recorder(repository=repositorio)
    await _start(recorder=recorder)
    invocation_id = await recorder.start_invocation(
        phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION,
        task_id=None,
        context_id=None,
        model_name="vendor/modelo",
        provider=ModelProviderEnum.OPEN_ROUTER,
    )

    await recorder.complete_invocation(
        invocation_id=invocation_id,
        outcome=InvocationOutcomeEnum.EMPTY_COMPLETION,
        duration_ms=812,
        tokens_input=100,
        tokens_output=40,
        finish_reason="length",
        provider_response_id="resp-1",
    )

    invocacao = recorder.session.invocations[0]
    assert invocacao.outcome is InvocationOutcomeEnum.EMPTY_COMPLETION
    assert invocacao.finish_reason == "length"
    assert invocacao.provider_response_id == "resp-1"
    assert recorder.session.totals.total_tokens == 140
    assert recorder.session.totals.inference_time_ms == 812
    gravada = await repositorio.find_by_id(session_id="sess_1")
    assert gravada is not None
    assert gravada.totals.total_tokens == 140


async def test_cada_invocacao_ganha_um_identificador_proprio() -> None:
    recorder = _build_recorder()
    await _start(recorder=recorder)

    ids = [
        await recorder.start_invocation(
            phase=ThinkingPhaseEnum.A1_GENERAL_CRITERIA,
            task_id=None,
            context_id=None,
            model_name="vendor/modelo",
            provider=ModelProviderEnum.OPEN_ROUTER,
        )
        for _ in range(2)
    ]

    assert ids == ["inv_1", "inv_2"]


async def test_finish_registra_a_falha_estruturada_e_persiste() -> None:
    repositorio = InMemorySessionRepository()
    recorder = _build_recorder(repository=repositorio)
    await _start(recorder=recorder)

    await recorder.finish(status=SessionStatusEnum.FAILED, final_answer=None, failure=_FALHA)

    gravada = await repositorio.find_by_id(session_id="sess_1")
    assert gravada is not None
    assert gravada.failure == _FALHA


async def test_flush_desligado_tambem_persiste_apenas_em_start_e_finish_com_invocacoes() -> None:
    repositorio = InMemorySessionRepository()
    recorder = _build_recorder(repository=repositorio, flush_every_message=False)
    await _start(recorder=recorder)

    invocation_id = await recorder.start_invocation(
        phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION,
        task_id=None,
        context_id=None,
        model_name="vendor/modelo",
        provider=ModelProviderEnum.OPEN_ROUTER,
    )
    await recorder.complete_invocation(
        invocation_id=invocation_id, outcome=InvocationOutcomeEnum.SUCCESS, duration_ms=1, tokens_input=1,
        tokens_output=1,
    )

    assert len(repositorio.save_calls) == 1


async def test_timestamp_das_mensagens_vem_do_relogio_injetado() -> None:
    recorder = _build_recorder(clock=FakeClock(now_values=[_PRIMEIRO_INSTANTE, _SEGUNDO_INSTANTE]))
    await _start(recorder=recorder)

    mensagem = await recorder.record_user_input(content="pergunta do usuario")

    assert mensagem.timestamp == _SEGUNDO_INSTANTE
    assert recorder.session.updated_at == _SEGUNDO_INSTANTE


async def test_finish_com_gravacao_falha_devolve_a_sessao_a_execucao_e_propaga_a_falha() -> None:
    repositorio = InMemorySessionRepository(failing_saves={SessionStatusEnum.COMPLETED: 1})
    recorder = _build_recorder(repository=repositorio)
    await _start(recorder)

    with pytest.raises(OSError, match="persistência indisponível"):
        await recorder.finish(status=SessionStatusEnum.COMPLETED, final_answer="resposta")

    assert recorder.session.status is SessionStatusEnum.RUNNING
    assert recorder.session.final_answer is None
    assert recorder.session.failure is None
    assert repositorio.sessions[recorder.session.id].status is SessionStatusEnum.RUNNING


async def test_finish_com_gravacao_falha_restaura_a_falha_estruturada_anterior_e_o_tempo_de_parede() -> None:
    repositorio = InMemorySessionRepository(failing_saves={SessionStatusEnum.FAILED: 1})
    recorder = _build_recorder(
        repository=repositorio,
        clock=FakeClock(now_values=[_PRIMEIRO_INSTANTE], monotonic_values=[100, 5100]),
    )
    await _start(recorder)

    with pytest.raises(OSError):
        await recorder.finish(status=SessionStatusEnum.FAILED, final_answer=None, failure=_FALHA)

    assert recorder.session.failure is None
    assert recorder.session.totals.wall_time_ms == 0


async def test_sessao_devolvida_a_execucao_pode_ser_encerrada_como_falha_depois() -> None:
    repositorio = InMemorySessionRepository(failing_saves={SessionStatusEnum.COMPLETED: 1})
    recorder = _build_recorder(repository=repositorio)
    await _start(recorder)
    with pytest.raises(OSError):
        await recorder.finish(status=SessionStatusEnum.COMPLETED, final_answer="resposta")

    sessao = await recorder.finish(status=SessionStatusEnum.FAILED, final_answer=None, failure=_FALHA)

    assert sessao.status is SessionStatusEnum.FAILED
    persistida = repositorio.sessions[sessao.id]
    assert persistida.status is SessionStatusEnum.FAILED
    assert persistida.failure == _FALHA


async def test_finish_repetido_apos_falha_de_gravacao_pode_concluir_a_sessao() -> None:
    repositorio = InMemorySessionRepository(failing_saves={SessionStatusEnum.COMPLETED: 1})
    recorder = _build_recorder(repository=repositorio)
    await _start(recorder)
    with pytest.raises(OSError):
        await recorder.finish(status=SessionStatusEnum.COMPLETED, final_answer="resposta")

    sessao = await recorder.finish(status=SessionStatusEnum.COMPLETED, final_answer="resposta")

    assert repositorio.sessions[sessao.id].status is SessionStatusEnum.COMPLETED
    assert repositorio.sessions[sessao.id].final_answer == "resposta"
