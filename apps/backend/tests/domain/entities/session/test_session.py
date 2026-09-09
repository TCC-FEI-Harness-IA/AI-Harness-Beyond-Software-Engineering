from datetime import UTC, datetime, timedelta

import pytest

from src.domain.entities.session.session import Session
from src.domain.entities.session.session_degradation import SessionDegradation
from src.domain.entities.session.session_message import SessionMessage
from src.domain.entities.session.session_totals import SessionTotals
from src.domain.enums.budget_limit_enum import BudgetLimitEnum
from src.domain.enums.message_source_enum import MessageSourceEnum
from src.domain.enums.session_status_enum import SessionStatusEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum

_CRIADO_EM = datetime(2026, 8, 31, 12, 0, tzinfo=UTC)


def _nova_sessao() -> Session:
    return Session(
        id="sess-1",
        user_question="pergunta do usuario",
        flow=ThinkingPhaseEnum.DIRECT_INFERENCE,
        model_name="vendor/modelo",
        max_tokens=1024,
        temperature=0.7,
        status=SessionStatusEnum.RUNNING,
        created_at=_CRIADO_EM,
        updated_at=_CRIADO_EM,
    )


def _nova_mensagem(order: int = 0, tokens_input: int = 10, tokens_output: int = 20) -> SessionMessage:
    return SessionMessage(
        id=f"msg-{order}",
        order=order,
        timestamp=_CRIADO_EM + timedelta(seconds=order + 1),
        phase=ThinkingPhaseEnum.DIRECT_INFERENCE,
        source=MessageSourceEnum.LLM_AGENT,
        content="conteudo",
        task_id=None,
        context_id=None,
        tokens_input=tokens_input,
        tokens_output=tokens_output,
        inference_time_ms=500,
        model_name="vendor/modelo",
    )


def _nova_degradacao() -> SessionDegradation:
    return SessionDegradation(
        limit=BudgetLimitEnum.TASK_ATTEMPTS,
        phase=ThinkingPhaseEnum.B2_TASK_VERIFICATION,
        task_id="T2",
        description="tentativas esgotadas",
        occurred_at=_CRIADO_EM,
    )


def test_carrega_os_campos_obrigatorios() -> None:
    sessao = _nova_sessao()

    assert sessao.id == "sess-1"
    assert sessao.user_question == "pergunta do usuario"
    assert sessao.flow is ThinkingPhaseEnum.DIRECT_INFERENCE
    assert sessao.model_name == "vendor/modelo"
    assert sessao.max_tokens == 1024
    assert sessao.temperature == 0.7
    assert sessao.status is SessionStatusEnum.RUNNING
    assert sessao.created_at == _CRIADO_EM
    assert sessao.updated_at == _CRIADO_EM


def test_defaults_de_uma_sessao_nova() -> None:
    sessao = _nova_sessao()

    assert sessao.messages == []
    assert sessao.totals == SessionTotals()
    assert sessao.final_answer is None
    assert sessao.degradations == []


def test_e_mutavel() -> None:
    sessao = _nova_sessao()

    sessao.status = SessionStatusEnum.COMPLETED

    assert sessao.status is SessionStatusEnum.COMPLETED


def test_add_message_anexa_atualiza_totais_e_data_de_atualizacao() -> None:
    sessao = _nova_sessao()
    mensagem = _nova_mensagem()

    sessao.add_message(mensagem)

    assert sessao.messages == [mensagem]
    assert sessao.totals.total_messages == 1
    assert sessao.totals.total_tokens == 30
    assert sessao.updated_at == mensagem.timestamp


def test_add_message_preserva_a_ordem_de_chegada() -> None:
    sessao = _nova_sessao()

    sessao.add_message(_nova_mensagem(order=0))
    sessao.add_message(_nova_mensagem(order=1))

    assert [mensagem.order for mensagem in sessao.messages] == [0, 1]
    assert sessao.totals.total_messages == 2


def test_register_degradation_anexa_a_lista() -> None:
    sessao = _nova_sessao()
    degradacao = _nova_degradacao()

    sessao.register_degradation(degradacao)

    assert sessao.degradations == [degradacao]


def test_finish_define_status_resposta_final_e_data_de_atualizacao() -> None:
    sessao = _nova_sessao()

    sessao.finish(status=SessionStatusEnum.COMPLETED, final_answer="resposta final")

    assert sessao.status is SessionStatusEnum.COMPLETED
    assert sessao.final_answer == "resposta final"
    assert sessao.updated_at > _CRIADO_EM
    assert sessao.updated_at.tzinfo is not None


def test_finish_aceita_sessao_sem_resposta_final() -> None:
    sessao = _nova_sessao()

    sessao.finish(status=SessionStatusEnum.FAILED, final_answer=None)

    assert sessao.status is SessionStatusEnum.FAILED
    assert sessao.final_answer is None


def test_finish_de_sessao_ja_encerrada_e_recusado() -> None:
    sessao = _nova_sessao()
    sessao.finish(status=SessionStatusEnum.COMPLETED, final_answer="resposta final")

    with pytest.raises(ValueError, match="já foi encerrada"):
        sessao.finish(status=SessionStatusEnum.FAILED, final_answer=None)
