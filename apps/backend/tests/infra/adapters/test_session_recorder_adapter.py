import logging
from datetime import UTC, datetime

import pytest

from src.domain.entities.llm.genai_model import GenaiModel
from src.domain.entities.llm.tokens_usage import TokensUsage
from src.domain.entities.session.session_degradation import SessionDegradation
from src.domain.enums.budget_limit_enum import BudgetLimitEnum
from src.domain.enums.message_source_enum import MessageSourceEnum
from src.domain.enums.model_provider_enum import ModelProviderEnum
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
_DEGRADACAO = SessionDegradation(
    limit=BudgetLimitEnum.TASK_ATTEMPTS,
    phase=ThinkingPhaseEnum.B2_TASK_VERIFICATION,
    task_id="T2",
    description="tentativas esgotadas",
    occurred_at=_PRIMEIRO_INSTANTE,
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
        )


async def test_record_programmatic_step_antes_de_start_e_recusado() -> None:
    with pytest.raises(ValueError, match="não foi iniciada"):
        await _build_recorder().record_programmatic_step(
            phase=ThinkingPhaseEnum.B3_RESULT_STORAGE,
            content="resultado armazenado",
            task_id="T1",
            context_id="ctx_1",
        )


async def test_record_degradation_antes_de_start_e_recusado() -> None:
    with pytest.raises(ValueError, match="não foi iniciada"):
        await _build_recorder().record_degradation(degradation=_DEGRADACAO)


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
    )

    assert mensagem.source is MessageSourceEnum.LLM_AGENT
    assert mensagem.phase is ThinkingPhaseEnum.B1_TASK_RESOLUTION
    assert mensagem.tokens_input == 11
    assert mensagem.tokens_output == 22
    assert mensagem.inference_time_ms == 812
    assert mensagem.task_id == "T1"
    assert mensagem.context_id == "ctx_1"
    assert mensagem.model_name == "vendor/modelo"


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
    assert sessao.totals.total_llm_calls == 1
    assert sessao.totals.tokens_input == 11
    assert sessao.totals.tokens_output == 22
    assert sessao.totals.inference_time_ms == 812


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


async def test_record_degradation_registra_na_sessao_e_persiste() -> None:
    repositorio = InMemorySessionRepository()
    recorder = _build_recorder(repository=repositorio)
    await _start(recorder=recorder)

    await recorder.record_degradation(degradation=_DEGRADACAO)

    assert recorder.session.degradations == [_DEGRADACAO]
    assert len(repositorio.save_calls) == 2


async def test_timestamp_das_mensagens_vem_do_relogio_injetado() -> None:
    recorder = _build_recorder(clock=FakeClock(now_values=[_PRIMEIRO_INSTANTE, _SEGUNDO_INSTANTE]))
    await _start(recorder=recorder)

    mensagem = await recorder.record_user_input(content="pergunta do usuario")

    assert mensagem.timestamp == _SEGUNDO_INSTANTE
    assert recorder.session.updated_at == _SEGUNDO_INSTANTE
