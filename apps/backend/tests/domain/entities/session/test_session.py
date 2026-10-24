from datetime import UTC, datetime, timedelta

import pytest

from src.domain.entities.session.session import Session
from src.domain.entities.session.llm_invocation import LLMInvocation
from src.domain.entities.session.session_failure import SessionFailure
from src.domain.entities.session.session_message import SessionMessage
from src.domain.entities.session.session_totals import SessionTotals
from src.domain.enums.budget_limit_enum import BudgetLimitEnum
from src.domain.enums.invocation_outcome_enum import InvocationOutcomeEnum
from src.domain.enums.message_source_enum import MessageSourceEnum
from src.domain.enums.model_provider_enum import ModelProviderEnum
from src.domain.enums.session_failure_reason_enum import SessionFailureReasonEnum
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


def _nova_invocacao(invocation_id: str = "inv-1") -> LLMInvocation:
    return LLMInvocation(
        id=invocation_id,
        phase=ThinkingPhaseEnum.B1_TASK_RESOLUTION,
        task_id="T1",
        context_id="ctx-1",
        model_name="vendor/modelo",
        provider=ModelProviderEnum.OPEN_ROUTER,
        started_at=_CRIADO_EM,
    )


def _nova_falha() -> SessionFailure:
    return SessionFailure(
        reason=SessionFailureReasonEnum.RESOURCE_LIMIT,
        phase=ThinkingPhaseEnum.B2_TASK_VERIFICATION,
        description="tentativas esgotadas",
        occurred_at=_CRIADO_EM,
        limit=BudgetLimitEnum.TASK_ATTEMPTS,
        task_id="T2",
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
    assert sessao.invocations == []
    assert sessao.failure is None
    assert sessao.provider is None
    assert sessao.legacy_totals is False


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
    assert sessao.totals.total_tokens == 0
    assert sessao.updated_at == mensagem.timestamp


def test_add_message_preserva_a_ordem_de_chegada() -> None:
    sessao = _nova_sessao()

    sessao.add_message(_nova_mensagem(order=0))
    sessao.add_message(_nova_mensagem(order=1))

    assert [mensagem.order for mensagem in sessao.messages] == [0, 1]
    assert sessao.totals.total_messages == 2


def test_start_invocation_registra_a_chamada_ja_no_inicio() -> None:
    sessao = _nova_sessao()
    invocacao = _nova_invocacao()

    sessao.start_invocation(invocacao)

    assert sessao.invocations == [invocacao]
    assert sessao.totals.total_llm_calls == 1
    assert sessao.totals.total_tokens == 0


def test_complete_invocation_substitui_o_registro_e_acumula_o_consumo() -> None:
    sessao = _nova_sessao()
    sessao.start_invocation(_nova_invocacao("inv-1"))
    sessao.start_invocation(_nova_invocacao("inv-2"))

    concluida = sessao.complete_invocation(
        invocation_id="inv-2",
        outcome=InvocationOutcomeEnum.SUCCESS,
        duration_ms=500,
        tokens_input=10,
        tokens_output=20,
        finish_reason="stop",
        provider_response_id=None,
    )

    assert [i.id for i in sessao.invocations] == ["inv-1", "inv-2"]
    assert sessao.invocations[0].outcome is InvocationOutcomeEnum.STARTED
    assert sessao.invocations[1] is concluida
    assert concluida.outcome is InvocationOutcomeEnum.SUCCESS
    assert sessao.totals.total_llm_calls == 2
    assert sessao.totals.total_tokens == 30
    assert sessao.totals.inference_time_ms == 500


def test_complete_invocation_de_id_desconhecido_e_recusado() -> None:
    sessao = _nova_sessao()

    with pytest.raises(ValueError, match="inv-x"):
        sessao.complete_invocation(
            invocation_id="inv-x",
            outcome=InvocationOutcomeEnum.SUCCESS,
            duration_ms=1,
            tokens_input=1,
            tokens_output=1,
        )


def test_complete_invocation_nao_soma_o_consumo_duas_vezes() -> None:
    sessao = _nova_sessao()
    sessao.start_invocation(_nova_invocacao())
    sessao.complete_invocation(
        invocation_id="inv-1", outcome=InvocationOutcomeEnum.SUCCESS, duration_ms=1, tokens_input=5, tokens_output=5
    )

    with pytest.raises(ValueError, match="já foi concluída"):
        sessao.complete_invocation(
            invocation_id="inv-1",
            outcome=InvocationOutcomeEnum.SUCCESS,
            duration_ms=1,
            tokens_input=5,
            tokens_output=5,
        )

    assert sessao.totals.total_tokens == 10


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


def test_finish_registra_a_falha_estruturada() -> None:
    sessao = _nova_sessao()
    falha = _nova_falha()

    sessao.finish(status=SessionStatusEnum.FAILED, final_answer=None, failure=falha)

    assert sessao.status is SessionStatusEnum.FAILED
    assert sessao.failure is falha


def test_finish_recusa_falha_em_sessao_que_nao_falhou() -> None:
    sessao = _nova_sessao()

    with pytest.raises(ValueError, match="failed"):
        sessao.finish(status=SessionStatusEnum.COMPLETED, final_answer="resposta", failure=_nova_falha())

    assert sessao.status is SessionStatusEnum.RUNNING


def test_reopen_desfaz_o_encerramento_e_restaura_a_data_de_atualizacao() -> None:
    sessao = _nova_sessao()
    sessao.finish(status=SessionStatusEnum.COMPLETED, final_answer="resposta")

    sessao.reopen(updated_at=_CRIADO_EM)

    assert sessao.status is SessionStatusEnum.RUNNING
    assert sessao.final_answer is None
    assert sessao.failure is None
    assert sessao.updated_at == _CRIADO_EM


def test_reopen_desfaz_tambem_a_falha_estruturada() -> None:
    sessao = _nova_sessao()
    falha = SessionFailure(
        reason=SessionFailureReasonEnum.RESOURCE_LIMIT,
        phase=ThinkingPhaseEnum.B2_TASK_VERIFICATION,
        description="tentativas esgotadas",
        occurred_at=_CRIADO_EM,
        limit=BudgetLimitEnum.TASK_ATTEMPTS,
    )
    sessao.finish(status=SessionStatusEnum.FAILED, final_answer=None, failure=falha)

    sessao.reopen(updated_at=_CRIADO_EM)

    assert sessao.failure is None


def test_reopen_de_sessao_em_execucao_e_recusado() -> None:
    sessao = _nova_sessao()

    with pytest.raises(ValueError, match="não há encerramento a desfazer"):
        sessao.reopen(updated_at=_CRIADO_EM)
