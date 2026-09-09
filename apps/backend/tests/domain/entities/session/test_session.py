from datetime import UTC, datetime

from src.domain.entities.session.session import Session
from src.domain.entities.session.session_totals import SessionTotals
from src.domain.enums.session_status_enum import SessionStatusEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum

_CRIADO_EM = datetime.now(tz=UTC)


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
