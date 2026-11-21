"""Sessão com uma recusa de saída recuperada, para testar persistência, consulta e exportação."""
from datetime import UTC, datetime

from src.domain.entities.session.llm_invocation import LLMInvocation
from src.domain.entities.session.session import Session
from src.domain.entities.session.session_message import SessionMessage
from src.domain.entities.thinking.output_diagnostic import OutputDiagnostic
from src.domain.entities.thinking.output_problem import OutputProblem
from src.domain.entities.thinking.output_recovery import OutputRecovery
from src.domain.enums.invocation_outcome_enum import InvocationOutcomeEnum
from src.domain.enums.length_interruption_enum import LengthInterruptionEnum
from src.domain.enums.message_source_enum import MessageSourceEnum
from src.domain.enums.model_provider_enum import ModelProviderEnum
from src.domain.enums.output_contract_status_enum import OutputContractStatusEnum
from src.domain.enums.output_problem_code_enum import OutputProblemCodeEnum
from src.domain.enums.output_syntax_status_enum import OutputSyntaxStatusEnum
from src.domain.enums.recovery_result_enum import RecoveryResultEnum
from src.domain.enums.recovery_strategy_enum import RecoveryStrategyEnum
from src.domain.enums.session_status_enum import SessionStatusEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum

_INSTANTE = datetime(2026, 10, 30, 9, 0, tzinfo=UTC)

DIAGNOSTICO_Q037 = OutputDiagnostic(
    syntax_status=OutputSyntaxStatusEnum.VALID,
    contract_status=OutputContractStatusEnum.INVALID,
    finish_reason="stop",
    length_interruption=LengthInterruptionEnum.NOT_DETECTED,
    problem=OutputProblem(
        code=OutputProblemCodeEnum.DECISION_CONSISTENCY,
        reason="A decisão 'approved' é incoerente com as avaliações.",
        field="decision",
        affected_ids=("T1-AC2",),
    ),
)
DIAGNOSTICO_REPARADO = OutputDiagnostic.accepted(
    finish_reason=None, length_interruption=LengthInterruptionEnum.SUSPECTED, repaired_closings="]}"
)
RECUPERACAO = OutputRecovery(
    strategy=RecoveryStrategyEnum.CORRECTION_PROMPT,
    result=RecoveryResultEnum.RECOVERED,
    resolved_by_invocation_id="inv-2",
)


def _invocacao(invocation_id: str, recovers_invocation_id: str | None = None) -> LLMInvocation:
    return LLMInvocation(
        id=invocation_id,
        phase=ThinkingPhaseEnum.B2_TASK_VERIFICATION,
        task_id="T1",
        context_id="ctx-v",
        model_name="vendor/modelo",
        provider=ModelProviderEnum.OPEN_ROUTER,
        started_at=_INSTANTE,
        temperature=1.0,
        recovers_invocation_id=recovers_invocation_id,
    ).complete(
        outcome=InvocationOutcomeEnum.SUCCESS, duration_ms=50, tokens_input=30, tokens_output=12, finish_reason="stop"
    )


def sessao_com_recusa_recuperada(identificador: str = "sess_diag") -> Session:
    """Sessão em que a 1ª saída da B.2 foi recusada (Q037) e a correção, aceita após reparo."""
    sessao = Session(
        id=identificador,
        user_question="pergunta",
        flow=ThinkingPhaseEnum.C3_FINAL_ANSWER,
        model_name="vendor/modelo",
        max_tokens=4096,
        temperature=0.0,
        status=SessionStatusEnum.RUNNING,
        created_at=_INSTANTE,
        updated_at=_INSTANTE,
        provider=ModelProviderEnum.OPEN_ROUTER,
    )
    for invocacao in (_invocacao("inv-1"), _invocacao("inv-2", recovers_invocation_id="inv-1")):
        sessao.start_invocation(invocation=invocacao)
    sessao.record_output_diagnostic(invocation_id="inv-1", diagnostic=DIAGNOSTICO_Q037)
    sessao.record_output_recovery(invocation_id="inv-1", recovery=RECUPERACAO)
    sessao.record_output_diagnostic(invocation_id="inv-2", diagnostic=DIAGNOSTICO_REPARADO)
    sessao.add_message(
        SessionMessage(
            id="msg-0",
            order=0,
            timestamp=_INSTANTE,
            phase=ThinkingPhaseEnum.B2_TASK_VERIFICATION,
            source=MessageSourceEnum.SYSTEM,
            content="Saída inválida descartada na fase B2: decisão incoerente",
            task_id="T1",
            context_id="ctx-v",
            tokens_input=0,
            tokens_output=0,
            inference_time_ms=0,
            model_name=None,
            invocation_id="inv-1",
        )
    )
    return sessao
